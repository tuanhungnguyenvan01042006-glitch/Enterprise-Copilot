"""
Điều phối toàn bộ quá trình Chunking:

1. Chia tài liệu theo Markdown heading.
2. Bảo vệ table, code block và Mermaid block.
3. Chia recursive các text block vượt giới hạn token.
4. Gắn source range, token count và chunk id ổn định cho từng chunk
* NOTE : từng bước trong pipeline này thực chất là từng hàm đã được xây dựng từ các file con trước đó
- ở đây file pipeline này chỉ gọi lần lượt từng hàm đó theo đúng các bước đúng theo pipeline 
Và nó sẽ gọi lần lượt trong hàm Main của file là hàm chunk_document, để sau này, khi muốn cho 1 file đi qua pipeline chunking, thì
ta chỉ cần gọi hàm chunk_docment và truyền file đó vào 
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document
from markdown_it import MarkdownIt

from app.RAG.Chunking.markdown_code import split_section_preserving_structures
from app.RAG.Chunking.markdown_headers import split_document_by_markdown_headers
from app.RAG.Chunking.markdown_tables import _table_ranges
from app.RAG.Chunking.recursive_text import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    split_long_text_blocks,
)
from app.RAG.Chunking.tokenizer import count_voyage_tokens


_MARKDOWN = MarkdownIt("commonmark").enable("table")


def _block_source_range(
    source: str, block: Document, search_from: int
) -> tuple[int, int]:
    """Locate a structured block in the cleaned source document."""

    block_type = block.metadata.get("block_type")

    if block_type == "text":
        start = source.find(block.page_content, search_from)
        if start < 0:
            raise ValueError(
                "Could not locate a text block in the cleaned Markdown source."
            )
        return start, start + len(block.page_content)

    lines = block.page_content.splitlines()
    tokens = _MARKDOWN.parse(block.page_content)

    if block_type == "table":
        table_ranges = _table_ranges(block.page_content, lines)
        if not table_ranges:
            raise ValueError("Could not locate a table block in the chunk content.")

        table_start, table_end = table_ranges[0]
        table_lines = lines[table_start:table_end]
        source_lines = table_lines[2:] or table_lines[:1]
        positions: list[tuple[int, int]] = []

        for line in source_lines:
            position = source.find(line, search_from)
            if position < 0:
                raise ValueError(
                    "Could not locate a table row in the cleaned Markdown source."
                )
            positions.append((position, position + len(line)))
            search_from = position + len(line)

        return positions[0][0], positions[-1][1]

    if block_type in {"code", "mermaid"}:
        code = next(
            (
                token
                for token in tokens
                if token.type in {"fence", "code_block"} and token.map
            ),
            None,
        )
        if code is None:
            raise ValueError("Could not locate a code block in the chunk content.")

        code_text = "\n".join(lines[code.map[0] : code.map[1]])
        start = source.find(code_text, search_from)
        if start < 0:
            raise ValueError(
                "Could not locate a code block in the cleaned Markdown source."
            )
        return start, start + len(code_text)

    raise ValueError(f"Unsupported chunk block type: {block_type!r}")


def chunk_document(
    document: Document,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:


    document_id = str(document.metadata.get("document_id") or document.id or "")
    if not document_id:
        raise ValueError("document_id is required to create stable chunk IDs.")

    chunks: list[Document] = []
    source_search_from = 0

    for section in split_document_by_markdown_headers(document):
        section_start = document.page_content.find(
            section.page_content, source_search_from
        )
        if section_start < 0:
            raise ValueError(
                "Could not locate a Markdown section in the cleaned source."
            )

        blocks = split_section_preserving_structures(section)
        block_search_from = section_start

        for block in blocks:
            source_start, source_end = _block_source_range(
                document.page_content, block, block_search_from
            )
            block.metadata["source_start"] = source_start
            block.metadata["source_end"] = source_end
            block_search_from = source_end

        chunks.extend(
            split_long_text_blocks(
                blocks,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )
        source_search_from = block_search_from

    for chunk_index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = chunk_index
        chunk.metadata["token_count"] = count_voyage_tokens(chunk.page_content)
        chunk.metadata["chunk_id"] = str(
            uuid5(
                NAMESPACE_URL,
                (
                    f"rag:{document_id}:"
                    f"{chunk.metadata['source_start']}:"
                    f"{chunk.metadata['source_end']}:"
                    f"{chunk.metadata['block_type']}"
                ),
            )
        )

    return chunks
