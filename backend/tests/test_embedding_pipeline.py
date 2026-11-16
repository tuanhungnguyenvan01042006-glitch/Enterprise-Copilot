from langchain_core.documents import Document
import pytest

from app.RAG.Embedding.cleaner import EMBEDDED_CONTENT_PLACEHOLDER
from app.RAG.Embedding.pipeline import prepare_chunks


def chunk(text: str, chunk_id: str = "chunk-1") -> Document:
    return Document(page_content=text, metadata={
        "document_id": "doc-1", "chunk_id": chunk_id, "chunk_index": 0,
        "block_type": "text", "token_count": 5, "section_path": "Policy",
        "source_start": 0, "source_end": 20, "knowledge_scope": "COMPANY",
        "department_id": None, "title": "Policy", "category": None,
        "storage_key": "private/path",
    })


def test_prepares_valid_chunks_and_reports_invalid_ones() -> None:
    original = chunk("## **Policy** [Read more](https://example.com)")
    invalid = chunk("content", "")
    empty = chunk(EMBEDDED_CONTENT_PLACEHOLDER, "chunk-3")
    last = chunk("Valid text", "chunk-4")

    prepared, errors = prepare_chunks([original, invalid, empty, last])

    assert [entry.item.point_id for entry in prepared] == ["chunk-1", "chunk-4"]
    assert prepared[0].item.text == "Policy Read more"
    assert prepared[0].original_text == original.page_content
    assert "storage_key" not in prepared[0].item.metadata
    assert [(error.index, error.chunk_id, error.reason) for error in errors] == [
        (1, "", "chunk_id: must be a non-empty string"),
        (2, "chunk-3", "text: empty after embedding cleaning"),
    ]
    assert all(error.document_id == "doc-1" for error in errors)
    assert original.page_content.startswith("## **Policy**")


def test_missing_metadata_and_empty_input_are_reported() -> None:
    missing = Document(page_content="content", metadata={})
    blank = chunk("   ")
    prepared, errors = prepare_chunks([missing, blank])

    assert prepared == []
    assert errors[0].chunk_id is None
    assert "missing required fields" in errors[0].reason
    assert errors[1].reason == "page_content: must not be empty"
    assert prepare_chunks([]) == ([], [])


def test_unexpected_errors_are_not_swallowed(monkeypatch) -> None:
    def fail(_item):
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr("app.RAG.Embedding.pipeline.clean_embedding_item", fail)
    with pytest.raises(RuntimeError, match="unexpected failure"):
        prepare_chunks([chunk("content")])
