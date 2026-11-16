from langchain_core.documents import Document

from app.RAG.Chunking import markdown_tables
from app.RAG.Chunking.markdown_headers import split_document_by_markdown_headers


def count_words(text: str) -> int:
    return len(text.split())


def test_short_table_stays_whole_with_its_intro(monkeypatch):
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    document = Document(
        page_content=(
            "## Channels\n\n"
            "Choose a channel from this list.\n\n"
            "| Channel | Purpose |\n| --- | --- |\n| #help | Ask for help |\n\n"
            "Use the appropriate channel."
        ),
        metadata={"document_id": "doc-1", "title": "Handbook"},
    )

    section = split_document_by_markdown_headers(document)[0]
    blocks = markdown_tables.split_section_preserving_tables(section, max_tokens=80)
    tables = [block for block in blocks if block.metadata["block_type"] == "table"]

    assert len(tables) == 1
    assert "Choose a channel from this list." in tables[0].page_content
    assert "Section: Channels" in tables[0].page_content
    assert "| #help | Ask for help |" in tables[0].page_content
    assert tables[0].metadata["document_id"] == "doc-1"
    assert tables[0].metadata["section_path"] == "Channels"
    assert blocks[-1].page_content == "Use the appropriate channel."


def test_long_table_repeats_context_and_header_without_splitting_rows(monkeypatch):
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    rows = [
        "| #one | For support |",
        "| #two | For sales |",
        r"| #three | Red\|blue team |",
        "| #four | For finance |",
    ]
    section = Document(
        page_content=(
            "Choose a channel from this list.\n\n"
            "| Channel | Purpose |\n| --- | --- |\n"
            + "\n".join(rows)
        ),
        metadata={"document_id": "doc-1", "section_path": "Handbook > Channels"},
    )

    blocks = markdown_tables.split_section_preserving_tables(section, max_tokens=30)
    table_chunks = [block for block in blocks if block.metadata["block_type"] == "table"]

    assert len(table_chunks) > 1
    for chunk in table_chunks:
        assert chunk.page_content.count("| Channel | Purpose |") == 1
        assert chunk.page_content.count("| --- | --- |") == 1
        assert "Section: Handbook > Channels" in chunk.page_content
        assert "Choose a channel from this list." in chunk.page_content
        assert count_words(chunk.page_content) <= 30
    for row in rows:
        assert sum(row in chunk.page_content for chunk in table_chunks) == 1
    assert section.metadata == {"document_id": "doc-1", "section_path": "Handbook > Channels"}


def test_long_intro_is_kept_as_text_and_does_not_break_short_table(monkeypatch):
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    intro = " ".join(["Context"] * 30)
    section = Document(
        page_content=f"{intro}\n\n| A | B |\n| --- | --- |\n| x | y |",
        metadata={"section_path": "Examples"},
    )

    blocks = markdown_tables.split_section_preserving_tables(section, max_tokens=20)

    assert len(blocks) == 2
    assert blocks[0].page_content == intro
    assert blocks[1].page_content == "Section: Examples\n\n| A | B |\n| --- | --- |\n| x | y |"


def test_table_looking_text_inside_code_fence_is_not_treated_as_table(monkeypatch):
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    content = "```markdown\n| A | B |\n| --- | --- |\n| x | y |\n```"
    section = Document(page_content=content, metadata={"section_path": "Examples"})

    blocks = markdown_tables.split_section_preserving_tables(section)

    assert len(blocks) == 1
    assert blocks[0].page_content == content
    assert blocks[0].metadata["block_type"] == "text"


def test_two_tables_and_the_text_between_them_survive_header_splitting(monkeypatch):
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    document = Document(
        page_content=(
            "## Examples\n\n"
            "| A | B |\n| --- | --- |\n| one | first |\n\n"
            "Here is another example.\n\n"
            "| C | D |\n| --- | --- |\n| two | second |"
        )
    )

    section = split_document_by_markdown_headers(document)[0]
    blocks = markdown_tables.split_section_preserving_tables(section)

    assert [block.metadata["block_type"] for block in blocks] == ["text", "table", "text", "table"]
    assert blocks[1].page_content.count("| one | first |") == 1
    assert blocks[2].page_content == "Here is another example."
    assert blocks[3].page_content.count("| two | second |") == 1


def test_one_large_row_remains_whole_below_model_limit(monkeypatch):
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    row = "| x | " + " ".join(["description"] * 25) + " |"
    section = Document(page_content="| A | B |\n| --- | --- |\n" + row)

    blocks = markdown_tables.split_section_preserving_tables(section, max_tokens=20)

    assert len(blocks) == 1
    assert blocks[0].page_content.endswith(row)
    assert count_words(blocks[0].page_content) > 20
    assert blocks[0].metadata["block_type"] == "table"


def test_keeps_table_with_extra_separator_column(monkeypatch):
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    section = Document(
        page_content=(
            "The following meeting options are available:\n\n"
            "| Approach | Small meeting | Large meeting |\n"
            "| --- | --- | --- | --- |\n"
            "| Async | Preferred | Optional |"
        ),
        metadata={"section_path": "Meetings"},
    )

    blocks = markdown_tables.split_section_preserving_tables(section)

    assert [block.metadata["block_type"] for block in blocks] == ["text", "table"]
    assert "The following meeting options are available:" in blocks[1].page_content
    assert "| --- | --- | --- | --- |" in blocks[1].page_content
    assert "| Async | Preferred | Optional |" in blocks[1].page_content


def test_adjacent_tables_keep_their_own_headers(monkeypatch):
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    section = Document(
        page_content=(
            "| Visibility | Effect |\n| --- | --- |\n| Public | Searchable |\n"
            "| Access | Use cases |\n| --- | --- |\n| Editor | Can edit |"
        )
    )

    blocks = markdown_tables.split_section_preserving_tables(section)

    assert [block.metadata["block_type"] for block in blocks] == ["table", "table"]
    assert "| Visibility | Effect |" in blocks[0].page_content
    assert "| Access | Use cases |" not in blocks[0].page_content
    assert "| Access | Use cases |" in blocks[1].page_content
    assert "| Editor | Can edit |" in blocks[1].page_content
