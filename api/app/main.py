from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import logging_filters
from app.config import settings
from app.db import create_pool
from app.demo import router as demo
from app.nominatim import Nominatim
from app.routers import data, geo, guide, summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging_filters.install()
    app.state.pool = create_pool()
    await app.state.pool.open(wait=False)
    app.state.nominatim = Nominatim()
    try:
        yield
    finally:
        await app.state.nominatim.aclose()
        await app.state.pool.close()


# API docs only outside production (audit A4)
_docs = settings.app_env != "production"
app = FastAPI(
    title="KryzIO API",
    lifespan=lifespan,
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
    openapi_url="/openapi.json" if _docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(geo.router)
app.include_router(guide.router)
app.include_router(summary.router)
app.include_router(demo.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "demo_mode": settings.demo_mode}
