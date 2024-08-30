from fastapi import FastAPI, Header, HTTPException, Depends, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from langserve import add_routes
from app.agent import executer_with_history
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing_extensions import Annotated
import jwt
from jwt import PyJWTError, ExpiredSignatureError, InvalidTokenError
import os
from app.history import chat_history, user_history
from app.share import set_public, get_public, set_private
from app.summary import create_summary
from typing import List
from pydantic import BaseModel
import asyncio
from langserve import APIHandler
from sse_starlette import EventSourceResponse


async def verify_token(Authorization: Annotated[str | None, Header()] = None) -> None:
    if not Authorization:
        raise HTTPException(status_code=403, detail="Authorization header missing")

    try:
        token = Authorization.split(" ")[1]  # Assuming "Bearer <token>" format
        decoded_token = jwt.decode(
            token,
            key=os.getenv("CLERK_PEM_PUBLIC_KEY"),
            algorithms=["RS256"],
            options={"verify_exp": True},  # Verify expiration
        )
        # Optionally, validate claims like 'aud' and 'iss' if needed.
    except (PyJWTError, ExpiredSignatureError, InvalidTokenError) as e:
        raise HTTPException(status_code=403, detail=f"Token is invalid: {str(e)}")


app = FastAPI(title="Holocaust Answer Engine", version="1.0.5")

authenticated = APIRouter(tags=["private"], dependencies=[Depends(verify_token)])

unauthenticated = APIRouter(tags=["public"])  # Change "public" to ["public"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://zekher.lukekosner.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@unauthenticated.get("/health")
async def health():
    return {"status": "ok"}


@unauthenticated.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


@authenticated.get("/user_history")
async def history_route(user_id: str, return_chats: bool = False):
    return await user_history(user_id, return_chats)


@authenticated.get("/chat_history")
async def chat_route(user_id: str, conversation_id: str):
    return await chat_history(user_id, conversation_id)


@authenticated.post("/share/set_public")
async def set_public_route(conversation_id: str, user_id: str):
    return await set_public(conversation_id, user_id)


@unauthenticated.get("/share/get_public")
async def get_public_route(conversation_id: str):
    return await get_public(conversation_id)


@unauthenticated.get("/share/get_history")
async def get_history_route(user_id: str, conversation_id: str):
    return await chat_history(user_id, conversation_id)


@authenticated.post("/share/set_private")
async def set_private_route(conversation_id: str, user_id: str):
    return await set_private(conversation_id, user_id)


class HistoriesRequest(BaseModel):
    histories: List[str]


@authenticated.post("/create_summary")
async def create_summary_route(body: HistoriesRequest):
    # Run create_summary for all histories concurrently
    summaries = await asyncio.gather(
        *[create_summary(history) for history in body.histories]
    )

    return summaries


@authenticated.post(
    "/chat/stream_events",
    summary="Stream Chat Events",
    description="This endpoint handles streaming chat events.",
    responses={
        200: {
            "description": "Stream successfully started.",
            "content": {"text/event-stream": {"example": "data: message"}},
        },
        401: {"description": "Unauthorized access."},
        500: {"description": "Internal server error."},
    },
)
async def v2_stream(request: Request) -> EventSourceResponse:
    """Handle stream request."""
    return await APIHandler(executer_with_history, path="/chat").astream_events(request)


app.include_router(authenticated)
app.include_router(unauthenticated)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=1122)
