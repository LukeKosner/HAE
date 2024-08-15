# 1. Handle Imports
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.upstash import UpstashVectorStore
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


# 2. Create Vector Database
loader = DirectoryLoader(
    f"{Path(__file__).parent}/optimized_sources",
    glob="**/*.txt",
    loader_cls=TextLoader,
)
fullDocs = loader.load()

fullDocVectorstore = UpstashVectorStore(
    embedding=OpenAIEmbeddings(),
    namespace="full",
)

# fullDocVectorstore.add_documents(fullDocs, batch_size=10)

# text_splitter = RecursiveCharacterTextSplitter(
#     chunk_size=1000, chunk_overlap=200, add_start_index=True
# )
# all_splits = text_splitter.split_documents(fullDocs)
splitDocVectorstore = UpstashVectorStore(
    embedding=OpenAIEmbeddings(),
    namespace="split",
)

# splitDocVectorstore.add_documents(all_splits)
