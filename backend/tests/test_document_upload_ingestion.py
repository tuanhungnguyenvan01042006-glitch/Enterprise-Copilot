import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import documents as documents_route
from app.models.document import Document
from app.RAG.Chunking import markdown_tables, recursive_text
from app.RAG.Chunking import pipeline as chunking_pipeline
from app.RAG.Ingestion import pipeline as ingestion_pipeline
from app.RAG.Embedding import voyage_langchain
from app.RAG import pipeline as rag_pipeline
from qdrant_client import QdrantClient


def count_words(text: str) -> int:
    return len(text.split())


class FakeSession:
    def __init__(self, user: SimpleNamespace) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.user = user

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        document = self.added[-1]
        if isinstance(document, Document) and document.id is None:
            document.id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, value: object) -> None:
        now = datetime.now(timezone.utc)
        for field in ("uploaded_at", "created_at", "updated_at"):
            if getattr(value, field, None) is None:
                setattr(value, field, now)
        if getattr(value, "revision", None) is None:
            value.revision = 1

    def get(self, _model: object, _identity: object) -> SimpleNamespace:
        return self.user

    def rollback(self) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def scalar(self, statement):
        return next((item for item in self.added if isinstance(item, Document)), None)


def _principal() -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            full_name="API Test Admin",
            account_type="ADMIN",
            department_id=None,
            department_role=None,
        )
    )


def test_document_upload_runs_registered_ingestion_and_chunking_task(
    tmp_path: Path, monkeypatch
) -> None:
    settings = SimpleNamespace(
        app_env="development",
        upload_dir=tmp_path / "storage" / "uploads",
        max_upload_bytes=10 * 1024 * 1024,
    )
    monkeypatch.setattr(documents_route, "get_settings", lambda: settings)
    monkeypatch.setattr(ingestion_pipeline, "get_settings", lambda: settings)
    monkeypatch.setattr(recursive_text, "count_voyage_tokens", count_words)
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    monkeypatch.setattr(chunking_pipeline, "count_voyage_tokens", count_words)
    monkeypatch.setattr(documents_route, "_audit", lambda *args, **kwargs: None)
    embedded_texts = []

    def fake_model(name):
        assert name == "voyage-4"
        def embed_documents(texts):
            embedded_texts.extend(texts)
            return [[0.1] * 1024 for _ in texts]
        return SimpleNamespace(embed_documents=embed_documents)

    monkeypatch.setattr(voyage_langchain, "_model", fake_model)
    qdrant = QdrantClient(":memory:")
    monkeypatch.setattr(qdrant, "close", lambda: None)
    monkeypatch.setattr(rag_pipeline, "QdrantClient", lambda **kwargs: qdrant)
    monkeypatch.setattr(rag_pipeline, "get_settings", lambda: SimpleNamespace(qdrant_url="local", qdrant_collection="docs"))

    source = (
        "---\n"
        "title: Uploaded policy\n"
        "---\n\n"
        "<!-- remove this comment -->\n"
        "# Password Policy\n\n"
        + " ".join(["Use a strong password."] * 80)
        + "\n\n"
        "| Rule | Value |\n| --- | --- |\n| Rotation | 90 days |\n"
    )
    principal = _principal()
    db = FakeSession(principal.user)
    monkeypatch.setattr(rag_pipeline, "SessionLocal", lambda: db)
    app = FastAPI()
    app.include_router(documents_route.router, prefix="/api/v1")
    app.dependency_overrides[documents_route.validate_csrf] = lambda: principal
    app.dependency_overrides[documents_route.get_db] = lambda: db

    with TestClient(app) as client:
        http_response = client.post(
            "/api/v1/documents",
            data={
                "metadata": json.dumps(
                    {
                        "title": "Uploaded policy",
                        "description": "Policy uploaded by the API test.",
                        "category": "POLICY",
                        "knowledge_scope": "COMPANY",
                        "language": "en",
                        "department_id": None,
                    }
                )
            },
            files={
                "file": (
                    "password-policy.md",
                    source.encode("utf-8"),
                    "text/markdown",
                )
            },
        )

    assert http_response.status_code == 201, http_response.text
    response = http_response.json()
    assert db.commits == 1
    document_id = response["id"]

    processed_dir = settings.upload_dir.parent / "processed"
    cleaned_file = processed_dir / "cleaned" / f"{document_id}.md"
    chunks_file = processed_dir / "chunks" / f"{document_id}.jsonl"
    assert cleaned_file.exists()
    assert chunks_file.exists()

    saved_chunks = [json.loads(line) for line in chunks_file.read_text(encoding="utf-8").splitlines()]
    assert len(saved_chunks) > 1
    assert all(chunk["metadata"]["document_id"] == document_id for chunk in saved_chunks)
    assert all(chunk["metadata"]["chunk_id"] for chunk in saved_chunks)
    assert all(chunk["metadata"]["token_count"] == count_words(chunk["page_content"]) for chunk in saved_chunks)
    assert "remove this comment" not in cleaned_file.read_text(encoding="utf-8")
    assert any(chunk["metadata"]["block_type"] == "table" for chunk in saved_chunks)
    assert len(embedded_texts) == len(saved_chunks)
    assert all(text.strip() for text in embedded_texts)
    assert qdrant.count("docs", exact=True).count == len(saved_chunks)
    records, _ = qdrant.scroll("docs", limit=100, with_payload=True)
    assert all(record.payload["document_id"] == document_id for record in records)
    assert all(record.payload["text"] for record in records)


