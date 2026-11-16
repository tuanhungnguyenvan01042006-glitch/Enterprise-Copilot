"""
Phần này là xử lý Mermaid, để đảm bảo Recursive ko làm hỏng cấu trúc Mermaid 
nên ta cũng sẽ xử lý trước, cách xử lý tương tự bên table
chỉ có 1 cái khác là Chunksize của Mermaid sẽ được phép > 750 token 
nguyên nhân là table thì tách được ra làm 2 table khác, chứ mermaid thì ko thể
Tuy nhiên, ta cần đảm bảo chunksize ko vượt quá giới hạn của Modal Embed, nên trong phần embed, có thể ta sẽ phải xử lý đặc biệt với trường hợp chunksize quá lớn
"""
from __future__ import annotations

from langchain_core.documents import Document
from markdown_it import MarkdownIt

from app.RAG.Chunking.markdown_tables import (
    DEFAULT_MAX_TOKENS,
    _table_context,
    _with_context,
    split_section_preserving_tables,
)


_MARKDOWN = MarkdownIt("commonmark").enable("table")


def split_section_preserving_code_blocks(
    section: Document, *, max_tokens: int = DEFAULT_MAX_TOKENS
) -> list[Document]:
    """Separate fenced and indented code blocks while keeping their source intact."""
    if section.metadata.get("block_type") in {"table", "code", "mermaid"}:
        return [section]

    lines = section.page_content.split("\n")
    code_blocks = [
        token
        for token in _MARKDOWN.parse(section.page_content)
        if token.type in {"fence", "code_block"} and token.map
    ]
    if not code_blocks:
        return [
            Document(
                page_content=section.page_content,
                metadata={**section.metadata, "block_type": "text"},
            )
        ]

    result = []
    cursor = 0
    for token in code_blocks:
        start, end = token.map
        text = "\n".join(lines[cursor:start]).strip()
        if text:
            result.append(
                Document(
                    page_content=text,
                    metadata={**section.metadata, "block_type": "text"},
                )
            )

        heading, intro = _table_context(lines, start, section, max_tokens)
        context = "\n\n".join(part for part in (heading, intro) if part)
        content = _with_context(context, "\n".join(lines[start:end]))
        language = ""
        if token.type == "fence" and token.info.strip():
            language = token.info.strip().split(maxsplit=1)[0].lower()
        block_type = "mermaid" if language == "mermaid" else "code"
        metadata = {**section.metadata, "block_type": block_type}
        if language:
            metadata["code_language"] = language
        result.append(Document(page_content=content, metadata=metadata))
        cursor = end

    text = "\n".join(lines[cursor:]).strip()
    if text:
        result.append(
            Document(
                page_content=text,
                metadata={**section.metadata, "block_type": "text"},
            )
        )
    return result


def split_section_preserving_structures(
    section: Document, *, max_tokens: int = DEFAULT_MAX_TOKENS
) -> list[Document]:
    """Preserve tables first, then separate code blocks from the remaining text."""
    table_blocks = split_section_preserving_tables(section, max_tokens=max_tokens)
    return [
        code_block
        for block in table_blocks
        for code_block in split_section_preserving_code_blocks(block, max_tokens=max_tokens)
    ]
