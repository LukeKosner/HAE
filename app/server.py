from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from langserve import add_routes
from app.agent import executer_with_history
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing_extensions import Annotated
import jwt
import os


async def verify_token(Authorization: Annotated[str, Header()]) -> None:
    try:
        print(Authorization)
        jwt.decode(
            Authorization, key=os.getenv("CLERK_PEM_PUBLIC_KEY"), algorithms=["RS256"]
        )
    except jwt.exceptions.PyJWTError:
        HTTPException(status_code=403, detail="Token is invalid")


app = FastAPI(dependencies=[Depends(verify_token)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://zekher.lukekosner.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


@app.get("/collections")
async def get_collections():
    return {
        "collections": [
            {
                "id": "boder",
                "name": "David Boder Collection",
            }
        ]
    }


add_routes(app, executer_with_history, path="/agent")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=1122)
