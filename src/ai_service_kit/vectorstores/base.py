"""Vector store interface extracted from concrete application code."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

from .models import CollectionInfo, IndexResult, SearchResult


class VectorStore(ABC):
    """Abstract contract for vector store implementations."""

    @abstractmethod
    async def index_documents(
        self,
        documents: Sequence[Mapping[str, Any]],
        collection_name: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> IndexResult:
        """Index documents into a collection."""

    @abstractmethod
    async def search(
        self,
        query: str,
        k: int = 5,
        collection_name: str | None = None,
        filter_metadata: Mapping[str, Any] | None = None,
        similarity_threshold: float | None = None,
    ) -> list[SearchResult]:
        """Search for similar documents in a collection."""

    @abstractmethod
    def get_collection_info(self, collection_name: str | None = None) -> CollectionInfo:
        """Return metadata about a collection."""

    @abstractmethod
    def list_collections(self) -> list[CollectionInfo]:
        """Return all known collection descriptors."""

    @abstractmethod
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection if it exists."""

    @abstractmethod
    def reset_collection(self, collection_name: str | None = None) -> str:
        """Reset a collection to a clean state and return its name."""
