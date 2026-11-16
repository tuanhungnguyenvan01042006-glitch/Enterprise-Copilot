from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.RAG.Chunking.tokenizer import count_voyage_tokens


DEFAULT_CHUNK_SIZE = 700           # NOTE : Cần thử nghiệm với nhiều chunk size, chunk overlap để tìm được thông số phù hợp nhất
DEFAULT_CHUNK_OVERLAP = 70


def split_long_text_blocks(
    blocks: list[Document],     # hàm nhận vào 1 list[document] bản chất chính là list chunks, thuộc cùng 1 Document đầu vào 
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and chunk_overlap must be smaller than chunk_size.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=count_voyage_tokens,
        add_start_index=True,
    )

    result = []
    for block in blocks:
        if (
            block.metadata.get("block_type") != "text"
            or count_voyage_tokens(block.page_content) <= chunk_size
        ):
            result.append(block)
        else:
            chunks = splitter.split_documents([block])
            local_search_from = 0
            for chunk in chunks:
                local_start = chunk.metadata.pop("start_index")
                if local_start < 0:
                    local_start = block.page_content.find(
                        chunk.page_content, local_search_from
                    )
                if local_start < 0:
                    raise ValueError("Could not locate a text chunk in its parent block.")
                if "source_start" in block.metadata:
                    chunk.metadata["source_start"] = block.metadata["source_start"] + local_start
                    chunk.metadata["source_end"] = (
                        chunk.metadata["source_start"] + len(chunk.page_content)
                    )
                local_search_from = local_start + 1
            result.extend(chunks)
            # Hàm Split document này sẽ trả về 1 list[Document] : là các chunk con được sinh ra từ block >700 token. Sau đó , các chunk này sẽ được append vào result

    return result    # result ở đây chính là list [documents] (chính là chunks) sinh ra từ 1 document gốc
