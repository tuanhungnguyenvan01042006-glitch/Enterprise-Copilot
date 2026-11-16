"""Run the ingestion pipeline and write artifacts for manual inspection.

Run from the backend directory, for example:

    python -m app.scripts.inspect_ingestion tests/fixtures/rag/handbook_sample.md
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from app.RAG.Ingestion.pipeline import ingest_document


def _document_id(source: Path) -> UUID:
    return uuid5(NAMESPACE_URL, f"rag-inspection:{source.resolve()}")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect Clean/Parse/Chunk output for one Markdown document."
    )
    parser.add_argument("source", type=Path, help="Path to a Markdown document.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for source.md, cleaned.md, chunks.jsonl and report.json.",
    )
    parser.add_argument("--document-id", type=UUID)
    parser.add_argument("--title")
    parser.add_argument("--category")
    parser.add_argument("--chunk-size", type=int, default=700)
    parser.add_argument("--chunk-overlap", type=int, default=70)
    parser.add_argument(
        "--knowledge-scope",
        choices=("COMPANY", "DEPARTMENT"),
        default="COMPANY",
    )
    parser.add_argument("--department-id", type=int)
    parser.add_argument("--storage-key")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source = args.source.expanduser().resolve()
    document_id = args.document_id or _document_id(source)
    title = args.title or source.stem.replace("_", " ").replace("-", " ").title()
    output_dir = args.output_dir or Path("storage/processed/integration") / source.stem
    storage_key = args.storage_key or f"{args.knowledge_scope}/inspection/{source.name}"
    # Đọc vào các tham số từ Command line, nếu ko có thì lấy mặc định tài liệu mẫu 
    # 1 vài tham số đáng chú ý là document_id(dù ko cần test, nma vẫn phải truyền vào cho đủ tham số hàm ingest)
    # ngoài ra còn có output dir : là vị trí muốn lưu file preview

    if args.knowledge_scope == "DEPARTMENT" and args.department_id is None:
        raise SystemExit("--department-id is required for DEPARTMENT scope.")
    if args.knowledge_scope == "COMPANY" and args.department_id is not None:
        raise SystemExit("--department-id must be omitted for COMPANY scope.")
    # Mình thắc mắc là ở đoạn này chỉ muốn kiểm tra pipeline, mà tại sao cần phải kiểm tra cả điều kiện này lm j ? 

    ingest_document(
        source,
        document_id=document_id,
        knowledge_scope=args.knowledge_scope,
        department_id=args.department_id, 
        title=title,
        category=args.category,
        storage_key=storage_key,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        preview_dir=output_dir,
    )
    # Bên trong hàm ingest cũng đã quy định, nếu tham số preview dir ko rỗng, thì nó sẽ chạy ché 
    # độ preview, và lưu các file cleaned.md, chunks.jsonl, report.json vào thư mục preview dir
    # vì vậy ở đây mình ko cần làm gì thêm, mà chỉ cần đọc file report.json ra và in ra terminal là xong

    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    print(f"Inspection complete: {output_dir.resolve()}")
    print(f"Chunks: {report['chunk_count']}")
    print(f"Block types: {report['block_type_counts']}")
    print(f"Token range: {report['min_token_count']}–{report['max_token_count']}")
    print("Open cleaned.md and chunks.jsonl to inspect the output.")
    # Đoạn code này sẽ in ra kết quả report trực tiếp ra terminal
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
