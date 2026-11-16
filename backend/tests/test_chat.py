import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.exceptions import HTTPException

from app.api.routes import chat
from app.core.auth import require_principal
from app.core.errors import http_exception_handler, validation_exception_handler
from app.db.base import Base
from app.db.session import get_db
from app.models.chat import ChatConversation, ChatMessage


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture
def setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # The user table is not needed by these route tests.
    ChatConversation.__table__.create(engine)
    ChatMessage.__table__.create(engine)
    sessions = sessionmaker(bind=engine)
    principal = SimpleNamespace(user=SimpleNamespace(id=uuid.uuid4(), account_type="STAFF", must_change_password=False), session=SimpleNamespace(csrf_token="token"))
    app = FastAPI()
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(chat.router, prefix="/api/v1")

    def database():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[require_principal] = lambda: principal
    with TestClient(app) as client:
        yield client, principal, sessions
    engine.dispose()


HEADERS = {"Origin": "http://localhost:8080", "X-CSRF-Token": "token"}
ROOT = "/api/v1/chat/conversations"


def test_conversation_turn_history_and_ownership(setup, monkeypatch):
    client, principal, sessions = setup
    monkeypatch.setattr(chat, "answer_question", lambda query: {
        "answer": "Answer [1]",
        "sources": [{"number": 1, "document_id": "doc-1", "title": "Policy", "section_path": "Leave", "chunk_id": "private", "text": "secret"}],
    })
    created = client.post(ROOT, headers=HEADERS)
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    assert client.post(f"{ROOT}/{conversation_id}/messages", json={"content": "   "}, headers=HEADERS).status_code == 422
    assert client.post(f"{ROOT}/{conversation_id}/messages", json={"content": "x" * 4001}, headers=HEADERS).status_code == 422
    turn = client.post(f"{ROOT}/{conversation_id}/messages", json={"content": "  Question  "}, headers=HEADERS)
    assert turn.status_code == 201
    assert turn.json()["user_message"]["content"] == "Question"
    assert turn.json()["assistant_message"]["sources"] == [{"number": 1, "document_id": "doc-1", "title": "Policy", "section_path": "Leave"}]
    detail = client.get(f"{ROOT}/{conversation_id}").json()
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
    assert client.get(ROOT).json()[0]["title"] == "Question"
    owner = principal.user.id
    principal.user.id = uuid.uuid4()
    assert client.get(f"{ROOT}/{conversation_id}").status_code == 404
    assert client.delete(f"{ROOT}/{conversation_id}", headers=HEADERS).status_code == 404
    principal.user.id = owner
    assert client.delete(f"{ROOT}/{conversation_id}", headers=HEADERS).status_code == 204


def test_csrf_auth_and_rag_failure_leave_no_messages(setup, monkeypatch):
    client, principal, _ = setup
    assert client.post(ROOT).status_code == 403
    principal.user.account_type = "ADMIN"
    assert client.post(ROOT, headers=HEADERS).status_code == 403
    principal.user.account_type = "STAFF"
    conversation_id = client.post(ROOT, headers=HEADERS).json()["id"]
    def fail(_query):
        raise RuntimeError("secret provider details")
    monkeypatch.setattr(chat, "answer_question", fail)
    response = client.post(f"{ROOT}/{conversation_id}/messages", json={"content": "Question"}, headers=HEADERS)
    assert response.status_code == 503
    assert "secret provider details" not in response.text
    assert client.get(f"{ROOT}/{conversation_id}").json()["messages"] == []
    client.app.dependency_overrides.pop(require_principal)
    assert client.get(ROOT).status_code == 401
