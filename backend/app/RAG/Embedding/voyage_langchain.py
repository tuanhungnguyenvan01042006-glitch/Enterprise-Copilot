"""Tạo embedding bằng integration Voyage AI (tức là hàm có sẵn của Langchain :bao gồm các hàm embed Document / Querry sẵn 

."""

from __future__ import annotations

import math

from langchain_voyageai import VoyageAIEmbeddings
# Sử dụng Langchain

from app.RAG.config import DOCUMENT_EMBEDDING_MODEL, EMBEDDING_DIMENSION, QUERY_EMBEDDING_MODEL
from app.RAG.Embedding.pipeline import PreparationError, prepare_chunks
from app.RAG.Embedding.types import EmbeddedPoint
from app.RAG.Embedding.validation import validate_embedded_point


# Đầu tiên là cần gọi Model mà mình sử dụng : Thắc mắc , tại sao ko khai báo API Key ở đây 
def _model(name: str) -> VoyageAIEmbeddings:
    return VoyageAIEmbeddings(
        model=name, output_dimension=EMBEDDING_DIMENSION, truncation=False
    )

# Điểm khác biệt là ở đây ko cần viết hàm post (httpx) , ko cần truyền vào từng Tham số cấu hình 
# Ko cần viết hàm hỗ trợ như ordered vector (để sắp xếp lại vector trả về theo đúng thứ tự) , hay quản lý batch ( dồn chunk vào từng batch, để nó ko vượt giới hạn batch ) 
# nói chung các tính năng cơ bản của Embed đã được tích hợp, hỗ trợ sẵn hết bởi Langchain, ta chỉ cần gọi hàm 
# GỌi hàm embed document để embed chunk và embed querry để embed querry 

# Mặc dù chỉ việc gọi hàm, tuy nhiên ,1 số chức năng nâng cao trong pipeline embed như Validate, clean,... thì vẫn phải thủ công tự thêm hàm vào 
# vì vậy ta vẫn phải định nghĩa 1 hàm nội bộ, rồi gọi lần lượt các hàm như pipeline Embed 
def embed_chunks(chunks) -> tuple[list[EmbeddedPoint], list[PreparationError]]:

    # trước tiên vẫn phải validate chunks đầu vào thủ công (vì validate ở đây thường do bài toán cụ thể, do dev quy định, nên ko thể nhờ Langchain)
    prepared, errors = prepare_chunks(chunks)
    if not prepared:
        return [], errors

    # LangChain xử lý việc gọi Voyage và chia batch theo giới hạn của nó ( chứ ko phải giới hạn batch mình tự định nghĩa) 
    vectors = _model(DOCUMENT_EMBEDDING_MODEL).embed_documents(
        [chunk.item.text for chunk in prepared]
    )
    if len(vectors) != len(prepared):
        raise ValueError("Voyage returned an unexpected number of embeddings")

    points = []
    for chunk, vector in zip(prepared, vectors):
        if len(vector) != EMBEDDING_DIMENSION:
            raise ValueError("Voyage returned an embedding with an unexpected dimension")
        # hàm embed chỉ trả về danh sách Vector, ta vẫn phải tự gắn vector vào chunks, đẻ tạo point 
        point = EmbeddedPoint(chunk.item.point_id, vector, chunk.original_text, chunk.item.metadata)
        validate_embedded_point(point)
        points.append(point)
    return points, errors


def embed_query(query: str) -> list[float]:
    """Tạo vector cho câu hỏi tìm kiếm."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    vector = _model(QUERY_EMBEDDING_MODEL).embed_query(query)
    if len(vector) != EMBEDDING_DIMENSION or any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
        for value in vector
    ):
        raise ValueError("Voyage returned an invalid query embedding")
    return vector
