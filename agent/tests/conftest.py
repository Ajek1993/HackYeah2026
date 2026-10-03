import pytest
from fastapi.testclient import TestClient

from app.chat import ChatService
from app.main import app, get_chat_service, get_sessions
from app.session import SessionStore
from tests.test_chat import FakeTools


@pytest.fixture
def make_client():
    def factory(llm, tools=None, sessions=None, max_tool_rounds=5):
        sessions = sessions or SessionStore(ttl_seconds=60, max_messages=20)
        service = ChatService(llm, tools or FakeTools(), sessions, max_tool_rounds)
        app.dependency_overrides[get_chat_service] = lambda: service
        app.dependency_overrides[get_sessions] = lambda: sessions
        return TestClient(app)

    yield factory
    app.dependency_overrides.clear()
