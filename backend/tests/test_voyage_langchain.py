from types import SimpleNamespace

import pytest
import voyageai
from langchain_core.documents import Document

from app.RAG.Embedding import voyage_langchain


def chunk(text, chunk_id):
    return Document(page_content=text, metadata={
        "document_id": "doc-1", "chunk_id": chunk_id, "chunk_index": 0,
        "block_type": "text", "token_count": 1, "section_path": "",
        "source_start": 0, "source_end": 1, "knowledge_scope": "COMPANY",
        "department_id": None, "title": "Policy", "category": None,
    })


def test_langchain_calls_voyage_with_correct_models_and_preserves_chunks(monkeypatch):
    calls = []
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setattr(voyageai.Client, "tokenize", lambda self, texts, model: [[1] for _ in texts])

    def fake_embed(self, texts, **kwargs):
        calls.append((texts, kwargs))
        return SimpleNamespace(embeddings=[[float(i)] * 1024 for i in range(len(texts))])

    monkeypatch.setattr(voyageai.Client, "embed", fake_embed)
    points, errors = voyage_langchain.embed_chunks([
        chunk("**Policy**", "one"), chunk("   ", "bad"), chunk("Another", "two"),
    ])
    query = voyage_langchain.embed_query("Question?")

    assert [point.point_id for point in points] == ["one", "two"]
    assert points[0].text == "**Policy**"
    assert points[1].vector == [1.0] * 1024
    assert errors[0].chunk_id == "bad"
    assert calls[0] == (["Policy", "Another"], {
        "model": "voyage-4", "input_type": "document",
        "truncation": False, "output_dimension": 1024,
    })
    assert calls[1] == (["Question?"], {
        "model": "voyage-4-lite", "input_type": "query",
        "truncation": False, "output_dimension": 1024,
    })
    assert len(query) == 1024


def test_invalid_results_and_empty_inputs(monkeypatch):
    assert voyage_langchain.embed_chunks([]) == ([], [])
    with pytest.raises(ValueError, match="non-empty"):
        voyage_langchain.embed_query(" ")

    monkeypatch.setattr(voyage_langchain, "_model", lambda name: SimpleNamespace(
        embed_documents=lambda texts: [], embed_query=lambda text: [float("nan")] * 1024,
    ))
    with pytest.raises(ValueError, match="number of embeddings"):
        voyage_langchain.embed_chunks([chunk("content", "one")])
    with pytest.raises(ValueError, match="invalid query embedding"):
        voyage_langchain.embed_query("Question?")


def test_langchain_batches_large_input(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setattr(voyageai.Client, "tokenize", lambda self, texts, model: [[1] for _ in texts])
    batch_sizes = []

    def fake_embed(self, texts, **kwargs):
        batch_sizes.append(len(texts))
        return SimpleNamespace(embeddings=[[0.0] * 1024 for _ in texts])

    monkeypatch.setattr(voyageai.Client, "embed", fake_embed)
    points, errors = voyage_langchain.embed_chunks(
        [chunk("content", str(index)) for index in range(1001)]
    )
    assert len(points) == 1001
    assert errors == []
    assert batch_sizes == [1000, 1]
