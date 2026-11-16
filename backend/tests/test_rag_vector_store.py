from uuid import uuid4

import pytest
from qdrant_client import QdrantClient, models

from app.RAG.Embedding.types import EmbeddedPoint
from app.RAG.vector_store import store_document_points


def point(document_id, chunk_id, text="Original text"):
    return EmbeddedPoint(point_id=chunk_id, vector=[0.5] * 1024, text=text, metadata={
        "document_id": document_id, "chunk_id": chunk_id, "chunk_index": 0,
        "block_type": "text", "token_count": 1, "section_path": "Policy",
        "source_start": 0, "source_end": 5, "knowledge_scope": "COMPANY",
        "department_id": None, "title": "Policy", "category": "POLICY",
    })


def test_store_rerun_and_replacement_preserve_other_documents():
    client = QdrantClient(":memory:")
    first, removed, other = (str(uuid4()) for _ in range(3))
    store_document_points(client, "docs", "doc-a", [point("doc-a", first), point("doc-a", removed)])
    store_document_points(client, "docs", "doc-b", [point("doc-b", other)])
    store_document_points(client, "docs", "doc-a", [point("doc-a", first), point("doc-a", removed)])
    assert client.count("docs", exact=True).count == 3

    store_document_points(client, "docs", "doc-a", [point("doc-a", first, "Updated text")])
    assert client.count("docs", exact=True).count == 2
    records = client.retrieve("docs", ids=[first, removed, other], with_payload=True)
    assert {str(record.id) for record in records} == {first, other}
    updated = next(record for record in records if str(record.id) == first)
    assert updated.payload["text"] == "Updated text"
    assert updated.payload["document_id"] == "doc-a"
    assert updated.payload["knowledge_scope"] == "COMPANY"
    assert updated.payload["section_path"] == "Policy"
    client.close()


def test_vectors_persist_after_client_reopens(tmp_path):
    chunk_id = str(uuid4())
    client = QdrantClient(path=str(tmp_path / "qdrant"))
    store_document_points(client, "docs", "doc-a", [point("doc-a", chunk_id)])
    client.close()
    reopened = QdrantClient(path=str(tmp_path / "qdrant"))
    records = reopened.retrieve("docs", ids=[chunk_id], with_payload=True, with_vectors=True)
    assert len(records) == 1
    assert records[0].payload["text"] == "Original text"
    assert len(records[0].vector) == 1024
    reopened.close()


def test_invalid_document_or_wrong_collection_does_not_delete_existing_points():
    client = QdrantClient(":memory:")
    chunk_id = str(uuid4())
    store_document_points(client, "docs", "doc-a", [point("doc-a", chunk_id)])
    with pytest.raises(ValueError, match="without valid chunks"):
        store_document_points(client, "docs", "doc-a", [])
    with pytest.raises(ValueError, match="document_id"):
        store_document_points(client, "docs", "doc-a", [point("doc-b", str(uuid4()))])
    assert client.count("docs", exact=True).count == 1
    client.create_collection("wrong", vectors_config=models.VectorParams(size=5, distance=models.Distance.COSINE))
    with pytest.raises(ValueError, match="1024-dimensional"):
        store_document_points(client, "wrong", "doc-a", [point("doc-a", str(uuid4()))])
    client.close()


def test_failed_upsert_keeps_existing_document(monkeypatch):
    client = QdrantClient(":memory:")
    old = str(uuid4())
    store_document_points(client, "docs", "doc-a", [point("doc-a", old)])

    def fail_upsert(**kwargs):
        raise RuntimeError("Qdrant unavailable")

    monkeypatch.setattr(client, "upsert", fail_upsert)
    with pytest.raises(RuntimeError, match="Qdrant unavailable"):
        store_document_points(client, "docs", "doc-a", [point("doc-a", str(uuid4()))])
    assert len(client.retrieve("docs", ids=[old])) == 1
    client.close()


def test_outdated_upload_does_not_write_to_qdrant(monkeypatch):
    from types import SimpleNamespace
    from app.RAG import pipeline

    doc_id = uuid4()
    current = SimpleNamespace(id=doc_id, storage_key="new.md", knowledge_scope="COMPANY",
                              department_id=None, title="Policy", category="POLICY")
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def scalar(self, statement): return current

    monkeypatch.setattr(pipeline, "ingest_and_embed_document", lambda *args, **kwargs: ([point(str(doc_id), str(uuid4()))], []))
    monkeypatch.setattr(pipeline, "SessionLocal", Session)
    def must_not_connect(**kwargs):
        raise AssertionError("outdated task should not connect")
    monkeypatch.setattr(pipeline, "QdrantClient", must_not_connect)
    pipeline.index_uploaded_document("old.md", document_id=str(doc_id), storage_key="old.md",
                                     knowledge_scope="COMPANY", department_id=None,
                                     title="Policy", category="POLICY")