def test_replace_document_file_runs_embedding(tmp_path: Path, monkeypatch) -> None:
    settings = SimpleNamespace(
        app_env="development", upload_dir=tmp_path / "uploads",
        max_upload_bytes=10 * 1024 * 1024,
    )
    monkeypatch.setattr(documents_route, "get_settings", lambda: settings)
    monkeypatch.setattr(ingestion_pipeline, "get_settings", lambda: settings)
    monkeypatch.setattr(recursive_text, "count_voyage_tokens", count_words)
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    monkeypatch.setattr(chunking_pipeline, "count_voyage_tokens", count_words)
    monkeypatch.setattr(documents_route, "_audit", lambda *args, **kwargs: None)
    embedded_texts = []

    def embed_documents(texts):
        embedded_texts.extend(texts)
        return [[0.1] * 1024 for _ in texts]

    monkeypatch.setattr(voyage_langchain, "_model", lambda name: SimpleNamespace(embed_documents=embed_documents))
    principal = _principal()
    db = FakeSession(principal.user)
    now = datetime.now(timezone.utc)
    document = Document(
        id=uuid.uuid4(), knowledge_scope="COMPANY", department_id=None,
        title="Policy", category="POLICY", language="en", created_by=principal.user.id,
        updated_by=principal.user.id, revision=1, created_at=now, updated_at=now,
        storage_key="old/file.md", original_filename="old.md", mime_type="text/markdown",
        size_bytes=1, checksum_sha256="old", uploaded_by=principal.user.id, uploaded_at=now,
    )
    db.scalar = lambda statement: document
    qdrant = QdrantClient(":memory:")
    monkeypatch.setattr(qdrant, "close", lambda: None)
    monkeypatch.setattr(rag_pipeline, "QdrantClient", lambda **kwargs: qdrant)
    monkeypatch.setattr(rag_pipeline, "get_settings", lambda: SimpleNamespace(qdrant_url="local", qdrant_collection="docs"))
    monkeypatch.setattr(rag_pipeline, "SessionLocal", lambda: db)
    app = FastAPI()
    app.include_router(documents_route.router, prefix="/api/v1")
    app.dependency_overrides[documents_route.validate_csrf] = lambda: principal
    app.dependency_overrides[documents_route.get_db] = lambda: db

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/documents/{document.id}/file", data={"expected_revision": "1"},
            files={"file": ("policy.md", b"# Policy\n\nNew password policy.", "text/markdown")},
        )

    assert response.status_code == 200, response.text
    assert db.commits == 1
    assert embedded_texts == ["Policy\n\nNew password policy."]
    assert qdrant.count("docs", exact=True).count == 1
