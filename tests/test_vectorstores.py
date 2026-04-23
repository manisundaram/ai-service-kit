from ai_service_kit.vectorstores import CollectionInfo, IndexResult, SearchResult


def test_vectorstore_models_capture_common_fields() -> None:
    indexed = IndexResult(
        indexed_count=2,
        chunk_count=3,
        collection_name="docs",
        embedding_model="text-embedding-3-small",
        chunk_ids=("a", "b", "c"),
    )
    result = SearchResult(
        id="a",
        content="hello",
        metadata={"source": "unit-test"},
        similarity_score=0.92,
    )
    collection = CollectionInfo(
        name="docs",
        document_count=3,
        embedding_dimension=1536,
        metadata={"backend": "abstract"},
    )

    assert indexed.chunk_count == 3
    assert result.similarity_score == 0.92
    assert collection.embedding_dimension == 1536