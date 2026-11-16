import pytest
from langchain_core.documents import Document

from app.RAG.Embedding.cleaner import (
    EMBEDDED_CONTENT_PLACEHOLDER,
    clean_embedding_item,
)
from app.RAG.Embedding.validation import (
    EmbeddingInputValidationError,
    build_embedding_item,
)


def embedding_item(text: str, *, block_type: str = "text"):
    return build_embedding_item(
        Document(
            page_content=text,
            metadata={
                "document_id": "doc-1",
                "chunk_id": "chunk-1",
                "chunk_index": 0,
                "block_type": block_type,
                "token_count": 5,
                "section_path": "Policy",
                "source_start": 0,
                "source_end": len(text),
                "knowledge_scope": "COMPANY",
                "department_id": None,
                "title": "Policy",
                "category": None,
            },
        )
    )


def test_removes_dynamic_placeholder_and_markdown_link_syntax() -> None:
    item = embedding_item(
        "Read [the password policy](/handbook/security/passwords/) for details. "
        f"{EMBEDDED_CONTENT_PLACEHOLDER}"
    )

    cleaned = clean_embedding_item(item)

    assert cleaned.text == "Read the password policy for details."
    assert cleaned.point_id == item.point_id
    assert cleaned.metadata == item.metadata
    assert item.text != cleaned.text


def test_keeps_url_when_markdown_link_has_no_label() -> None:
    cleaned = clean_embedding_item(embedding_item("See [](https://example.com/docs)."))

    assert cleaned.text == "See example.com/docs."


def test_normalizes_markdown_image_to_alt_text() -> None:
    cleaned = clean_embedding_item(
        embedding_item(
            "Review ![Password policy diagram](/images/password-policy.png "
            '"Password policy") before continuing.'
        )
    )

    assert cleaned.text == "Review Password policy diagram before continuing."


def test_removes_empty_markdown_image_without_emptying_surrounding_text() -> None:
    cleaned = clean_embedding_item(
        embedding_item("Before ![](/images/decorative.png) after.")
    )

    assert cleaned.text == "Before after."


def test_normalizes_template_variables() -> None:
    cleaned = clean_embedding_item(
        embedding_item(
            "Role: {{JOB_TITLE}}; start: {{START_DATE}}; "
            "date: {{Original Hire Date}}."
        )
    )

    assert cleaned.text == "Role: JOB TITLE; start: START DATE; date: Original Hire Date."


def test_normalizes_markdown_formatting_and_whitespace() -> None:
    cleaned = clean_embedding_item(
        embedding_item(
            "## **Password Policy**\n\n"
            "- Use *strong* passwords.\n"
            "- Run `check_password`.\n\n\n"
            "Keep   credentials   private."
        )
    )

    assert cleaned.text == (
        "Password Policy\n\n"
        "Use strong passwords.\n"
        "Run check_password.\n\n"
        "Keep credentials private."
    )


def test_removes_icons_from_embedding_text_without_changing_source() -> None:
    item = embedding_item("🤝 Collaboration, 📈 Results, ✅ approved, ○ not started.")

    cleaned = clean_embedding_item(item)

    assert cleaned.text == "Collaboration, Results, approved, not started."
    assert item.text == "🤝 Collaboration, 📈 Results, ✅ approved, ○ not started."


def test_table_uses_text_cleanup_without_changing_source() -> None:
    text = (
        "Section: Policy\n\n"
        "| Status | Guide |\n"
        "| --- | --- |\n"
        "| ✅ **Approved** | [Policy](https://example.com/policy) |"
    )
    item = embedding_item(text, block_type="table")

    cleaned = clean_embedding_item(item)

    assert cleaned.text == (
        "Section: Policy\n\n"
        "| Status | Guide |\n"
        "| --- | --- |\n"
        "| Approved | Policy |"
    )
    assert [line.count("|") for line in cleaned.text.splitlines()] == [
        line.count("|") for line in text.splitlines()
    ]
    assert item.text == text
    assert cleaned.point_id == item.point_id
    assert cleaned.metadata == item.metadata


@pytest.mark.parametrize("block_type", ["code", "mermaid"])
def test_structured_blocks_are_returned_unchanged(block_type: str) -> None:
    text = f"[Guide](/guide) ✅ {EMBEDDED_CONTENT_PLACEHOLDER}"
    item = embedding_item(text, block_type=block_type)

    cleaned = clean_embedding_item(item)

    assert cleaned is item
    assert cleaned.text == text


def test_cleans_link_syntax_inside_inline_code() -> None:
    cleaned = clean_embedding_item(
        embedding_item(
            "Use `[#thanks](https://gitlab.slack.com/archives/C038E3Q6L)`. "
            "Contact the `#eba-team` channel and read [the guide](/guide)."
        )
    )

    assert cleaned.text == (
        "Use #thanks. Contact the #eba-team channel and read the guide."
    )


def test_placeholder_only_text_is_rejected_after_cleaning() -> None:
    with pytest.raises(
        EmbeddingInputValidationError,
        match="text: empty after embedding cleaning",
    ):
        clean_embedding_item(embedding_item(EMBEDDED_CONTENT_PLACEHOLDER))
