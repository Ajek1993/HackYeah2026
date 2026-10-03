from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.chat import ChatRequest, ChatResponse, ChatService
from app.config import settings
from app.llm import GLMClient, LLMUnavailableError
from app.prompt import AGENT_UNAVAILABLE_MESSAGE
from app.session import SessionStore
from app.tools import ToolExecutor

app = FastAPI(title="KryzIO Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@lru_cache
def get_sessions() -> SessionStore:
    return SessionStore()


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService(GLMClient(), ToolExecutor(), get_sessions())


@app.exception_handler(LLMUnavailableError)
def llm_unavailable(request: Request, exc: LLMUnavailableError) -> JSONResponse:
    # Intentionally not logged: the failed request may contain the user's address.
    return JSONResponse(
        status_code=503,
        content={"error": "agent_unavailable", "message": AGENT_UNAVAILABLE_MESSAGE},
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": settings.glm_model}


@app.post("/chat")
def chat(
    request: ChatRequest, service: Annotated[ChatService, Depends(get_chat_service)]
) -> ChatResponse:
    return service.reply(request)


@app.delete("/chat/{session_id}", status_code=204)
def clear_chat(
    session_id: str, sessions: Annotated[SessionStore, Depends(get_sessions)]
) -> Response:
    sessions.clear(session_id)
    return Response(status_code=204)
