"""Contracts and validation for the embedding pipeline."""

from app.RAG.Embedding.types import EmbeddedPoint, EmbeddingItem
from app.RAG.Embedding.cleaner import (
    EMBEDDED_CONTENT_PLACEHOLDER,
    clean_embedding_item,
)
from app.RAG.Embedding.pipeline import PreparedChunk, PreparationError, prepare_chunks
from app.RAG.Embedding.validation import (
    EmbeddingInputValidationError,
    build_embedding_item,
    validate_chunk,
    validate_embedded_point,
    validate_embedding_item,
)

__all__ = [
    "EmbeddedPoint",
    "EMBEDDED_CONTENT_PLACEHOLDER",
    "EmbeddingInputValidationError",
    "EmbeddingItem",
    "PreparedChunk",
    "PreparationError",
    "build_embedding_item",
    "clean_embedding_item",
    "prepare_chunks",
    "validate_chunk",
    "validate_embedded_point",
    "validate_embedding_item",
]
