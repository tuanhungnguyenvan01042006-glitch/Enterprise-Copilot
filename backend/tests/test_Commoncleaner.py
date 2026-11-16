from langchain_core.documents import Document

from app.RAG.Ingestion.CleanernParser.cleaner import clean_document
from app.RAG.Ingestion.CleanernParser.common_markdown import (
    clean_common_markdown,
    find_code_line_ranges,
    find_markdown_block_line_ranges,
    strip_front_matter,
)
# import các hàm cần test vào, cho dữ liệu chạy qua để xem kết quả thu được có như mong muốn ko, nếu như mong muốn thì là hàm ngon 

# Mỗi hàm test sẽ tạo dữ liệu mẫu, đưa dữ liệu đó đi qua hàm, để xem kết quả có như mong đợi không (thông qua hàm assert)
def test_strip_front_matter_removes_only_the_initial_yaml_block() -> None:
    # Dữ liệu mẫu 
    page_content = (
        "---\n"
        "title: Example\n"
        "description: A test document\n"
        "---\n"
        "\n"
        "# Heading\n"
        "\n"
        "Body text.\n"
    )

    assert strip_front_matter(page_content) == "# Heading\n\nBody text.\n"
      # dữ liệu mẫu cần phải loại bỏ được front matter

def test_strip_front_matter_preserves_horizontal_rules_in_body() -> None:
    page_content = "---\ntitle: Example\n---\n# Heading\n\n---\n\nMore text."

    assert strip_front_matter(page_content) == "# Heading\n\n---\n\nMore text."


def test_strip_front_matter_supports_crlf_and_closing_delimiter_at_eof() -> None:
    assert strip_front_matter("---\r\ntitle: Example\r\n---") == ""
    assert strip_front_matter("---\r\ntitle: Example\r\n---\r\n\r\nBody") == "Body"


def test_strip_front_matter_leaves_content_without_a_valid_block_unchanged() -> None:
    no_front_matter = "# Heading\n\nBody text."
    malformed_front_matter = "---\ntitle: Example\n# This is body text"

    assert strip_front_matter(no_front_matter) == no_front_matter
    assert strip_front_matter(malformed_front_matter) == malformed_front_matter


def test_clean_document_preserves_metadata_and_does_not_mutate_input() -> None:
    original = Document(
        page_content=(
            "---\ntitle: Example\n---\n\n"
            "<!-- maintainer note -->\n# Body\n\n"
            "Return to the main [all-remote page](_index.md)."
        ),
        metadata={"source": "example.md", "category": "REFERENCE"},
    )

    cleaned = clean_document(original)

    assert cleaned is not original
    assert cleaned.page_content == "# Body"
    assert cleaned.metadata == original.metadata
    assert original.page_content.startswith("---\n")


def test_clean_document_runs_html_cleaner_after_common_markdown_cleaning() -> None:
    original = Document(
        page_content=(
            "---\ntitle: Example\n---\n\n"
            "<div class=\"card\"><h2>Benefits</h2>"
            "<p>Read <a href=\"/policy\">the policy</a>.</p>"
            "<script>discard_this()</script></div>\n\n"
            "| Item | Details |\n| --- | --- |\n| Leave | Request<br>approval |\n\n"
            "```html\n<script>keep_as_code()</script>\n```\n"
        ),
        metadata={"source": "example.md"},
    )

    cleaned = clean_document(original)

    assert "## Benefits" in cleaned.page_content
    assert "[the policy](/policy)" in cleaned.page_content
    assert "discard_this()" not in cleaned.page_content
    assert "| Leave | Request; approval |" in cleaned.page_content
    assert "```html\n<script>keep_as_code()</script>\n```" in cleaned.page_content
    assert cleaned.metadata == original.metadata


def test_find_code_line_ranges_includes_mermaid_fence_and_indented_code() -> None:
    content = (
        "# Diagram\n\n"
        "```mermaid\n"
        "A --> B\n"
        "```\n\n"
        "    <!-- literal code -->\n\n"
        "A normal paragraph.\n"
    )

    assert find_code_line_ranges(content) == [(2, 5), (6, 7)]


def test_find_code_line_ranges_handles_tilde_and_unclosed_fences() -> None:
    content = "Intro\r\n\r\n~~~text\r\n<!-- keep -->\r\n~~~\r\n\r\n```python\r\nprint('hi')"

    assert find_code_line_ranges(content) == [(2, 5), (6, 8)]


def test_parser_locates_table_html_and_code_blocks() -> None:
    content = (
        "# Guide\n\n"
        "| Key | Value |\n| --- | --- |\n| A | B |\n\n"
        "<div>\nHTML\n</div>\n\n"
        "```mermaid\nA --> B\n```\n"
    )

    assert find_markdown_block_line_ranges(content) == {
        "code": [(10, 13)],
        "table": [(2, 5)],
        "html": [(6, 9)],
    }


def test_common_cleaning_preserves_mermaid_and_removes_noise_outside_code() -> None:
    code = '```mermaid\r\nA --> B\r\n<!-- literal -->\r\n{style="width: 50%;"}\r\n```\r\n'
    content = (
        "# Guide\r\n\r\n<!-- maintainer\r\nnote -->\r\n\r\n"
        + code
        + '\r\n![Diagram](image.png)\r\n{style="max-width:50%"}\r\n\r\n'
        + "Keep text <!-- hidden --> next.\r\n\r\n\r\n"
        + "---\r\n\r\nDetails remain.\r\n"
    )

    cleaned = clean_common_markdown(content)

    assert code in cleaned
    assert "maintainer" not in cleaned
    assert "hidden" not in cleaned
    assert "![Diagram](image.png)" in cleaned
    assert cleaned.count("{style=") == 1
    assert "Keep text next." in cleaned
    assert "\n\n---\n\nDetails remain." in cleaned
    before_code, after_code = cleaned.split(code)
    assert "\n\n\n" not in before_code
    assert "\n\n\n" not in after_code


def test_common_cleaning_removes_entire_contribute_tail() -> None:
    content = (
        "# Guide\n\nReturn to the main [all-remote page](_index.md).\n\n"
        "Useful guidance.\n\n"
        "## Contribute your lessons\n\n"
        "If you have a tip, consider creating a [merge request](https://example.org) "
        "and adding a contribution to this page.\n\n"
        "---\n\nReturn to the main [all-remote page](_index.md)\n"
    )

    assert clean_common_markdown(content) == (
        "# Guide\n\nReturn to the main [all-remote page](_index.md).\n\n"
        "Useful guidance."
    )


def test_common_cleaning_removes_contribute_tail_without_invitation_phrase() -> None:
    content = (
        "```text\nReturn to the main [all-remote page](_index.md).\n```\n\n"
        "## Contribute your lessons\n\nPractical instructions remain.\n"
    )

    assert clean_common_markdown(content) == "```text\nReturn to the main [all-remote page](_index.md).\n```\n"


def test_common_cleaning_keeps_contribute_section_when_more_content_follows() -> None:
    content = (
        "## Contribute your lessons\n\n"
        "Practical instructions remain.\n\n"
        "## Additional guidance\n\nThis is not boilerplate.\n"
    )

    assert clean_common_markdown(content) == content.rstrip("\n")
