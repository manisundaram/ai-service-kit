"""Vector store model shapes shared by concrete implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class DocumentRecord:
    """A stored or returned document record."""

    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    chunk_index: int | None = None


@dataclass(slots=True, frozen=True)
class SearchResult(DocumentRecord):
    """A search result with similarity metadata."""

    similarity_score: float = 0.0


@dataclass(slots=True, frozen=True)
class IndexResult:
    """Outcome of an indexing operation."""

    indexed_count: int
    chunk_count: int
    collection_name: str
    embedding_model: str | None = None
    chunk_ids: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class CollectionInfo:
    """Metadata about a vector collection."""

    name: str
    document_count: int
    embedding_dimension: int
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
