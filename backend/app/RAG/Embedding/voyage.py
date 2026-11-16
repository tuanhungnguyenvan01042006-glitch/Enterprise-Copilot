"""Voyage API calls for document chunks and search queries
Đây là bản tự viết API Request tới Server Voyage bằng httpx, chứ không Dùng Integration của Langchain
."""

# Đây là file kết nối giữa Pipeline Embedding và API của Voyage AI : Tức là ta sẽ bọc các API Call bên trong 1 hàm backend để dễ quản lý
# Thắc mắc : Ko thấy sử dụng Langchain 
# NOTE : Đây là cách ko sử dụng Langchain mà sử dụng Httpx để kết nối tới Voyage 
from __future__ import annotations

import os
import math

import httpx
# Thư viện httpx (của python) hỗ trợ gửi HTTP request, hỗ trợ async 

from app.RAG.Chunking.tokenizer import count_voyage_tokens
from app.RAG.config import DOCUMENT_EMBEDDING_MODEL, EMBEDDING_DIMENSION, QUERY_EMBEDDING_MODEL
from app.RAG.Embedding.pipeline import PreparedChunk, PreparationError, prepare_chunks
from app.RAG.Embedding.types import EmbeddedPoint
from app.RAG.Embedding.validation import validate_embedded_point

 
_API_URL = "https://api.voyageai.com/v1"
# Giải thích API URL : Là cổng giao tiếp với nền tảng Voyage :
"""
Base URL này chính là nơi tiếp nhận các HTTP Request (thường là POST request) 
chứa văn bản từ các ứng dụng bên ngoài
xử lý qua các mô hình AI của họ, và trả về kết quả dưới định dạng JSON.
"""

# Leave room below the 320,000-token request limit.
_BATCH_TOKEN_BUDGET = 300000    # giới hạn của Batch : chứ ko phải giới hạn của Đầu vào model (32k)


# Hàm tạo Request tới API Voyage 
def _post(path: str, payload: dict) -> dict:
    key = os.environ.get("VOYAGE_API_KEY", "").strip()
    # Cần chuẩn bị sẵn API key 
    if not key:
        raise ValueError("VOYAGE_API_KEY is required for Voyage embeddings")
    response = httpx.post(
        f"{_API_URL}/{path}", json=payload,
        headers={"Authorization": f"Bearer {key}"}, timeout=120.0,
    )
    #  
    response.raise_for_status()
    return response.json()
# Tóm lại thì cụ thể, hàm này dùng cho tác vụ gì : Chat,embed chunk ,...?

def _ordered_vectors(data: list, expected: int) -> list[list[float]]:  
    # data ở đây chính là vector / expected là số lượng vecotr 
    if len(data) != expected or sorted(row["index"] for row in data) != list(range(expected)):
        raise ValueError("Voyage returned an unexpected number or order of embeddings")
    vectors = [row["embedding"] for row in sorted(data, key=lambda row: row["index"])]
    if any(not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSION for vector in vectors):
        raise ValueError("Voyage returned an embedding with an unexpected dimension")
    return vectors
# Vẫn thắc mắc là nếu xảy ra lỗi thì sẽ rollback như thế nào?
"""
_ordered_vectors(data, expected)
Hàm này kiểm tra và sắp xếp vector do API trả về:
- Số vector phải bằng số lượng mong đợi.
- Mỗi vector phải có index hợp lệ, không thiếu hoặc trùng.
- Sắp xếp vector theo index, để ghép đúng với thứ tự text đã gửi.
- Mỗi vector phải có đúng 1.024 chiều theo cấu hình hiện tại.
 * Tuy nhiên theo mình nghĩ thì các tác vụ này Langchain có thể hỗ trợ hết, tại sao lại cần viết thủ công hàm như này
"""


# Hàm này nhận vào danh sách Chunks (thuộc cùng 1 tài liệu), đem đi Embed (gọi lại hàm post API) rồi trả về Vector
def _embed_group(group: list[PreparedChunk]) -> list[EmbeddedPoint]:   
    response = _post("embeddings", {
        "model": DOCUMENT_EMBEDDING_MODEL,
        "input": [chunk.item.text for chunk in group],  # Truyền vào text (đã đc clean)
        "input_type": "document",
        "output_dimension": EMBEDDING_DIMENSION,
        "truncation": False,
    })
    vectors = _ordered_vectors(response["data"], len(group))  # cần sắp xếp lại danh sách vector nhận về, để nó đúng thứ tự so với danh sách chunk gửi vào ( tức là vector phải đi đúng với chunk của nó)
    points = []
    for chunk, vector in zip(group, vectors):
        point = EmbeddedPoint(chunk.item.point_id, vector, chunk.original_text, chunk.item.metadata)
        validate_embedded_point(point)
        points.append(point)
    return points



# hàm này là hàm chính : Nó nối lại toàn bộ quy trình từ lúc nhận chunk, valid chunk, tạo embed item, tới gọi API Voyage để embed, và trả về vectors theo từng chunks
# Hàm này nên bỏ vào pipeline,vì nó là hàm tổng ,chứa toàn bộ pipeline của Module này , nma thôi ko chuyển sang đâu, mệt lắm.
def embed_chunks(chunks) -> tuple[list[EmbeddedPoint], list[PreparationError]]:
    """Prepare chunks and embed them in input order in bounded batches."""
    prepared, errors = prepare_chunks(chunks)
    points: list[EmbeddedPoint] = []
    group: list[PreparedChunk] = []    # Thực tế đây chính là batch : Danh sách chunks được gửi trong cùng 1 API Request
    group_tokens = 0
    for chunk in prepared:
        # Voyage prepends this prompt when input_type is document.
        tokens = count_voyage_tokens("Represent the document for retrieval: " + chunk.item.text)
        if tokens > 32000:
            raise ValueError(f"Chunk {chunk.item.point_id} exceeds the 32000-token model limit")
        if group and (group_tokens + tokens > _BATCH_TOKEN_BUDGET or len(group) >= 1000):
            # Ở đây sẽ gửi API post theo batch (gửi nhiều chunks cùng 1 API request)
            # nó duyệt dần từng chunk vào batch, nếu phát hiện chunk tới làm vượt quá giới hạn batch
            # thì ko thêm nữa, mà gửi API request với batch hiện tại (đã đầy) luôn, sau đó reset batch về rỗng
            points.extend(_embed_group(group))
            group, group_tokens = [], 0
        group.append(chunk)
        group_tokens += tokens
    if group:        # Nếu còn batch chưa được gửi , thì gửi nốt
        points.extend(_embed_group(group))
    return points, errors
# Với cơ chế hiện tại, tất cả chunks trong cùng 1 batch chắc chắn trong cùng 1 tài liệu


def embed_query(query: str) -> list[float]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    response = _post("embeddings", {
        "model": QUERY_EMBEDDING_MODEL, "input": [query], "input_type": "query",
        "output_dimension": EMBEDDING_DIMENSION, "truncation": False,
    })
    vector = _ordered_vectors(response["data"], 1)[0]
    # Reuse the existing finite-number checks without requiring chunk metadata.
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in vector):
        raise ValueError("Voyage returned an invalid query embedding")
    return vector
