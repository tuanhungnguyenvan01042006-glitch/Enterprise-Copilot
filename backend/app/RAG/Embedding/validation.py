

# Tóm lại, đây là file kiểm tra đầu vào, đầu ra , và từng contract trong Module Embeding đã đúng chuẩn chưa , tránh việc cứ âm thầm Embed, mà có nhiều dữ liệu lỗi mà ko bt
# Thực tế, các hàm này chủ yếu là kiểm tra metadata xem đã chuẩn chưa

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from langchain_core.documents import Document

from app.RAG.Embedding.types import EmbeddedPoint, EmbeddingItem


ALLOWED_BLOCK_TYPES = frozenset({"text", "table", "code", "mermaid"})
ALLOWED_KNOWLEDGE_SCOPES = frozenset({"COMPANY", "DEPARTMENT"})

# These fields are produced by the existing Chunking pipeline or carried from
# the source Document metadata. ``storage_key`` is intentionally not part of
# the EmbeddingItem output metadata; it remains an internal document-storage
# concern.
REQUIRED_CHUNK_METADATA = (
    "document_id",
    "chunk_id",
    "chunk_index",
    "block_type",
    "token_count",
    "section_path",
    "source_start",
    "source_end",
    "knowledge_scope",
    "department_id",
    "title",
    "category",
)

# Keep this ordered so the serialized contract is deterministic in logs and
# previews. It intentionally excludes internal fields such as storage_key.
OUTPUT_METADATA_FIELDS = REQUIRED_CHUNK_METADATA


class EmbeddingInputValidationError(ValueError):
    """Raised when a chunk or embedding contract is invalid."""


def _fail(field: str, message: str) -> None:
    raise EmbeddingInputValidationError(f"{field}: {message}")
   # hàm in ra thông báo lỗi : trường dữ liệu nào đó bị lỗi với message gì đó


def _require_int(value: Any, *, field: str, minimum: int | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(field, "must be an integer")
    if minimum is not None and value < minimum:
        _fail(field, f"must be greater than or equal to {minimum}")


# Kiểm tra chunk đầu vào, nếu chunk đầu vào lỗi , thì in ra lỗi, chứ ko Embed
# Tóm lại là hàm kiểm tra đầu vào, trước khi đưa đi Embed
def validate_chunk(document: Document) -> None:
    if not isinstance(document, Document):
        _fail("document", "must be a langchain Document")
    if not isinstance(document.page_content, str):
        _fail("page_content", "must be a string")
    if not document.page_content.strip():
        _fail("page_content", "must not be empty")
    if not isinstance(document.metadata, Mapping):
        _fail("metadata", "must be a mapping")

    metadata = document.metadata
    missing = [field for field in REQUIRED_CHUNK_METADATA if field not in metadata]
    if missing:
        _fail("metadata", f"missing required fields: {', '.join(missing)}")

    for field in ("document_id", "chunk_id", "title"):
        value = metadata[field]
        if not isinstance(value, str) or not value.strip():
            _fail(field, "must be a non-empty string")

    _require_int(metadata["chunk_index"], field="chunk_index", minimum=0)
    _require_int(metadata["token_count"], field="token_count", minimum=1)
    _require_int(metadata["source_start"], field="source_start", minimum=0)
    _require_int(metadata["source_end"], field="source_end", minimum=1)
    if metadata["source_end"] <= metadata["source_start"]:
        _fail("source_end", "must be greater than source_start")

    block_type = metadata["block_type"]
    if block_type not in ALLOWED_BLOCK_TYPES:
        allowed = ", ".join(sorted(ALLOWED_BLOCK_TYPES))
        _fail("block_type", f"must be one of: {allowed}")

    section_path = metadata["section_path"]
    if not isinstance(section_path, str):
        _fail("section_path", "must be a string")

    scope = metadata["knowledge_scope"]
    if scope not in ALLOWED_KNOWLEDGE_SCOPES:
        allowed = ", ".join(sorted(ALLOWED_KNOWLEDGE_SCOPES))
        _fail("knowledge_scope", f"must be one of: {allowed}")

    department_id = metadata["department_id"]
    if scope == "COMPANY" and department_id is not None:
        _fail("department_id", "must be null for COMPANY documents")
    if scope == "DEPARTMENT":
        _require_int(department_id, field="department_id", minimum=1)

    category = metadata["category"]
    if category is not None and (not isinstance(category, str) or not category.strip()):
        _fail("category", "must be a non-empty string or null")

    # hàm xây dựng đối tượng Embeding Item 
  # Để hàm này ở đây ko hợp lý lắm
  # Hàm này biến 1 chunk thành Embedding item ( trước khi đi clean text của nó)
  # Thực tế, Embeding Item chỉ khác CHunk ở chỗ nó có ít metadata hơn, và đổi tên trường chunk id thành point id 
  # nên thực tế hàm này chức năng chính là để gọi hàm validate chunk : Kiểm tra input đầu vào oke chưa, trước khi đem đi clean
def build_embedding_item(document: Document) -> EmbeddingItem:
    """Build the minimal output contract from a validated chunk."""

    validate_chunk(document)
    metadata = {
        field: document.metadata[field]
        for field in OUTPUT_METADATA_FIELDS
    }
    return EmbeddingItem(
        point_id=document.metadata["chunk_id"],
        text=document.page_content,
        metadata=metadata,
    )

     # hàm kiểm tra Embeding item 
def validate_embedding_item(item: EmbeddingItem) -> None:
    """Validate the text/metadata contract before a model call."""

    if not isinstance(item, EmbeddingItem):
        _fail("embedding_item", "must be an EmbeddingItem")
    if not isinstance(item.point_id, str) or not item.point_id.strip():
        _fail("point_id", "must be a non-empty string")
    if not isinstance(item.text, str) or not item.text.strip():
        _fail("text", "must be a non-empty string")
    if not isinstance(item.metadata, dict):
        _fail("metadata", "must be a dictionary")
    missing = [field for field in REQUIRED_CHUNK_METADATA if field not in item.metadata]
    if missing:
        _fail("metadata", f"missing required fields: {', '.join(missing)}")
    if item.metadata["chunk_id"] != item.point_id:
        _fail("point_id", "must match metadata.chunk_id")
    if "storage_key" in item.metadata:
        _fail("metadata.storage_key", "must not be included in embedding output")

   #Kiểm tra đối tượng Embedded Point
def validate_embedded_point(point: EmbeddedPoint) -> None:
    """Validate a vector result before it is sent to a vector store."""

    if not isinstance(point, EmbeddedPoint):
        _fail("embedded_point", "must be an EmbeddedPoint")
    if not isinstance(point.point_id, str) or not point.point_id.strip():
        _fail("point_id", "must be a non-empty string")
    if not isinstance(point.text, str) or not point.text.strip():
        _fail("text", "must be a non-empty string")
    if not isinstance(point.vector, list) or not point.vector:
        _fail("vector", "must be a non-empty list")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        for value in point.vector
    ):
        _fail("vector", "must contain only finite numeric values")
    validate_embedding_item(
        EmbeddingItem(
            point_id=point.point_id,
            text=point.text,
            metadata=point.metadata,
        )
    )
