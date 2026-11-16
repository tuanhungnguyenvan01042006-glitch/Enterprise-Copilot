from langchain_core.documents import Document
import pytest

from app.RAG.Embedding.types import EmbeddedPoint, EmbeddingItem
from app.RAG.Embedding.validation import (
    EmbeddingInputValidationError,
    build_embedding_item,
    validate_chunk,
    validate_embedded_point,
    validate_embedding_item,
)


def valid_chunk(**overrides) -> Document:
    metadata = {
        "document_id": "doc-1",
        "chunk_id": "chunk-1",
        "chunk_index": 0,
        "block_type": "text",
        "token_count": 5,
        "section_path": "Security > Password Policy",
        "source_start": 0,
        "source_end": 20,
        "knowledge_scope": "COMPANY",
        "department_id": None,
        "title": "Password Policy",
        "category": "POLICY",
        "storage_key": "COMPANY/doc-1/file.md",
    }
    metadata.update(overrides)
    return Document(page_content="Use a strong password.", metadata=metadata)


def test_valid_chunk_builds_minimal_embedding_item() -> None:
    item = build_embedding_item(valid_chunk())

    assert item == EmbeddingItem(
        point_id="chunk-1",
        text="Use a strong password.",
        metadata={
            "document_id": "doc-1",
            "chunk_id": "chunk-1",
            "chunk_index": 0,
            "block_type": "text",
            "token_count": 5,
            "section_path": "Security > Password Policy",
            "source_start": 0,
            "source_end": 20,
            "knowledge_scope": "COMPANY",
            "department_id": None,
            "title": "Password Policy",
            "category": "POLICY",
        },
    )
    assert "storage_key" not in item.metadata


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("chunk_id", "", "chunk_id: must be a non-empty string"),
        ("chunk_index", -1, "chunk_index: must be greater than or equal to 0"),
        ("block_type", "image", "block_type: must be one of: code, mermaid, table, text"),
        ("token_count", 0, "token_count: must be greater than or equal to 1"),
        ("source_end", 0, "source_end: must be greater than or equal to 1"),
        (
            "knowledge_scope",
            "PRIVATE",
            "knowledge_scope: must be one of: COMPANY, DEPARTMENT",
        ),
    ],
)
def test_invalid_chunk_reports_specific_field_error(field, value, message) -> None:
    chunk = valid_chunk(**{field: value})
    if field == "knowledge_scope":
        chunk.metadata["department_id"] = None

    with pytest.raises(EmbeddingInputValidationError, match=message):
        validate_chunk(chunk)


def test_empty_content_is_rejected() -> None:
    base = valid_chunk()
    chunk = Document(page_content="  ", metadata=base.metadata)

    with pytest.raises(
        EmbeddingInputValidationError,
        match="page_content: must not be empty",
    ):
        validate_chunk(chunk)


def test_department_scope_requires_department_id() -> None:
    chunk = valid_chunk(knowledge_scope="DEPARTMENT", department_id=None)

    with pytest.raises(
        EmbeddingInputValidationError,
        match="department_id: must be an integer",
    ):
        validate_chunk(chunk)


def test_embedding_item_requires_non_empty_text() -> None:
    item = EmbeddingItem(point_id="chunk-1", text=" ", metadata={})

    with pytest.raises(
        EmbeddingInputValidationError,
        match="text: must be a non-empty string",
    ):
        validate_embedding_item(item)


def test_embedded_point_rejects_non_finite_vector_values() -> None:
    point = EmbeddedPoint(
        point_id="chunk-1",
        vector=[0.1, float("nan")],
        text="content",
        metadata={},
    )

    with pytest.raises(
        EmbeddingInputValidationError,
        match="vector: must contain only finite numeric values",
    ):
        validate_embedded_point(point)
