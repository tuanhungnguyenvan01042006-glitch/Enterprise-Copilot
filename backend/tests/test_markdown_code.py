from langchain_core.documents import Document

from app.RAG.Chunking import markdown_tables
from app.RAG.Chunking.markdown_code import split_section_preserving_structures
from app.RAG.Chunking.markdown_headers import split_document_by_markdown_headers


def count_words(text: str) -> int:
    return len(text.split())


def test_preserves_mermaid_with_section_and_intro_context(monkeypatch):
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    source = Document(
        page_content=(
            "## Decisions\n\n"
            "This diagram shows how to choose a channel.\n\n"
            "```mermaid\nflowchart TD\n  Start --> End\n```\n\n"
            "Additional guidance."
        ),
        metadata={"document_id": "doc-1"},
    )

    section = split_document_by_markdown_headers(source)[0]
    blocks = split_section_preserving_structures(section)
    diagram = next(block for block in blocks if block.metadata["block_type"] == "mermaid")

    assert [block.metadata["block_type"] for block in blocks] == ["text", "mermaid", "text"]
    assert diagram.page_content == (
        "Section: Decisions\n\n"
        "This diagram shows how to choose a channel.\n\n"
        "```mermaid\nflowchart TD\n  Start --> End\n```"
    )
    assert diagram.metadata["code_language"] == "mermaid"
    assert diagram.metadata["document_id"] == "doc-1"


def test_composes_table_and_code_preservation_in_source_order(monkeypatch):
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    source = Document(
        page_content=(
            "## Example\n\n"
            "| Name | Value |\n| --- | --- |\n| port | 8080 |\n\n"
            "Example configuration:\n\n"
            "```python\nPORT = 8080\n```"
        ),
        metadata={"document_id": "doc-2"},
    )

    section = split_document_by_markdown_headers(source)[0]
    blocks = split_section_preserving_structures(section)

    assert [block.metadata["block_type"] for block in blocks] == ["text", "table", "text", "code"]
    assert blocks[0].page_content == "## Example"
    assert "| port | 8080 |" in blocks[1].page_content
    assert blocks[2].page_content == "Example configuration:"
    assert blocks[3].page_content.endswith("```python\nPORT = 8080\n```")
    assert blocks[3].metadata["code_language"] == "python"
