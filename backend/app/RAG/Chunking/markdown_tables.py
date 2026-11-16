""" thực tế triết lý của đoạn này là : Ở đây ta sợ ở bước sau, nếu ta dùng Recursive Split 
thì có thể làm hỏng cấu trúc Table / Mermaid 
vì vậy ta đi trước 1 bước. Cụ thể file này sẽ có output là : 
1. Section chứa table, sẽ bị lọc hết table ra, chỉ còn lại text, ko chứa table
2. Table sẽ đựa lưu riêng trong 1 section mới (có context trước đó) chuyên chỉ để lưu table
nếu table quá lớn, thì ta tách ra thành các section với table nhỏ hơn 
Vì ta đã dán nhãn Table, cũng như tự tách chunk table thủ công nếu > 700 token, nên ta ko cần xử lý nó trong Recursive Split nữa 
"""
from __future__ import annotations

import re

from langchain_core.documents import Document
from markdown_it import MarkdownIt

from app.RAG.Chunking.tokenizer import count_voyage_tokens


_MARKDOWN = MarkdownIt("commonmark").enable("table")
_SEPARATOR_CELL = re.compile(r":?-+:?")
DEFAULT_MAX_TOKENS = 700
MAX_INTRO_TOKENS = 150
MODEL_MAX_TOKENS = 32000


def _is_table_header(lines: list[str], index: int) -> bool:
    if (
        index + 1 >= len(lines)
        or "|" not in lines[index]
        or "|" not in lines[index + 1]
    ):
        return False
    cells = lines[index + 1].strip().strip("|").split("|")
    return all(_SEPARATOR_CELL.fullmatch(cell.strip()) for cell in cells)


def _table_ranges(text: str, lines: list[str]) -> list[tuple[int, int]]:
    code_lines = {
        index
        for token in _MARKDOWN.parse(text)
        if token.type in {"fence", "code_block"} and token.map
        for index in range(token.map[0], token.map[1])
    }
    ranges = []
    index = 0
    while index < len(lines) - 1:
        if index in code_lines or index + 1 in code_lines or not _is_table_header(lines, index):
            index += 1
            continue

        start = index
        leading_pipe = lines[start].lstrip().startswith("|")
        index += 2
        while index < len(lines) and index not in code_lines:
            row = lines[index].lstrip()
            if _is_table_header(lines, index) or not row:
                break
            if leading_pipe and not row.startswith("|"):
                break
            if not leading_pipe and "|" not in row:
                break
            index += 1
        ranges.append((start, index))
    return ranges


def _with_context(context: str, table: str) -> str:
    return f"{context}\n\n{table}" if context else table


def _table_context(
    lines: list[str],
    table_start: int,
    section: Document,
    max_tokens: int,
) -> tuple[str, str]:
    section_name = section.metadata.get("section_path") or section.metadata.get("title")
    heading = f"Section: {section_name}" if section_name else ""

    intro = ""
    preceding = _MARKDOWN.parse("\n".join(lines[:table_start]))
    paragraph = next(
        (token for token in reversed(preceding) if token.type == "paragraph_open" and token.level == 0),
        None,
    )
    if paragraph and paragraph.map:
        start, end = paragraph.map
        if table_start - end <= 2 and all(not line.strip() for line in lines[end:table_start]):
            candidate = "\n".join(lines[start:end]).strip()
            if count_voyage_tokens(candidate) <= min(MAX_INTRO_TOKENS, max_tokens // 4):
                intro = candidate
    # Intro phải thỏa mãn điều kiện : cách đầu bảng tối đa 2 dòng, mọi dòng ở giữa đều trống, đoạn văn ko được vượt quá 100token hoặc maxtoken /4
    return heading, intro


def _split_table(
    table_lines: list[str],
    heading: str,
    intro: str,
    max_tokens: int,
) -> list[str]:
    context = "\n\n".join(part for part in (heading, intro) if part)
    # Ghép heading và Intro thành phần context cố định của table 
    table = _with_context(context, "\n".join(table_lines))
    # ghép context vào table
    if count_voyage_tokens(table) <= max_tokens:
        return [table]
    # Nếu sau khi ghép context vào mà ko vượt mức thì oke luôn, trả về Section table 
    # Đây chính là trường hợp Table ngắn : Ghép context vào là done luôn 
    header = "\n".join(table_lines[:2])
    rows = table_lines[2:]
    # lấy ra tên cột (header) là 2 hàng đầu, các hàng dưới là các hàng nội dung bảng 

    chunks = []
    current_rows: list[str] = []   # là biến chứa các row của chunk hiện tại đang xét
    for row in rows:
        candidate = _with_context(context, "\n".join([header, *current_rows, row]))
        # với mỗi hàng mới, ta có 1 candidate mới là bảng sau khi thêm Current rows vào
        # nếu candidate này vượt quá, thì bỏ tạo ra chunk table chỉ dài đến trước current rows
        if current_rows and count_voyage_tokens(candidate) > max_tokens:
            chunks.append(_with_context(context, "\n".join([header, *current_rows])))
            # ta tạo ra bảng bằng cách ghép 2 dòng đầu(dòng header : chứa tên cột) và các hàng tiếp theo của bảng
            current_rows = [row]
        else:
            current_rows.append(row)
            # nếu chưa vượt ngưỡng, thì cho hàng hiện tại vào danh sách hàng của 

    chunks.append(_with_context(context, "\n".join([header, *current_rows])))
    if any(count_voyage_tokens(chunk) > MODEL_MAX_TOKENS for chunk in chunks):
        raise ValueError("A table row exceeds the Voyage 4 token limit.")
    return chunks


def split_section_preserving_tables(
    section: Document, *, max_tokens: int = DEFAULT_MAX_TOKENS
) -> list[Document]:
    """Return text and table blocks, splitting long tables only between rows."""
    if not 0 < max_tokens <= MODEL_MAX_TOKENS:
        raise ValueError("max_tokens must be between 1 and 32000.")

    lines = section.page_content.split("\n")
    tables = _table_ranges(section.page_content, lines)
    if not tables:
        return [Document(page_content=section.page_content, metadata={**section.metadata, "block_type": "text"})]

    result = []
    cursor = 0
    for start, end in tables:
        text = "\n".join(lines[cursor:start]).strip()
        if text:
            result.append(Document(page_content=text, metadata={**section.metadata, "block_type": "text"}))
            # tức là 2 type là riêng biệt, ko được lẫn lộn : text / table 
            # Tức là nếu 1 section có cả text và tables, thì nó sẽ lấy ra tất cả table, đem làm section riêng, và dồn các khối code còn lại thành 1 section type Text riêng 
        heading, intro = _table_context(lines, start, section, max_tokens)
        for content in _split_table(lines[start:end], heading, intro, max_tokens):
            result.append(Document(page_content=content, metadata={**section.metadata, "block_type": "table"}))
        cursor = end

    text = "\n".join(lines[cursor:]).strip()
    if text:
        result.append(Document(page_content=text, metadata={**section.metadata, "block_type": "text"}))
    return result
