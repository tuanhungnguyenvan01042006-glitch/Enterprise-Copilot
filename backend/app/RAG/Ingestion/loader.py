from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import UUID

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document


MARKDOWN_SUFFIX = ".md"
DEFAULT_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


class MarkdownValidationError(ValueError):
    """Raised when a Markdown file is invalid."""


class MarkdownLoadError(ValueError):
    """Raised when a valid Markdown file cannot be read."""


def validate_markdown_file(
    file_path: str | Path,
    *,
    max_size_bytes: int | None = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> Path:
    path = Path(file_path).expanduser()

    if path.suffix.lower() != MARKDOWN_SUFFIX:
        raise MarkdownValidationError("Only .md files are supported.")
    if max_size_bytes is not None and max_size_bytes <= 0:
        raise ValueError("max_size_bytes must be greater than zero or None.")

    try:
        path = path.resolve(strict=True)
        if not path.is_file():
            raise MarkdownValidationError("The Markdown path must point to a file.")
        size_bytes = path.stat().st_size
    except FileNotFoundError as exc:
        raise MarkdownValidationError("Markdown file does not exist.") from exc
    except OSError as exc:
        raise MarkdownValidationError("Markdown file cannot be accessed.") from exc

    if size_bytes == 0:
        raise MarkdownValidationError("Markdown file must not be empty.")
    if max_size_bytes is not None and size_bytes > max_size_bytes:
        raise MarkdownValidationError(
            f"Markdown file exceeds the maximum size of {max_size_bytes} bytes."
        )

    return path


def load_markdown_file(
    file_path: str | Path,
    *,
    metadata: Mapping[str, Any] | None = None,
    max_size_bytes: int | None = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> list[Document]:
    path = validate_markdown_file(file_path, max_size_bytes=max_size_bytes)

    try:
        documents = TextLoader(
            str(path),
            encoding="utf-8-sig",
            autodetect_encoding=False,
        ).load()
    except UnicodeDecodeError as exc:
        raise MarkdownLoadError("Markdown file must be valid UTF-8.") from exc
    except RuntimeError as exc:
        if isinstance(exc.__cause__, UnicodeDecodeError):
            raise MarkdownLoadError("Markdown file must be valid UTF-8.") from exc
        raise MarkdownLoadError("Markdown file cannot be read.") from exc
    except OSError as exc:
        raise MarkdownLoadError("Markdown file cannot be read.") from exc

    if not documents or not any(document.page_content.strip() for document in documents):
        raise MarkdownValidationError("Markdown file must contain text content.")

    document_metadata = {
        "source": path.name,
        "file_name": path.name,
        "file_type": "markdown",
    }
    document_metadata.update(metadata or {})

    for document in documents:
        document.metadata.update(document_metadata)

    return documents


def load_document(
    file_path: str | Path,
    *,
    document_id: UUID | str,
    knowledge_scope: str,
    department_id: int | None,
    title: str,
    category: str | None,
    storage_key: str,
    max_size_bytes: int | None = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> list[Document]:
    """Load one document with metadata from the backend Document record."""
    document_metadata = {
        "document_id": str(document_id),
        "knowledge_scope": knowledge_scope,
        "department_id": department_id,
        "title": title,
        "category": category,
        "storage_key": storage_key,
    }

    return load_markdown_file(
        file_path,
        metadata=document_metadata,
        max_size_bytes=max_size_bytes,
    )
