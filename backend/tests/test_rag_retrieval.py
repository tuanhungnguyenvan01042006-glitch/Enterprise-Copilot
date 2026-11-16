from types import SimpleNamespace
from uuid import uuid4

import pytest
from qdrant_client import QdrantClient, models

from app.RAG import service


def test_retrieval_queries_qdrant_and_preserves_order_and_payload(monkeypatch):
    client = QdrantClient(":memory:")
    client.create_collection("docs", vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE))
    client.upsert("docs", [
        models.PointStruct(id=str(uuid4()), vector=[1, 0], payload={"text": "first", "document_id": "a"}),
        models.PointStruct(id=str(uuid4()), vector=[0, 1], payload={"text": "second", "document_id": "b"}),
    ])
    monkeypatch.setattr(service, "embed_query", lambda query: [1, 0])
    monkeypatch.setattr(service, "get_settings", lambda: SimpleNamespace(qdrant_url="local", qdrant_collection="docs"))
    monkeypatch.setattr(service, "QdrantClient", lambda **kwargs: client)
    results = service.retrieve_chunks("test question", top_k=2)
    assert [result["text"] for result in results] == ["first", "second"]
    assert results[0]["document_id"] == "a"
    assert results[0]["score"] > results[1]["score"]


def test_retrieval_validates_limit_and_handles_empty_collection(monkeypatch):
    with pytest.raises(ValueError, match="top_k"):
        service.retrieve_chunks("query", 0)
    client = QdrantClient(":memory:")
    monkeypatch.setattr(service, "embed_query", lambda query: [1, 0])
    monkeypatch.setattr(service, "get_settings", lambda: SimpleNamespace(qdrant_url="local", qdrant_collection="missing"))
    monkeypatch.setattr(service, "QdrantClient", lambda **kwargs: client)
    assert service.retrieve_chunks("query") == []
