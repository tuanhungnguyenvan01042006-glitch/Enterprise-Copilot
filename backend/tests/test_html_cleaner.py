from app.RAG.Ingestion.CleanernParser.html_cleaner import clean_html, extract_html_fragment


def test_plain_markdown_and_fenced_html_are_unchanged() -> None:
    content = "# Guide\n\n`<svg>`\n\n```html\n<script>example</script>\n```\n"
    assert clean_html(content) == content


def test_extract_fragment_keeps_meaningful_content_and_block_boundaries() -> None:
    fragment = (
        '<div class="card"><h2>Benefits</h2><p>EUR 150<br>per month</p>'
        '<a href="/handbook/benefits/">Read policy</a>'
        '<img alt="Coverage chart" src="chart.png">'
        '<details><summary>Eligibility</summary><p>Full-time team members</p></details>'
        '<svg><title>Icon</title></svg><script>secret()</script>'
        '<style>.card {color: red}</style><iframe src="video"></iframe></div>'
    )

    cleaned = extract_html_fragment(fragment)

    assert "## Benefits" in cleaned
    assert "EUR 150\nper month" in cleaned
    assert "[Read policy](/handbook/benefits/)" in cleaned
    assert "Coverage chart" in cleaned
    assert "### Eligibility" in cleaned
    assert "Full-time team members" in cleaned
    for discarded in ("secret()", "Icon", "color: red", "iframe", 'class="card"'):
        assert discarded not in cleaned


def test_html_table_preserves_each_header_value_pair() -> None:
    content = "<table><tr><th>Country</th><th>Allowance</th></tr><tr><td>NL</td><td>EUR 150</td></tr></table>"
    assert "- Country: NL; Allowance: EUR 150" in clean_html(content)


def test_image_alt_does_not_merge_with_adjacent_text() -> None:
    assert extract_html_fragment('<p>Before<img alt="Coverage chart">after</p>') == (
        "Before Coverage chart after"
    )


def test_mixed_markdown_keeps_code_span_links_and_table_rows() -> None:
    content = (
        "# Guide\n\n"
        "Use `<svg>` and <a href=\"/policy\">read policy</a>.<br>Next step.\n\n"
        "| Role | Actions |\n| --- | --- |\n| Staff | Read<br>Review |\n\n"
        "```mermaid\nA --> B<br>\n```\n"
    )

    cleaned = clean_html(content)

    assert "`<svg>`" in cleaned
    assert "[read policy](/policy)" in cleaned
    assert "Next step." in cleaned
    assert "| Staff | Read; Review |" in cleaned
    assert "```mermaid\nA --> B<br>\n```" in cleaned


def test_details_keeps_summary_and_markdown_body() -> None:
    content = (
        '## Medical Allowance\n\n<details markdown="1">\n\n'
        '<summary>Eligibility Requirements</summary>\n\n'
        '* Full-time employment\n* Based in the Netherlands\n\n</details>\n'
    )

    cleaned = clean_html(content)

    assert "## Medical Allowance" in cleaned
    assert "### Eligibility Requirements" in cleaned
    assert "* Full-time employment" in cleaned
    assert "* Based in the Netherlands" in cleaned
    assert "<details" not in cleaned
    assert "</details>" not in cleaned
