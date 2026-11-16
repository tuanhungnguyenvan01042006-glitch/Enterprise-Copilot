"""Lưu các chunk đã embedding vào Qdrant."""

from qdrant_client import QdrantClient, models

"""
- QdrantClient : Đây là client để ứng dụng Python kết nối và gửi thao tác đến máy chủ 
Qdrant, nơi lưu trữ và tìm kiếm vector. 
  + Thực tế có thể hiểu QdrantClient chính là tài khoản Qdrant, và ở khi gọi hàm, ta sẽ truyền qdrant_url vào client này 
- models : Đây là namespace chứa các kiểu dữ liệu và cấu hình mà Qdrant dùng cho yêu cầu.
Nó không phải một model dữ liệu riêng của ứng dụng.
"""
"""
* Giải thích cách tích hợp Qdrant (thông qua qdrant_url (client)) :
+ thực tế nó giống các database khác như postgresql chính trong dự án này : 
không cần lấy QDRANT_URL từ website hay đăng ký tài khoản cho cấu hình hiện tại.
Project đã chạy Qdrant trên máy bạn bằng Docker
"""
from app.RAG.config import EMBEDDING_DIMENSION

from app.RAG.Embedding.types import EmbeddedPoint
from app.RAG.Embedding.validation import validate_embedded_point

# Collection : danh sách vector (có thể hiểu chính là 1 Database/ Table của vector)
# Hàm này kiểm tra Collection vector đã tồn tại chưa, nếu chưa thì khởi tạo Collection (tức chính là khởi tạo Vector Database)
def ensure_collection(client: QdrantClient, collection: str) -> None:
    if not client.collection_exists(collection):    # Kiểm tra xem đã tồn tại collection vector chx
        try:
            # nếu chưa có thì khởi tạo Collection, với tên, cấu hình vector, và công thức tính Khoảng cách 
            client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(size=EMBEDDING_DIMENSION, distance=models.Distance.COSINE),
            )
        except Exception:
            if not client.collection_exists(collection):
                raise
    config = client.get_collection(collection).config.params.vectors
    if not isinstance(config, models.VectorParams) or config.size != EMBEDDING_DIMENSION or config.distance != models.Distance.COSINE:
        raise ValueError("Qdrant collection must use 1024-dimensional cosine vectors")

   # hàm chính để đưa vector vào Qdrant
def store_document_points(
    client: QdrantClient, collection: str, document_id: str, points: list[EmbeddedPoint]
) -> None:
    """Upsert phiên bản mới, sau đó xóa những chunk cũ không còn tồn tại."""
    if not points:
        raise ValueError("Cannot index a document without valid chunks")
    
    ids = [point.point_id for point in points]   # Lấy ra danh sách point_id
    if len(ids) != len(set(ids)):   # hàm set tạo ra 1 danh sách ko bị trùng nhau --> hàm kiểm tra có Vector / Chunk nào bị lặp lại 2 lần hay không
        raise ValueError("Duplicate chunk IDs in document")
    for point in points:
        validate_embedded_point(point)   # Kiểm tra đ j lắm thế ?
        if point.metadata["document_id"] != document_id:
            raise ValueError("Point document_id does not match the document")
        if len(point.vector) != EMBEDDING_DIMENSION:
            raise ValueError("Embedding vector has an unexpected dimension")

    ensure_collection(client, collection)

    # Hàm thêm Vector vào Qdrant
    client.upsert(
        collection_name=collection,
        points=[models.PointStruct(id=point.point_id, vector=point.vector,
                                   payload={**point.metadata, "text": point.text}) for point in points],
        wait=True,
    )

    # Đây chính là hàm xử lý logic khi update file : xóa bỏ vector cũ
    client.delete(
        collection_name=collection,
        points_selector=models.FilterSelector(filter=models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))],
            # xóa bỏ các vector có trùng Document_id
            must_not=[models.HasIdCondition(has_id=ids)],
            # Ngoại trừ các vector vừa mới thêm vào trong phiên này (các vector mới)
        )),
        wait=True,
    )
