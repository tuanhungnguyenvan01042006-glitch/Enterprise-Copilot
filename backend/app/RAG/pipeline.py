# File pipeline tổng của toàn bộ thư mục RAG, đa số chỉ là gọi lại hàm tổng của từng Module khác

from app.RAG.Embedding.voyage_langchain import embed_chunks
from app.RAG.Ingestion.pipeline import ingest_document
from app.RAG.vector_store import store_document_points
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.document import Document
from qdrant_client import QdrantClient
from sqlalchemy import select
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


def ingest_and_embed_document(file_path, **kwargs):
    chunks = ingest_document(file_path, **kwargs)    # bao gồm từ clean, chunking, đến embeding
    return embed_chunks(chunks)

# hàm này Ngăn tác vụ cũ ghi đè phiên bản mới
"""
Khi upload phiên bản mới của một tài liệu, hệ thống cập nhật các chunk hiện có và xóa
 những chunk cũ không còn thuộc phiên bản mới. Nếu tài liệu đã thay đổi trong lúc 
 tác vụ nền đang chạy, tác vụ cũ sẽ không ghi đè phiên bản mới.
"""

def index_uploaded_document(file_path, **kwargs):
    """Index the uploaded version only while it is still current."""
    points, errors = ingest_and_embed_document(file_path, **kwargs)
    for error in errors:
        logger.warning("Embedding skipped chunk %s: %s", error.chunk_id, error.reason)
    if not points:
        raise ValueError("Cannot index a document without valid chunks")

    with SessionLocal() as db:
        document = db.scalar(
            select(Document).where(Document.id == UUID(str(kwargs["document_id"]))).with_for_update()
        )
        if document is None or any(
            getattr(document, name) != kwargs[name]
            for name in ("storage_key", "knowledge_scope", "department_id", "title", "category")
        ):
            logger.info("Skipping outdated indexing task for document %s", kwargs["document_id"])
            return False
        settings = get_settings()
        client = QdrantClient(url=settings.qdrant_url)
        try:
            store_document_points(client, settings.qdrant_collection, str(document.id), points)
        finally:
            client.close()
    return True

# vậy hàm này thực tế chả làm cái đ j, hoàn toàn chỉ là gọi lại hàm tổng của Ingestion

# Thắc mắc : tại sao vẫn chưa Langchain ở đâu ?
