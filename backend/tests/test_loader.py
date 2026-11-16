from pathlib import Path
from uuid import UUID

import pytest

from app.RAG.Ingestion.loader import (
    MarkdownLoadError,
    MarkdownValidationError,
    load_document,
    load_markdown_file,
    validate_markdown_file,
)


def _metadata() -> dict[str, object]:
    return {
        "document_id": UUID("11111111-1111-1111-1111-111111111111"),
        "knowledge_scope": "DEPARTMENT",
        "department_id": 1,
        "title": "Password Policy",
        "category": "POLICY",
        "storage_key": "DEPARTMENT/1/document/file.md",
    }


def test_load_document_returns_content_and_metadata(tmp_path: Path) -> None:
    source = tmp_path / "password-policy.md"
    source.write_text("# Password Policy\n\nUse a strong password.", encoding="utf-8")

    documents = load_document(source, **_metadata())

    assert len(documents) == 1
    assert documents[0].page_content == "# Password Policy\n\nUse a strong password."
    assert documents[0].metadata["source"] == "password-policy.md"
    assert documents[0].metadata["file_type"] == "markdown"
    assert documents[0].metadata["document_id"] == "11111111-1111-1111-1111-111111111111"
    assert documents[0].metadata["knowledge_scope"] == "DEPARTMENT"
    assert documents[0].metadata["department_id"] == 1
    assert documents[0].metadata["title"] == "Password Policy"
    assert documents[0].metadata["category"] == "POLICY"
    assert documents[0].metadata["storage_key"] == "DEPARTMENT/1/document/file.md"
    assert "original_filename" not in documents[0].metadata


def test_load_document_rejects_non_markdown_file(tmp_path: Path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("not markdown", encoding="utf-8")

    with pytest.raises(MarkdownValidationError, match=r"Only \.md files"):
        load_document(source, **_metadata())


def test_load_document_rejects_empty_file(tmp_path: Path) -> None:
    source = tmp_path / "empty.md"
    source.touch()

    with pytest.raises(MarkdownValidationError, match="must not be empty"):
        load_document(source, **_metadata())


def test_load_document_rejects_invalid_utf8(tmp_path: Path) -> None:
    source = tmp_path / "invalid.md"
    source.write_bytes(b"# Invalid\xff")

    with pytest.raises(MarkdownLoadError, match="valid UTF-8"):
        load_markdown_file(source)


def test_validate_markdown_file_rejects_file_over_limit(tmp_path: Path) -> None:
    source = tmp_path / "large.md"
    source.write_text("# Large", encoding="utf-8")

    with pytest.raises(MarkdownValidationError, match="exceeds the maximum size"):
        validate_markdown_file(source, max_size_bytes=1)
