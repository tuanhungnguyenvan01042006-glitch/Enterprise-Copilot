"""Minimal text cleanup immediately before an embedding model call."""

from __future__ import annotations

import re
from dataclasses import replace

from app.RAG.Embedding.types import EmbeddingItem
from app.RAG.Embedding.validation import (
    EmbeddingInputValidationError,
    validate_embedding_item,
)


EMBEDDED_CONTENT_PLACEHOLDER = "[Embedded or dynamic content unavailable in source]"
_UNCHANGED_BLOCK_TYPES = frozenset({"code", "mermaid"})
_PLACEHOLDER_LINE = re.compile(
    rf"(?m)^[ \t]*{re.escape(EMBEDDED_CONTENT_PLACEHOLDER)}[ \t]*(?:\n|$)"
)
_PLACEHOLDER_INLINE = re.compile(
    rf"[ \t]*{re.escape(EMBEDDED_CONTENT_PLACEHOLDER)}[ \t]*"
)
_MARKDOWN_DESTINATION = (
    r"(?P<destination><[^>\n]+>|(?:[^()\n]+|\([^()\n]*\))+?)"
)
_MARKDOWN_IMAGE = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\("
    + _MARKDOWN_DESTINATION
    + r"\s*(?:\"[^\"]*\"|'[^']*')?\)"
)
_MARKDOWN_LINK = re.compile(
    r"(?<!\!)\[(?P<label>[^\]\n]*)\]\("
    + _MARKDOWN_DESTINATION
    + r"\s*(?:\"[^\"]*\"|'[^']*')?\)"
)
_TEMPLATE_VARIABLE = re.compile(
    r"\{\{(?![%<])(?P<value>[^{}\n]+)\}\}"
)
_MARKDOWN_HEADING = re.compile(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+")
_MARKDOWN_LIST_MARKER = re.compile(
    r"(?m)^[ \t]{0,3}(?:[-+*]|\d+[.)])[ \t]+"
)
_MARKDOWN_INLINE_CODE = re.compile(r"(?<!`)`(?P<value>[^`\n]+)`(?!`)")
_MARKDOWN_BOLD = re.compile(r"\*\*(?P<value>.+?)\*\*|(?<!\w)__(?P<under>.+?)__(?!\w)")
_MARKDOWN_ITALIC = re.compile(
    r"(?<!\w)\*(?P<star>\S(?:.*?\S)?)\*(?!\w)|"
    r"(?<!\w)_(?P<under>\S(?:.*?\S)?)_(?!\w)"
)
_URL_SCHEME = re.compile(r"^https?://", re.IGNORECASE)
_ICON = re.compile(
    r"[\U0001F000-\U0001FAFF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\u25CB\u27F3]"
    r"[\uFE0E\uFE0F\u200D]*"
)


def _remove_dynamic_placeholders(text: str) -> str:
    text = _PLACEHOLDER_LINE.sub("", text)
    return _PLACEHOLDER_INLINE.sub(" ", text)


def _image_text(match: re.Match[str]) -> str:
    return match.group("alt").strip()


def _remove_markdown_images(text: str) -> str:
    return _MARKDOWN_IMAGE.sub(_image_text, text)


def _template_text(match: re.Match[str]) -> str:
    value = match.group("value").strip().strip("\"'")
    return re.sub(r"[_-]+", " ", value)


def _normalize_template_variables(text: str) -> str:
    return _TEMPLATE_VARIABLE.sub(_template_text, text)


def _normalize_url(value: str) -> str:
    return _URL_SCHEME.sub("", value)


def _markdown_formatting_text(match: re.Match[str]) -> str:
    return next(value for value in match.groupdict().values() if value is not None)


def _normalize_markdown_formatting(text: str) -> str:
    text = _MARKDOWN_HEADING.sub("", text)
    text = _MARKDOWN_LIST_MARKER.sub("", text)
    text = _MARKDOWN_INLINE_CODE.sub(lambda match: match.group("value"), text)
    text = _MARKDOWN_BOLD.sub(_markdown_formatting_text, text)
    return _MARKDOWN_ITALIC.sub(_markdown_formatting_text, text)


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _link_text(match: re.Match[str]) -> str:
    label = match.group("label").strip()
    if label:
        return _normalize_url(label) if _URL_SCHEME.match(label) else label

    destination = match.group("destination").strip()
    destination = re.split(r"\s+(?=[\"'])", destination, maxsplit=1)[0]
    if destination.startswith("<") and destination.endswith(">"):
        destination = destination[1:-1]
    return _normalize_url(destination)


def _remove_markdown_link_syntax(text: str) -> str:
    return _MARKDOWN_LINK.sub(_link_text, text)


def clean_embedding_item(item: EmbeddingItem) -> EmbeddingItem:
    validate_embedding_item(item)
    if item.metadata.get("block_type") in _UNCHANGED_BLOCK_TYPES:
        return item

    cleaned = _remove_dynamic_placeholders(item.text)
    cleaned = _remove_markdown_images(cleaned)
    cleaned = _remove_markdown_link_syntax(cleaned)
    cleaned = _normalize_template_variables(cleaned)
    cleaned = _normalize_markdown_formatting(cleaned)
    cleaned = _ICON.sub("", cleaned).replace("\uFE0E", "").replace("\uFE0F", "")
    cleaned = _normalize_whitespace(cleaned)

    if not cleaned:
        raise EmbeddingInputValidationError(
            "text: empty after embedding cleaning"
        )

    return replace(item, text=cleaned)
