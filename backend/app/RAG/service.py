# Là nơi giao tiếp với BE , cung cấp Rag Service cho BE 
# service là nơi điều phối các pipeline : ingestion, retrieve, generate của rag 
# ( Ví dụ, khi có người dùng ask question, gửi yêu cầu tới Rag service, chính service là nơi điều phối question đó đi qua retrival và generate)

from qdrant_client import QdrantClient

from app.RAG.Embedding.voyage_langchain import embed_query
from app.RAG.generation import generate_answer
from app.core.config import get_settings

 
def retrieve_chunks(query: str, top_k: int = 5) -> list[dict]:
    """Tìm chunk theo câu hỏi; chỉ dùng nội bộ, chưa kiểm tra quyền người dùng."""
    if not isinstance(top_k, int) or isinstance(top_k, bool) or not 1 <= top_k <= 100:
        raise ValueError("top_k must be an integer between 1 and 100")
    vector = embed_query(query)
    settings = get_settings()
    client = QdrantClient(url=settings.qdrant_url)
    try:
        if not client.collection_exists(settings.qdrant_collection):
            return []
        results = client.query_points(         # Vậy hàm để Retrieve là query_points
            collection_name=settings.qdrant_collection,
            query=vector,
            limit=top_k,
            with_payload=True,
        ).points
        return [{"id": str(point.id), "score": point.score, **(point.payload or {})} for point in results]
        # point.payload là nơi chứa Text 
    finally:
        client.close()


def answer_question(query: str, top_k: int = 5) -> dict:
    """Trả lời nội bộ dựa trên các chunk tìm được; chưa kiểm tra quyền."""
    return generate_answer(query, retrieve_chunks(query, top_k))
 # Hàm Generate Answer sẽ gọi lại hàm retrieve Chunks để thu được những relavant chunks 
