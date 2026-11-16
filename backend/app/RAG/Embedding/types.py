"""Small data contracts used at the embedding pipeline boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EmbeddingItem:
    """Validated text and metadata ready for an embedding provider.

    ``text`` contains the chunk content after embedding-specific cleanup.
    """

    point_id: str
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EmbeddedPoint:
    """A vector plus the original chunk text and vector-store metadata."""

    point_id: str
    vector: list[float]
    text: str
    metadata: dict[str, Any]
