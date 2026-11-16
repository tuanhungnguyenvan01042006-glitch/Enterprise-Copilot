from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from uuid import UUID

from langchain_core.documents import Document

from app.core.config import get_settings
from app.RAG.Chunking.pipeline import chunk_document
from app.RAG.Ingestion.CleanernParser.cleaner import clean_document
from app.RAG.Ingestion.loader import load_document


def ingest_document(
    file_path: str | Path,
    *,    # các tham số sau * phải truyền theo tên ; vd : (knowledge_scope=Company)
    document_id: UUID | str,
    knowledge_scope: str,
    department_id: int | None,
    title: str,
    category: str | None,
    storage_key: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    preview_dir: str | Path | None = None,
) -> list[Document]:
    documents = load_document(
        file_path,
        document_id=document_id,
        knowledge_scope=knowledge_scope,
        department_id=department_id,
        title=title,
        category=category,
        storage_key=storage_key,
    )
    # phần nội dung phía dưới này là nội dung bên trong hàm document, tức là ta 
    # chỉ cần truyền vào Document,Document sẽ được chạy qua hàm clean, chunk 
    cleaned_documents = [clean_document(document) for document in documents]
    chunk_kwargs = {}
    if chunk_size is not None:
        chunk_kwargs["chunk_size"] = chunk_size
    if chunk_overlap is not None:
        chunk_kwargs["chunk_overlap"] = chunk_overlap
    chunks = [
        chunk
        for document in cleaned_documents
        for chunk in chunk_document(document, **chunk_kwargs)
    ]
    # Đoạn này cú pháp hơi phức tạp 1 chút, có thể hiểu là lấy document chia ra làm các chunk sau đó góp vào danh sách chunks


    # Phần đoạn dưới này chỉ là logic để chạy preview, kiểm tra xem output oke chưa 
    if preview_dir is None:
        settings = get_settings()
        if settings.app_env.lower() != "development": 
            return chunks
        # Nếu ko phải đang ở chế độ dev, thì ko chạy preview.
        processed_dir = settings.upload_dir.parent / "processed"
        cleaned_preview_dir = processed_dir / "cleaned"
        cleaned_preview_dir.mkdir(parents=True, exist_ok=True)
        cleaned_preview_file = cleaned_preview_dir / f"{document_id}.md"
        # Tạo ra địa chỉ file cleaned 
        cleaned_preview_file.write_text(
            "\n\n".join(document.page_content for document in cleaned_documents),
            encoding="utf-8",
        )   # Viết lại bản preview của file cleaned ra địa chỉ processed/cleaned/document_id.md

        chunk_preview_dir = processed_dir / "chunks"
        chunk_preview_dir.mkdir(parents=True, exist_ok=True)
        chunk_preview_file = chunk_preview_dir / f"{document_id}.jsonl"
        # Viết lại bản preview của file chunks ra địa chỉ processed/chunks/document_id.jsonl
        chunk_preview = "\n".join(
            json.dumps(
                {"page_content": chunk.page_content, "metadata": chunk.metadata},
                ensure_ascii=False,
                default=str,
            )
            for chunk in chunks
        )
        if chunks:
            chunk_preview += "\n"
        chunk_preview_file.write_text(chunk_preview, encoding="utf-8")
    else:
        preview_root = Path(preview_dir)
        preview_root.mkdir(parents=True, exist_ok=True)
        Path(preview_root / "source.md").write_text(
            Path(file_path).read_text(encoding="utf-8-sig"),
            encoding="utf-8",
        )
        (preview_root / "cleaned.md").write_text(
            "\n\n".join(document.page_content for document in cleaned_documents),
            encoding="utf-8",
        )
        (preview_root / "chunks.jsonl").write_text(
            "\n".join(
                json.dumps(
                    {"page_content": chunk.page_content, "metadata": chunk.metadata},
                    ensure_ascii=False,
                    default=str,
                )
                for chunk in chunks
            )
            + ("\n" if chunks else ""),
            encoding="utf-8",
        )
        block_types = Counter(chunk.metadata["block_type"] for chunk in chunks)
        token_counts = [chunk.metadata["token_count"] for chunk in chunks]
        (preview_root / "report.json").write_text(
            json.dumps(
                {
                    "document_id": str(document_id),
                    "chunk_count": len(chunks),
                    "block_type_counts": dict(sorted(block_types.items())),
                    "min_token_count": min(token_counts) if token_counts else 0,
                    "max_token_count": max(token_counts) if token_counts else 0,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return chunks
