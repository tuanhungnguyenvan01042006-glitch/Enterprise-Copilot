from __future__ import annotations

import re

from markdown_it import MarkdownIt
from markdown_it.token import Token

# Phần 1 : Xây dựng các hàm hỗ trợ : 

#1 Tách Front matter
_FRONT_MATTER_PATTERN = re.compile(
    r"\A---[ \t]*\r?\n.*?^---[ \t]*(?:\r?\n|\Z)",
    flags=re.DOTALL | re.MULTILINE,
)
def strip_front_matter(page_content: str) -> str:
    match = _FRONT_MATTER_PATTERN.match(page_content)
    if match is None:
        return page_content
    return page_content[match.end() :].lstrip("\r\n")

#2 : Parse tất cả các thành phần noise ra : HTML, Style, Navigation,...
_MARKDOWN_PARSER = MarkdownIt("commonmark").enable("table")
    # Tạo ra đối tượng Parser chuyên để xử lý văn bản markdown, có hỗ trợ table trong Markdown

# Đây là các regex dùng để parse ra các thành phần noise 
_HTML_COMMENT = re.compile(r"[ \t]*<!--.*?-->[ \t]*", re.DOTALL)
_STYLE_ATTRIBUTE = re.compile(r'[ \t]*\{style="[^"\n]*"\}[ \t]*')
_NAVIGATION_TAIL = re.compile(
    r"(?m)(?:^---[ \t]*(?:\n[ \t]*)+)?"
    r"^Return to the main \[[^\]\n]+\]\([^\n)]+\)\.?[ \t]*(?:\n[ \t]*)*\Z"
)
_CONTRIBUTE_TAIL = re.compile(
    r"(?m)^## Contribute your lessons[ \t]*\n"
    r"(?:(?!^#{1,6}[ \t]).*(?:\n|$))*\Z"
)


def find_markdown_block_line_ranges(page_content: str) -> dict[str, list[tuple[int, int]]]:
    token_kinds = {
        "fence": "code",
        "code_block": "code",
        "table_open": "table",
        "html_block": "html",
    }
    blocks: dict[str, list[tuple[int, int]]] = {"code": [], "table": [], "html": []}
    for token in parse_markdown_tokens(page_content):
        kind = token_kinds.get(token.type)
        if kind and token.map is not None:
            blocks[kind].append((token.map[0], token.map[1]))
    return blocks
 

def parse_markdown_tokens(page_content: str) -> list[Token]:
    return _MARKDOWN_PARSER.parse(page_content)


def find_code_line_ranges(page_content: str) -> list[tuple[int, int]]:
    return find_markdown_block_line_ranges(page_content)["code"]


# xóa các phần bên ngoài khối code 
def _clean_text_outside_code(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")   # Chuẩn hóa xuống dòng \n
    text = _HTML_COMMENT.sub(" ", text)   # xóa html commment
    text = _STYLE_ATTRIBUTE.sub(" ", text)   # xóa thẻ style
    text = re.sub(r"(?m)^[ \t]+$", "", text)   # xóa khoảng trắng, tab,... 
    return re.sub(r"\n{3,}", "\n\n", text)    # Chuẩn hóa các thứ : Tóm lại là chuẩn hóa văn bản


def _remove_tail_boilerplate(text: str) -> str: 
    text = _NAVIGATION_TAIL.sub("", text)
    text = _CONTRIBUTE_TAIL.sub("", text)
    return text.rstrip("\n")


def clean_common_markdown(page_content: str) -> str:
    lines = page_content.splitlines(keepends=True)
    parts = []
    cursor = 0
    for start, end in find_code_line_ranges(page_content):
        parts.append(_clean_text_outside_code("".join(lines[cursor:start])))
        parts.append("".join(lines[start:end]))
        cursor = end
    tail = _clean_text_outside_code("".join(lines[cursor:]))
    parts.append(_remove_tail_boilerplate(tail))
    return "".join(parts).lstrip("\n")



