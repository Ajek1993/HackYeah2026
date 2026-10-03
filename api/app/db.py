import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import settings


def get_conn():
    """Sync connection for Celery tasks."""
    return psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=5)


def create_pool() -> AsyncConnectionPool:
    """Async pool for API endpoints; opened and closed in the FastAPI lifespan."""
    return AsyncConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=10,
        open=False,
        timeout=5,
        kwargs={"row_factory": dict_row, "connect_timeout": 5},
    )
