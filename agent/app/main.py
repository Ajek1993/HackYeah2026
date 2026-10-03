from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.chat import ChatRequest, ChatResponse, ChatService
from app.config import settings
from app.llm import GLMClient, LLMUnavailableError
from app.prompt import AGENT_UNAVAILABLE_MESSAGE
from app.ratelimit import RateLimiter
from app.session import SESSION_ID_PATTERN, SessionStore
from app.tools import ToolExecutor

RATE_LIMITED_MESSAGE = "Za dużo pytań naraz. Spróbuj ponownie za chwilę."

# API docs only outside production (audit A4)
_docs = settings.app_env != "production"
app = FastAPI(
    title="KryzIO Agent",
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
    openapi_url="/openapi.json" if _docs else None,
)

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


@lru_cache
def get_chat_limiter() -> RateLimiter:
    return RateLimiter(settings.chat_rate_limit_per_minute)


def enforce_chat_limit(
    request: Request, limiter: Annotated[RateLimiter, Depends(get_chat_limiter)]
) -> None:
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(client):
        raise HTTPException(429, RATE_LIMITED_MESSAGE)


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


@app.post("/chat", dependencies=[Depends(enforce_chat_limit)])
async def chat(
    request: ChatRequest, service: Annotated[ChatService, Depends(get_chat_service)]
) -> ChatResponse:
    return await service.reply(request)


@app.delete("/chat/{session_id}", status_code=204)
def clear_chat(
    session_id: Annotated[str, Path(pattern=SESSION_ID_PATTERN)],
    sessions: Annotated[SessionStore, Depends(get_sessions)],
) -> Response:
    sessions.clear(session_id)
    return Response(status_code=204)
