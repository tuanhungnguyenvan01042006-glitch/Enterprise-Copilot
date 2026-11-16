from __future__ import annotations

import re

from app.RAG.Ingestion.CleanernParser.common_markdown import find_code_line_ranges


_STATIC_WRAPPERS = {"details", "panel", "alert", "card", "cardpane"}
_REMOVED_SHORTCODES = {"a", "external", "label", "all-remote/country-select"}
_PLACEHOLDER_SHORTCODES = {
    "youtube",
    "vimeo",
    "kpi",
    "team-size",
    "group-by-expertise",
    "include",
    "people-group/entities-with-probation",
    "people-group/entities-without-probation",
}
_MISSING_CONTENT_PLACEHOLDER = "[Embedded or dynamic content unavailable in source]"

_SHORTCODE = re.compile(
    r"\{\{\s*(?:"
    r"%\s*(?P<percent_close>/)?\s*(?P<percent_name>[\w-]+(?:/[\w-]+)*)"
    r"(?P<percent_args>.*?)\s*%"
    r"|"
    r"<\s*(?P<angle_close>/)?\s*(?P<angle_name>[\w-]+(?:/[\w-]+)*)"
    r"(?P<angle_args>.*?)\s*>"
    r")\s*\}\}",
    re.DOTALL,
)
_SEMANTIC_ATTRIBUTE = re.compile(
    r'''(?<![\w-])(?P<name>summary|header|title|footer)\s*=\s*'''
    r'''(?P<quote>["'])(?P<value>.*?)(?P=quote)''',
    re.DOTALL,
)


def _semantic_attribute_replacements(attributes: str) -> str:
    replacements = []
    for match in _SEMANTIC_ATTRIBUTE.finditer(attributes):
        value = " ".join(match.group("value").split())
        if not value:
            continue
        if match.group("name") == "footer":
            replacements.append(f"**Caption:** {value}")
        else:
            replacements.append(f"### {value}")

    replacement_text = "\n\n".join(replacements)
    return f"\n{replacement_text}\n\n" if replacements else "\n"


def _replace_shortcode(match: re.Match[str]) -> str:
    name = (match.group("percent_name") or match.group("angle_name")).lower()
    is_closing = bool(match.group("percent_close") or match.group("angle_close"))

    if name in _STATIC_WRAPPERS:
        if is_closing:
            return "\n"
        attributes = match.group("percent_args") or match.group("angle_args") or ""
        return _semantic_attribute_replacements(attributes)

    if name in _REMOVED_SHORTCODES:
        return ""

    if name in _PLACEHOLDER_SHORTCODES:
        return _MISSING_CONTENT_PLACEHOLDER

    return "\n" if is_closing else _MISSING_CONTENT_PLACEHOLDER


def _clean_shortcode_text(text: str) -> str:
    return _SHORTCODE.sub(_replace_shortcode, text)


def clean_shortcodes(page_content: str) -> str:
    lines = page_content.splitlines(keepends=True)
    parts: list[str] = []
    cursor = 0

    for start, end in find_code_line_ranges(page_content):
        parts.append(_clean_shortcode_text("".join(lines[cursor:start])))
        parts.append("".join(lines[start:end]))
        cursor = end

    parts.append(_clean_shortcode_text("".join(lines[cursor:])))
    return "".join(parts)
