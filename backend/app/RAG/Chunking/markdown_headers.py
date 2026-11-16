# Đây là stage 1 : Đang chunking theo markdown header 

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter
from markdown_it import MarkdownIt


def split_document_by_markdown_headers(document: Document) -> list[Document]:
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
        ],
        strip_headers=False,
        return_each_line=False,
    )
    sections = splitter.split_text(document.page_content)


    """
    thêm đoạn này là vì khi chạy hàm MarkdownHeader với 1 đoạn text, nó sẽ
    xóa hàng trống trong đoạn đó, mà kết thúc 1 bảng luôn có hàng trống
    nếu xóa mất, thì có thể gây lỗi, khi code vẫn nhận diện nội dung sau đó là thuộc vào bảng 
    """
    # Restore the original text: the splitter collapses blank lines and some
    # Unicode characters, which can change Markdown tables.
    source_lines = document.page_content.split("\n")
    parser = MarkdownIt("commonmark")
    heading_lines = {
        token.map[0]
        for token in parser.parse(document.page_content)
        if token.type == "heading_open" and token.map and token.tag in {"h1", "h2", "h3", "h4"}
    }
    starts = []
    search_from = 0
    for section_index, section in enumerate(sections):
        section_lines = section.page_content.split("\n")
        first_heading = None
        for token in parser.parse(section.page_content):
            if token.type != "heading_open" or not token.map or token.tag not in {"h1", "h2", "h3", "h4"}:
                continue
            heading = section_lines[token.map[0]].strip()
            position = next(
                (
                    index
                    for index in range(search_from, len(source_lines))
                    if index in heading_lines and source_lines[index].strip() == heading
                ),
                None,
            )
            if position is None:
                raise ValueError("Could not align Markdown sections with the original text.")
            if first_heading is None:
                first_heading = position
            search_from = position + 1
        if section_index and first_heading is None:
            raise ValueError("Could not align Markdown sections with the original text.")
        starts.append(0 if section_index == 0 else first_heading)

    result = []
    for index, section in enumerate(sections):
        end = starts[index + 1] if index + 1 < len(starts) else len(source_lines)
        content = "\n".join(source_lines[starts[index]:end]).strip("\n")
        if not content.strip():
            continue

        section_path = " > ".join(
            section.metadata[level]
            for level in ("h1", "h2", "h3", "h4")
            if section.metadata.get(level)
        )
        result.append(
            Document(
                page_content=content,
                metadata={**document.metadata, "section_path": section_path},
            )
        )

    return result
