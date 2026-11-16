from langchain_core.documents import Document
import pytest

from app.RAG.Chunking import markdown_tables, recursive_text
from app.RAG.Chunking.pipeline import chunk_document


def count_words(text: str) -> int:
    return len(text.split())


def test_short_text_and_structured_blocks_are_left_unchanged(monkeypatch):
    monkeypatch.setattr(recursive_text, "count_voyage_tokens", count_words)
    text = Document(page_content="short text", metadata={"block_type": "text"})
    table = Document(
        page_content="| " + "row " * 20,
        metadata={"block_type": "table"},
    )
    mermaid = Document(
        page_content="graph TD " + "node " * 20,
        metadata={"block_type": "mermaid"},
    )

    result = recursive_text.split_long_text_blocks(
        [text, table, mermaid], chunk_size=5, chunk_overlap=1
    )

    assert result == [text, table, mermaid]


def test_long_text_splits_by_token_count_and_inherits_parent_metadata(monkeypatch):
    monkeypatch.setattr(recursive_text, "count_voyage_tokens", count_words)
    parent = Document(
        page_content="one two three four five six seven eight nine ten eleven twelve",
        metadata={
            "block_type": "text",
            "document_id": "doc-1",
            "section_path": "Guide > Setup",
        },
    )

    chunks = recursive_text.split_long_text_blocks(
        [parent], chunk_size=5, chunk_overlap=2
    )

    assert len(chunks) > 1
    assert all(count_words(chunk.page_content) <= 5 for chunk in chunks)
    assert all(chunk.metadata == parent.metadata for chunk in chunks)
    assert all(chunk.page_content.strip() for chunk in chunks)
    assert any(
        set(left.page_content.split()[-2:]).issubset(set(right.page_content.split()[:3]))
        for left, right in zip(chunks, chunks[1:])
    )


def test_invalid_chunk_settings_are_rejected():
    for chunk_size, chunk_overlap in [(0, 0), (10, -1), (10, 10)]:
        with pytest.raises(ValueError):
            recursive_text.split_long_text_blocks(
                [], chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )


def test_chunk_document_runs_all_chunking_stages_and_adds_final_metadata(monkeypatch):
    monkeypatch.setattr(recursive_text, "count_voyage_tokens", count_words)
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    monkeypatch.setattr("app.RAG.Chunking.pipeline.count_voyage_tokens", count_words)

    long_text = " ".join(f"policy{i}" for i in range(45))
    source = Document(
        page_content=(
            "# Handbook\n\n## Procedures\n\n"
            f"{long_text}\n\n"
            "| Step | Action |\n| --- | --- |\n| 1 | Review |\n\n"
            "```mermaid\ngraph TD\n  A --> B\n```"
        ),
        metadata={"document_id": "doc-2", "category": None},
    )

    chunks = chunk_document(source, chunk_size=10, chunk_overlap=2)

    assert [chunk.metadata["chunk_index"] for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.metadata["document_id"] == "doc-2" for chunk in chunks)
    assert all(chunk.metadata["section_path"] == "Handbook > Procedures" for chunk in chunks)
    assert all(chunk.metadata["token_count"] == count_words(chunk.page_content) for chunk in chunks)
    assert all(
        0 <= chunk.metadata["source_start"] < chunk.metadata["source_end"] <= len(source.page_content)
        for chunk in chunks
    )
    assert len({chunk.metadata["chunk_id"] for chunk in chunks}) == len(chunks)

    text_chunks = [chunk for chunk in chunks if chunk.metadata["block_type"] == "text"]
    assert len(text_chunks) > 1
    assert all(chunk.metadata["token_count"] <= 10 for chunk in text_chunks)
    assert all(
        source.page_content[chunk.metadata["source_start"]:chunk.metadata["source_end"]]
        == chunk.page_content
        for chunk in text_chunks
    )
    assert any(chunk.metadata["block_type"] == "table" for chunk in chunks)
    assert any(chunk.metadata["block_type"] == "mermaid" for chunk in chunks)
    table_chunk = next(chunk for chunk in chunks if chunk.metadata["block_type"] == "table")
    mermaid_chunk = next(chunk for chunk in chunks if chunk.metadata["block_type"] == "mermaid")
    assert "| 1 | Review |" in table_chunk.page_content
    assert "| 1 | Review |" in source.page_content[
        table_chunk.metadata["source_start"]:table_chunk.metadata["source_end"]
    ]
    assert "A --> B" in mermaid_chunk.page_content
    assert source.page_content[
        mermaid_chunk.metadata["source_start"]:mermaid_chunk.metadata["source_end"]
    ].startswith("```mermaid")

    repeated_chunks = chunk_document(source, chunk_size=10, chunk_overlap=2)
    assert [chunk.metadata["chunk_id"] for chunk in chunks] == [
        chunk.metadata["chunk_id"] for chunk in repeated_chunks
    ]
