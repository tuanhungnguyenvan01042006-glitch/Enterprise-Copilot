"""Index các tài liệu đã lưu trong PostgreSQL, bao gồm tài liệu import hàng loạt."""

import argparse
from pathlib import Path

from sqlalchemy import select

import app.db.base  # Register mapped tables.
from app.RAG.pipeline import index_uploaded_document
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.document import Document 


def index_documents(limit: int | None = None, offset: int = 0) -> int:
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    if offset < 0:
        raise ValueError("offset must not be negative")
    root = get_settings().upload_dir.resolve()
    with SessionLocal() as db:
        statement = select(Document).order_by(Document.created_at, Document.id).offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        documents = [
            (doc.id, doc.storage_key, doc.knowledge_scope, doc.department_id, doc.title, doc.category)
            for doc in db.scalars(statement)
        ]

    succeeded = failed = 0
    for document_id, storage_key, scope, department_id, title, category in documents:
        try:
            path = (root / storage_key).resolve()
            if root not in path.parents or not path.is_file():
                raise ValueError("document file is missing or outside the upload directory")
            indexed = index_uploaded_document(
                path, document_id=document_id, storage_key=storage_key,
                knowledge_scope=scope, department_id=department_id, title=title, category=category,
            )
            if not indexed:
                raise RuntimeError("document changed during indexing; retry it")
            succeeded += 1
            print(f"INDEXED {document_id}")
        except Exception as exc:
            failed += 1
            print(f"FAILED {document_id}: {type(exc).__name__}: {exc}")
    print(f"Completed: indexed={succeeded}, failed={failed}, total={len(documents)}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Index documents already imported into the application.")
    parser.add_argument("--limit", type=int, help="Index only the first N documents, useful for a small trial.")
    parser.add_argument("--offset", type=int, default=0, help="Skip this many documents before indexing.")
    args = parser.parse_args()
    return index_documents(args.limit, args.offset)


if __name__ == "__main__":
    raise SystemExit(main())
