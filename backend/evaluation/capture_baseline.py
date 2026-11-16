"""Read PostgreSQL and Qdrant and record a reproducible retrieval baseline """
"""
Script này tạo ra basline.json ; vai trò của baseline.json : 
- lưu thông tin tại thời điểm chụp của Qdrant : Số documen, point,... thông tin cơ bản của từng chunk,...
--> MỤC ĐÍCH : Để phát hiện xem Postgresql và Qdrant có sự thay đổi gì ko : Tóm lại là để xem Collection có thay đổi j ko , chỉ vậy thui 
-  Thời điểm capture : khi dữ liệu và Qdrant đã nạp/index ổn định : trước khi benchmark, hoặc trước 1 thay đổi lớn cần so sánh dữ liệu trước và sau 
- Tại sao nó cần thiết với Benchmark : cx chx hiểu lắm ?? 

* Cụ thể thì File này làm gì : 
Script tạo lại baseline.json.
Khi chạy, script:
1. Đọc document từ PostgreSQL.
2. Đọc các point, payload và vector từ Qdrant.
3. Kiểm tra document thiếu/dư và point thiếu text.
4. Tính fingerprint của dữ liệu Qdrant.
5. Ghi cấu hình và kết quả vào baseline.json.
Lưu ý: chạy script sẽ ghi đè baseline.json hiện tại. Nếu cần so sánh với baseline cũ, phải lưu lại bản cũ trước.
"""


import hashlib
import json
import struct
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client import QdrantClient
from sqlalchemy import select

import app.db.base  # Register ORM models.
from app.RAG.Chunking.recursive_text import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
from app.RAG.Chunking.tokenizer import TOKENIZER_ID
from app.RAG.config import DOCUMENT_EMBEDDING_MODEL, EMBEDDING_DIMENSION, QUERY_EMBEDDING_MODEL
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.document import Document


def main() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        documents = sorted(
            [{"id": str(d.id), "checksum_sha256": d.checksum_sha256, "revision": d.revision}
             for d in db.scalars(select(Document))],
            key=lambda d: d["id"],
        )
    ids = {d["id"] for d in documents}
    client = QdrantClient(url=settings.qdrant_url)
    counts = Counter()
    point_digests = []
    missing_text = 0
    try:
        collection = client.get_collection(settings.qdrant_collection)
        config = collection.config.params.vectors
        offset = None
        while True:
            points, offset = client.scroll(settings.qdrant_collection, limit=128, offset=offset,
                                           with_payload=True, with_vectors=True)
            for point in points:
                payload = point.payload or {}
                counts[str(payload.get("document_id"))] += 1
                missing_text += not bool(payload.get("text"))
                digest = hashlib.sha256()
                digest.update(str(point.id).encode())
                digest.update(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
                if not isinstance(point.vector, list):
                    raise ValueError("Expected a single unnamed vector per point")
                digest.update(struct.pack(f"<{len(point.vector)}f", *point.vector))
                point_digests.append(digest.hexdigest())
            if offset is None:
                break
    finally:
        client.close()
    baseline = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "collection": settings.qdrant_collection,
        "document_count": len(documents),
        "point_count": len(point_digests),
        "indexed_document_count": len(counts),
        "missing_document_ids": sorted(ids - set(counts)),
        "extra_document_ids": sorted(set(counts) - ids),
        "points_missing_text": missing_text,
        "qdrant_vector_size": config.size,
        "qdrant_distance": str(config.distance.value),
        "point_payload_and_vector_sha256": hashlib.sha256("\n".join(sorted(point_digests)).encode()).hexdigest(),
        "documents": documents,
        "current_pipeline_configuration": {
            "document_embedding_model": DOCUMENT_EMBEDDING_MODEL,
            "query_embedding_model": QUERY_EMBEDDING_MODEL,
            "embedding_dimension": EMBEDDING_DIMENSION,
            "tokenizer": TOKENIZER_ID,
            "chunk_size": DEFAULT_CHUNK_SIZE,
            "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
        },
        "known_skipped_chunks": [
            {"document": "Cadence", "chunk_id": "417c6087-075c-5aa3-b7b2-a00b845acdf6", "reason": "empty after embedding cleaning"},
            {"document": "GitLab Values", "chunk_id": "3fe4e617-9e6e-51b3-9a79-9b84fd3a5f33", "reason": "empty after embedding cleaning"},
        ],
        "note": "Pipeline configuration is current code configuration; existing Qdrant points do not record model/version provenance.",
    }
    output = Path(__file__).with_name("baseline.json")
    output.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {output}: documents={len(documents)}, points={len(point_digests)}, "
          f"missing={len(baseline['missing_document_ids'])}, extra={len(baseline['extra_document_ids'])}, "
          f"missing_text={missing_text}")


if __name__ == "__main__":
    main()
