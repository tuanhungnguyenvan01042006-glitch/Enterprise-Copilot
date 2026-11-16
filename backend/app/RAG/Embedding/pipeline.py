from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from langchain_core.documents import Document

from app.RAG.Embedding.cleaner import clean_embedding_item
from app.RAG.Embedding.types import EmbeddingItem
from app.RAG.Embedding.validation import EmbeddingInputValidationError, build_embedding_item


@dataclass(frozen=True)
class PreparedChunk:
    item: EmbeddingItem
    original_text: str


@dataclass(frozen=True)
class PreparationError:
    index: int
    document_id: str | None
    chunk_id: str | None
    reason: str
# Thắc mắc : Tại sao các module trước ko có phần Kiểm tra, trả về lỗi, mà sao phần này có(hoặc do t ko nhớ)
# Đây là vấn đề của Agent (Overengineering) hay do module này quan trọng hơn : vì nó là sản phẩm cuối cùng được đưa vào Qdrant
# Nhưng quy tắc đúng vẫn là cần kiểm tra đầu vào , đầu ra của mỗi module / mỗi hà 


# Hàm này có tác dụng đưa vào chunks, sau đó thực hiện valid, clean, trả về Embeding Item (đã clean for embed)
def prepare_chunks(
    chunks: Iterable[Document],
) -> tuple[list[PreparedChunk], list[PreparationError]]:
    """Return prepared chunks and validation errors in input order.

    Invalid chunks, including text that becomes empty after cleaning, are
    reported and skipped. Unexpected errors still propagate to the caller.
    """
    prepared: list[PreparedChunk] = []
    errors: list[PreparationError] = []

    for index, chunk in enumerate(chunks):
        try:
            item = clean_embedding_item(build_embedding_item(chunk))  
            # bên trong hàm build embed item có kiểm tra chunk đầu vào 
            # bên trong hàm clean embed item có kiểm tra Embed item (sau khi được )
            # có thể thấy là Công tác Valid ở đây là cực kĩ, kiểm tra đầu vào, đầu ra, từng contract phải chuẩn metadata
            prepared.append(PreparedChunk(item=item, original_text=chunk.page_content))
        except EmbeddingInputValidationError as error:
            metadata = chunk.metadata if isinstance(chunk, Document) else {}
            errors.append(
                PreparationError(
                    # In ra lỗi, chunk thứ bao nhiêu, của document nào, chunk id là gì, reason là gì
                    index=index,
                    document_id=metadata.get("document_id"),
                    chunk_id=metadata.get("chunk_id"),
                    reason=str(error),
                )
            )
    return prepared, errors
