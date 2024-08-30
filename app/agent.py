from typing import Any, List, Union, Callable, Dict
from pathlib import Path
import re
from fastapi import HTTPException, Request
from typing_extensions import TypedDict
from langchain.agents import AgentExecutor
import time
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain_core.messages import AIMessage, FunctionMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import UpstashRedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables import ConfigurableFieldSpec
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.tools import tool
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langserve.pydantic_v1 import BaseModel, Field
from langchain.tools.retriever import create_retriever_tool
from app.vectorstore import fullDocVectorstore, splitDocVectorstore
import os
from upstash_redis import Redis
import dotenv

dotenv.load_dotenv()


def _is_valid_identifier(value: str) -> bool:
    """Check if the value is a valid identifier."""
    valid_characters = re.compile(r"^[a-zA-Z0-9-_]+$")
    return bool(valid_characters.match(value))


def create_session_factory(
    base_dir: Union[str, Path],
) -> Callable[[str], BaseChatMessageHistory]:
    def get_chat_history(
        userId: str, conversationId: str
    ) -> UpstashRedisChatMessageHistory:
        """Get a chat history from a user id and conversation id."""
        if not _is_valid_identifier(userId):
            raise ValueError(
                f"User ID {userId} is not in a valid format. "
                "User ID must only contain alphanumeric characters, "
                "hyphens, and underscores."
                "Please include a valid cookie in the request headers called 'user-id'."
            )
        if not _is_valid_identifier(conversationId):
            raise ValueError(
                f"Conversation ID {conversationId} is not in a valid format. "
                "Conversation ID must only contain alphanumeric characters, "
                "hyphens, and underscores. Please provide a valid conversation id "
                "via config. For example, "
                "chain.invoke(.., {'configurable': {'conversationId': '123'}})"
            )

        return UpstashRedisChatMessageHistory(
            url=os.getenv("UPSTASH_REDIS_HISTORY_REST_URL"),
            token=os.getenv("UPSTASH_REDIS_HISTORY_REST_TOKEN"),
            session_id=conversationId,
            key_prefix=userId + "/",
        )

    return get_chat_history


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are the Holocaust Answer Engine (HAE), a virtual historian-librarian with access to a robust database of primary source testimony about the Holocaust. Your role is to answer questions about the Holocaust using only the information provided by your specialized tools. Do not use any background knowledge or information not obtained through these tools.

You have access to two tools:

1. Short-answer retrieval tool: This tool provides general information from multiple sources to answer broader questions about the Holocaust. Also use this tool to answer questions about survivors from various places.
2. Personal testimony tool: This tool provides access to full testimonies of individuals to answer more specific, personal questions.

When answering questions, follow these guidelines:
1. Determine which tool is most appropriate for the question asked.
2. Use only information obtained from the tool calls.
3. If the information provided by the tools is insufficient to answer the question, state that you don't have enough information to provide a complete answer.
4. Be respectful and sensitive when discussing Holocaust-related topics.
5. Do not speculate or provide information beyond what is given by the tools.

Important ethical considerations:
1. Always maintain a respectful and somber tone when discussing Holocaust-related topics.
2. Do not engage in Holocaust denial or minimization.
3. If asked about controversial or sensitive topics, provide factual information from the tools without personal commentary.
4. If a question is inappropriate or offensive, politely refuse to answer and explain why.

Remember that you are limited to the information provided by the tools. Do not use any external knowledge or make assumptions beyond what is explicitly stated in the tool responses. Return your answer in plaintext; no XML, markdown, or other formatting is necessary. If you are unsure how to answer a question, you may ask for clarification or guidance.
""",
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

fullDocRetriever = fullDocVectorstore.as_retriever(search_kwargs={"k": 1})

splitDocRetriever = splitDocVectorstore.as_retriever(search_kwargs={"k": 4})

fullDocRetrieverTool = create_retriever_tool(
    fullDocRetriever,
    "personal_testimony_retriever",
    "Use this tool to answer questions about specific individuals in the context of the Holocaust. You must use this tool if you are asked about a specific individual in the context of the Holocaust. Return your answer in plaintext; no XML, markdown, or other formatting is necessary.",
)

splitDocRetrieverTool = create_retriever_tool(
    splitDocRetriever,
    "short_answer_retriever",
    "Use this tool to answer questions about the Holocaust in general. If you see the name of a person in the question, do not use it. Remember that this tool returns 4 documents. They are all unique parts of survivors' (plural) testimony. Don't create a singular narrative unless only one survivor is mentioned. You must use this tool if you are asked about the Holocaust in general. Return your answer in plaintext; no XML, markdown, or other formatting is necessary.",
)

model = ChatOpenAI(model="gpt-4o-mini", stream_usage=True)

tools = [fullDocRetrieverTool, splitDocRetrieverTool]

model_with_tools = model.bind_tools([fullDocRetrieverTool, splitDocRetrieverTool])


def inspect(conversationId):
    """Print the conversationId and return it."""
    print(conversationId)
    return conversationId


agent = (
    {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_to_openai_tool_messages(
            x["intermediate_steps"]
        ),
        "chat_history": lambda x: x["chat_history"],
    }
    | prompt
    | model_with_tools
    | OpenAIToolsAgentOutputParser()
)


agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


class Input(BaseModel):
    input: str
    chat_history: List[Union[HumanMessage, AIMessage, FunctionMessage]] = Field(
        ...,
        extra={"widget": {"type": "chat", "input": "input", "output": "output"}},
    )


class Output(BaseModel):
    output: Any


class InputChat(TypedDict):
    """Input for the chat endpoint."""

    input: str
    """Human input"""


executer_with_history = RunnableWithMessageHistory(
    agent_executor,
    create_session_factory("chat_histories"),
    input_messages_key="input",
    history_messages_key="chat_history",
    history_factory_config=[
        ConfigurableFieldSpec(
            id="userId",
            annotation=str,
            name="User ID",
            description="Unique identifier for the user.",
            default="",
            is_shared=True,
        ),
        ConfigurableFieldSpec(
            id="conversationId",
            annotation=str,
            name="Conversation ID",
            description="Unique identifier for the conversation.",
            default="",
            is_shared=True,
        ),
    ],
).with_types(input_type=InputChat)
