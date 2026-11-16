import math

import pytest
from langchain_core.documents import Document

from app.RAG.Embedding import voyage


def chunk(document_id, chunk_id, index, text):
    return Document(page_content=text, metadata={
        "document_id": document_id, "chunk_id": chunk_id, "chunk_index": index,
        "block_type": "text", "token_count": 1, "section_path": "",
        "source_start": index, "source_end": index + 1, "knowledge_scope": "COMPANY",
        "department_id": None, "title": "Title", "category": None,
    })


def test_documents_and_query_use_correct_models(monkeypatch):
    requests = []
    monkeypatch.setattr(voyage, "count_voyage_tokens", lambda text: 1)

    def post(path, payload):
        requests.append((path, payload))
        if payload["input_type"] == "document":
            rows = [{"index": i, "embedding": [float(i)] * 1024}
                    for i, _ in enumerate(payload["input"])]
            return {"data": rows[::-1]}
        return {"data": [{"index": 0, "embedding": [0.25] * 1024}]}

    monkeypatch.setattr(voyage, "_post", post)
    chunks = [chunk("doc-a", "a2", 1, "**Second**"),
              chunk("doc-b", "b1", 0, "Other"),
              chunk("doc-a", "a1", 0, "First"),
              chunk("doc-a", "bad", 2, " ")]
    points, errors = voyage.embed_chunks(chunks)
    query = voyage.embed_query("Find policy")

    assert [point.point_id for point in points] == ["a2", "b1", "a1"]
    assert points[0].text == "**Second**"
    assert points[1].vector == [1.0] * 1024
    assert errors[0].chunk_id == "bad"
    assert requests[0][0] == "embeddings"
    assert requests[0][1]["input"] == ["Second", "Other", "First"]
    assert requests[0][1]["model"] == "voyage-4"
    assert requests[0][1]["input_type"] == "document"
    assert requests[0][1]["truncation"] is False
    assert requests[1][1]["model"] == "voyage-4-lite"
    assert requests[1][1]["input_type"] == "query"
    assert requests[1][1]["truncation"] is False
    assert len(query) == 1024


def test_chunks_are_split_into_bounded_batches(monkeypatch):
    monkeypatch.setattr(voyage, "_BATCH_TOKEN_BUDGET", 2)
    monkeypatch.setattr(voyage, "count_voyage_tokens", lambda text: 1)
    groups = []
    monkeypatch.setattr(voyage, "_embed_group", lambda group: groups.append(group) or [])
    voyage.embed_chunks([chunk("d", str(i), i, "text") for i in range(3)])
    assert [len(group) for group in groups] == [2, 1]


def test_rejects_bad_provider_response_and_query(monkeypatch):
    with pytest.raises(ValueError, match="non-empty"):
        voyage.embed_query("  ")
    monkeypatch.setattr(voyage, "_post", lambda *_: {"data": [{"index": 0, "embedding": [1]}]})
    with pytest.raises(ValueError, match="dimension"):
        voyage.embed_query("query")
    monkeypatch.setattr(voyage, "_post", lambda *_: {"data": [{"index": 0, "embedding": [math.nan] * 1024}]})
    with pytest.raises(ValueError, match="invalid"):
        voyage.embed_query("query")


def test_end_to_end_entry_point_calls_ingestion_and_embedding(monkeypatch):
    from app.RAG import pipeline
    chunks = [chunk("d", "c", 0, "text")]
    monkeypatch.setattr(pipeline, "ingest_document", lambda path, **kwargs: chunks)
    monkeypatch.setattr(pipeline, "embed_chunks", lambda items: (items, []))
    assert pipeline.ingest_and_embed_document("file.md", document_id="d") == (chunks, [])


def test_http_request_uses_key_and_propagates_api_errors(monkeypatch):
    import httpx

    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    def post(url, **kwargs):
        assert url == "https://api.voyageai.com/v1/embeddings"
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"
        assert kwargs["json"]["input"] == ["query"]
        return httpx.Response(429, request=httpx.Request("POST", url))

    monkeypatch.setattr(voyage.httpx, "post", post)
    with pytest.raises(httpx.HTTPStatusError):
        voyage.embed_query("query")
