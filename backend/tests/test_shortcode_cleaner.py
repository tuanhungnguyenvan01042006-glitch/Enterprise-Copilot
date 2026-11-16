import pytest

from langchain_core.documents import Document

from app.RAG.Ingestion.CleanernParser.cleaner import clean_document
from app.RAG.Ingestion.CleanernParser.shortcode_cleaner import clean_shortcodes


def test_details_keeps_summary_and_static_markdown_body() -> None:
    content = (
        '{{% details summary="GitLab BV (Belgium)" %}}\n\n'
        "### Belgium\n\nKeep this policy text.\n"
        "{{% /details %}}\n"
    )

    cleaned = clean_document(Document(page_content=content, metadata={}))

    assert cleaned.page_content == (
        "### GitLab BV (Belgium)\n\n"
        "### Belgium\n\nKeep this policy text."
    )


def test_static_wrappers_keep_semantic_attributes_and_body() -> None:
    content = (
        '{{% panel header="**Coding**" header-bg="green" %}}\n'
        "Expense category.{{% /panel %}}\n\n"
        '{{% alert title="Note" color="primary" %}}Important detail.{{% /alert %}}'
    )

    cleaned = clean_shortcodes(content)

    assert "### **Coding**" in cleaned
    assert "### Note" in cleaned
    assert "header-bg" not in cleaned
    assert 'color="primary"' not in cleaned
    assert "Expense category." in cleaned
    assert "Important detail." in cleaned


def test_cardpane_and_cards_keep_body_and_semantic_attributes() -> None:
    content = (
        "{{% cardpane %}}\n"
        '{{% card header="**Compensation**" %}}\n'
        "**Why:** [Our Compensation Principle](/handbook/total-rewards/compensation/)\n"
        "{{% /card %}}\n\n"
        '{{% card header="Benefits" %}}\n'
        "**What:** [General Benefits](/handbook/total-rewards/benefits/)\n"
        "{{% /card %}}\n"
        "{{% /cardpane %}}\n"
    )

    cleaned = clean_shortcodes(content)

    assert "### **Compensation**" in cleaned
    assert "### Benefits" in cleaned
    assert "**Why:** [Our Compensation Principle]" in cleaned
    assert "**What:** [General Benefits]" in cleaned
    assert "cardpane" not in cleaned
    assert "{{%" not in cleaned


def test_card_footer_is_kept_as_a_caption_and_body_is_preserved() -> None:
    content = (
        '{{< card footer="A useful caption" >}}\n'
        "![Remote work image](remote-work.jpg)\n"
        "{{< /card >}}"
    )

    cleaned = clean_shortcodes(content)

    assert "**Caption:** A useful caption" in cleaned
    assert "![Remote work image](remote-work.jpg)" in cleaned
    assert "{{<" not in cleaned


def test_markers_and_widgets_are_removed_without_a_placeholder() -> None:
    content = (
        '{{% a "low-context" %}}Use explicit communication. '
        '<a href="https://example.com">Watch on YouTube {{< external >}}</a> '
        '{{< label name="Visibility: Audit" color="#E24329" >}}Policy text.'
        "{{< all-remote/country-select >}}"
    )

    cleaned = clean_shortcodes(content)

    assert "Use explicit communication." in cleaned
    assert "Watch on YouTube" in cleaned
    assert "Policy text." in cleaned
    assert "low-context" not in cleaned
    assert "Visibility: Audit" not in cleaned
    assert "#E24329" not in cleaned
    assert "country-select" not in cleaned
    assert "unavailable in source" not in cleaned
    assert "{{" not in cleaned


def test_dynamic_content_has_a_placeholder_without_losing_static_context() -> None:
    content = (
        "## Sales KPIs\n{{< kpi \"Sales\" >}}\n"
        "Watch this explanation: {{< youtube \"video-id\" start=12 >}}\n"
        "{{< vimeo 650088717 >}}\n"
        "The team has {{< team-size >}} members.\n"
        "{{< group-by-expertise \"mentor\" >}}\n"
    )

    cleaned = clean_shortcodes(content)

    placeholder = "[Embedded or dynamic content unavailable in source]"
    assert cleaned == (
        f"## Sales KPIs\n{placeholder}\n"
        f"Watch this explanation: {placeholder}\n"
        f"{placeholder}\n"
        f"The team has {placeholder} members.\n"
        f"{placeholder}\n"
    )


def test_unresolved_partials_have_placeholders_at_the_missing_content() -> None:
    content = (
        "## Resources\n{{% include \"includes/course.md\" %}}\n"
        "## Locations with probation\n"
        "{{< people-group/entities-with-probation >}}\n"
        "## Locations without probation\n"
        "{{< people-group/entities-without-probation >}}"
    )

    cleaned = clean_shortcodes(content)

    placeholder = "[Embedded or dynamic content unavailable in source]"
    assert cleaned == (
        f"## Resources\n{placeholder}\n"
        f"## Locations with probation\n{placeholder}\n"
        f"## Locations without probation\n{placeholder}"
    )


def test_document_keeps_an_explicit_gap_for_the_missing_team_size() -> None:
    content = "The GitLab Inc. team consists of the following {{< team-size >}} team members."

    cleaned = clean_document(Document(page_content=content, metadata={}))

    assert cleaned.page_content == (
        "The GitLab Inc. team consists of the following "
        "[Embedded or dynamic content unavailable in source] team members."
    )


def test_known_shortcodes_inside_code_fence_are_unchanged() -> None:
    code = (
        '{{% alert title="Example" %}}\n'
        '{{< youtube "video-id" >}}\n'
        '{{% include "includes/course.md" %}}\n'
        '{{< future-shortcode >}}\n'
        '{{< /future-shortcode >}}\n'
        '{{% /alert %}}'
    )
    content = f"```text\n{code}\n```\n"

    assert clean_shortcodes(content) == content


def test_unknown_shortcode_has_a_placeholder_and_keeps_surrounding_text() -> None:
    content = 'Before {{< future-shortcode value="unknown data" >}} after.'

    assert clean_shortcodes(content) == (
        "Before [Embedded or dynamic content unavailable in source] after."
    )


@pytest.mark.parametrize(
    ("opening", "closing"),
    [
        ('{{< unknown-wrapper title="Example" >}}', "{{< /unknown-wrapper >}}"),
        ('{{% unknown-wrapper title="Example" %}}', "{{% /unknown-wrapper %}}"),
    ],
)
def test_unknown_wrapper_keeps_body_and_replaces_only_the_opening(
    opening: str, closing: str,
) -> None:
    content = f"{opening}\nImportant instructions.\n{closing}"

    assert clean_shortcodes(content) == (
        "[Embedded or dynamic content unavailable in source]\n"
        "Important instructions.\n\n"
    )


def test_template_variables_are_preserved() -> None:
    content = "Role: {{JOB_TITLE}}; start: {{START_DATE}}; hire date: {{Original Hire Date}}."

    assert clean_shortcodes(content) == content
