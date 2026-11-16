from langchain_core.documents import Document

from app.RAG.Chunking.markdown_headers import split_document_by_markdown_headers


def test_splits_h2_to_h4_and_keeps_heading_path_and_source_metadata():
    document = Document(
        page_content=(
            "## Policies\nOverview text.\n"
            "### Accounts\nAccount text.\n"
            "#### Passwords\nPassword text.\n"
            "### Access\nAccess text.\n"
            "## Exceptions\nException text."
        ),
        metadata={"document_id": "doc-1", "category": None},
    )

    sections = split_document_by_markdown_headers(document)

    assert [section.metadata["section_path"] for section in sections] == [
        "Policies",
        "Policies > Accounts",
        "Policies > Accounts > Passwords",
        "Policies > Access",
        "Exceptions",
    ]
    assert all(section.metadata["document_id"] == "doc-1" for section in sections)
    assert all(section.metadata["category"] is None for section in sections)
    assert sections[1].page_content.startswith("### Accounts")


def test_includes_h1_in_section_path():
    document = Document(page_content="# Handbook\n\n## Policies\nPolicy text.")

    sections = split_document_by_markdown_headers(document)

    assert len(sections) == 1
    assert sections[0].metadata["section_path"] == "Handbook > Policies"
    assert sections[0].page_content.startswith("# Handbook")


def test_keeps_preamble_and_document_without_recognized_headings():
    preamble_document = Document(page_content="Introduction.\n\n## Scope\nScope text.")
    plain_document = Document(page_content="A document without H2-H4 headings.")

    preamble_sections = split_document_by_markdown_headers(preamble_document)
    plain_sections = split_document_by_markdown_headers(plain_document)

    assert [section.page_content for section in preamble_sections] == [
        "Introduction.",
        "## Scope\nScope text.",
    ]
    assert preamble_sections[0].metadata["section_path"] == ""
    assert len(plain_sections) == 1
    assert plain_sections[0].page_content == "A document without H2-H4 headings."
    assert plain_sections[0].metadata["section_path"] == ""


def test_leaves_h5_h6_and_headings_inside_code_fences_in_section_content():
    document = Document(
        page_content=(
            "## Main\nBody text.\n"
            "##### Smaller heading\nSmaller section text.\n"
            "###### Smallest heading\nSmallest section text.\n"
            "```markdown\n### Code sample heading\n```"
        )
    )

    sections = split_document_by_markdown_headers(document)

    assert len(sections) == 1
    assert sections[0].metadata["section_path"] == "Main"
    assert "##### Smaller heading" in sections[0].page_content
    assert "###### Smallest heading" in sections[0].page_content
    assert "### Code sample heading" in sections[0].page_content


def test_preserves_blank_lines_and_table_text_after_splitting():
    content = (
        "## Places\n\n"
        "A nearby table.\n\n"
        "| Name | Note |\n| --- | --- |\n| Wales | 🏴\U000e0067 |\n\n"
        "Text after the table.\n\n"
        "### Next\n\nAnother section."
    )

    sections = split_document_by_markdown_headers(Document(page_content=content))

    assert sections[0].page_content == content.split("### Next", 1)[0].strip("\n")
    assert sections[1].page_content == "### Next\n\nAnother section."


def test_source_alignment_ignores_same_heading_inside_code_fence():
    content = (
        "## Main\n\n"
        "```markdown\n### Repeated\n```\n\n"
        "### Repeated\n\nReal section."
    )

    sections = split_document_by_markdown_headers(Document(page_content=content))

    assert len(sections) == 2
    assert sections[0].page_content == "## Main\n\n```markdown\n### Repeated\n```"
    assert sections[1].page_content == "### Repeated\n\nReal section."


def test_repeated_heading_keeps_all_original_text():
    content = "# Handbook\n\n## Rules\nFirst rule.\n\n## Rules\nSecond rule."

    sections = split_document_by_markdown_headers(Document(page_content=content))

    assert [section.page_content for section in sections] == [content]
