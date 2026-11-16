"""Estimate Voyage 4 tokens for a Markdown corpus.

This reports raw, cleaned, chunked, and embedding-input token totals. The
embedding-input total is the closest estimate for embedding cost because it
uses the same tokenizer and the current Clean/Parse, Chunking, and Embedding
Cleaner stages.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.RAG.Chunking.pipeline import chunk_document
from app.RAG.Chunking.tokenizer import count_voyage_tokens
from app.RAG.Embedding.cleaner import clean_embedding_item
from app.RAG.Embedding.validation import build_embedding_item
from app.RAG.Ingestion.CleanernParser.cleaner import clean_document
from app.RAG.Ingestion.loader import load_markdown_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate voyageai/voyage-4 tokens for a Markdown corpus."
    )
    parser.add_argument("root", type=Path, help="Root directory to scan recursively.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("storage/processed/token-estimate.json"),
        help="JSON report path.",
    )
    parser.add_argument("--chunk-size", type=int, default=700)
    parser.add_argument("--chunk-overlap", type=int, default=70)
    return parser


def _metadata(root: Path, source: Path) -> dict[str, object]:
    relative = source.relative_to(root).as_posix()
    document_id = str(uuid5(NAMESPACE_URL, f"rag-token-estimate:{relative}"))
    return {
        "document_id": document_id,
        "knowledge_scope": "COMPANY",
        "department_id": None,
        "title": source.stem,
        "category": None,
        "storage_key": f"COMPANY/token-estimate/{relative}",
    }


def _sum_tokens(texts: list[str]) -> int:
    return sum(count_voyage_tokens(text) for text in texts)


def estimate(root: Path, *, chunk_size: int, chunk_overlap: int) -> dict[str, object]:
    root = root.expanduser().resolve(strict=True)
    sources = sorted(path for path in root.rglob("*.md") if path.is_file())
    failures: list[dict[str, str]] = []
    file_summaries: list[dict[str, object]] = []
    failed_sources: set[str] = set()
    block_types: Counter[str] = Counter()
    raw_tokens = 0
    cleaned_tokens = 0
    chunk_tokens = 0
    embedding_input_tokens = 0
    embedding_skipped_chunks = 0
    embedding_skipped_candidate_tokens = 0
    document_count = 0
    chunk_count = 0

    for source in sources:
        relative_source = source.relative_to(root).as_posix()
        summary: dict[str, object] = {
            "source": relative_source,
            "status": "ok",
            "raw_document_tokens": 0,
            "cleaned_document_tokens": 0,
            "chunk_count": 0,
            "chunk_content_tokens": 0,
            "embedding_input_tokens": 0,
            "embedding_skipped_chunks": 0,
        }
        try:
            documents = load_markdown_file(source, metadata=_metadata(root, source))
            document_count += len(documents)
            file_raw_tokens = _sum_tokens([document.page_content for document in documents])
            raw_tokens += file_raw_tokens
            summary["raw_document_tokens"] = file_raw_tokens

            cleaned_documents = [clean_document(document) for document in documents]
            file_cleaned_tokens = _sum_tokens(
                [document.page_content for document in cleaned_documents]
            )
            cleaned_tokens += file_cleaned_tokens
            summary["cleaned_document_tokens"] = file_cleaned_tokens

            try:
                chunks = [
                    chunk
                    for document in cleaned_documents
                    for chunk in chunk_document(
                        document,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                ]
            except Exception as exc:
                summary["status"] = "failed"
                failed_sources.add(relative_source)
                failures.append(
                    {
                        "source": relative_source,
                        "stage": "chunking",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
                file_summaries.append(summary)
                continue

            chunk_count += len(chunks)
            file_chunk_tokens = _sum_tokens([chunk.page_content for chunk in chunks])
            chunk_tokens += file_chunk_tokens
            summary["chunk_count"] = len(chunks)
            summary["chunk_content_tokens"] = file_chunk_tokens

            for chunk in chunks:
                block_type = str(chunk.metadata["block_type"])
                block_types[block_type] += 1
                try:
                    embedding_item = clean_embedding_item(build_embedding_item(chunk))
                    item_tokens = count_voyage_tokens(embedding_item.text)
                    embedding_input_tokens += item_tokens
                    summary["embedding_input_tokens"] = (
                        int(summary["embedding_input_tokens"]) + item_tokens
                    )
                except Exception as exc:
                    candidate_tokens = count_voyage_tokens(chunk.page_content)
                    embedding_skipped_chunks += 1
                    embedding_skipped_candidate_tokens += candidate_tokens
                    summary["status"] = "partial"
                    summary["embedding_skipped_chunks"] = (
                        int(summary["embedding_skipped_chunks"]) + 1
                    )
                    failed_sources.add(relative_source)
                    failures.append(
                        {
                            "source": relative_source,
                            "stage": "embedding_cleaner",
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )
        except Exception as exc:  # Keep the corpus estimate useful if one file is malformed.
            summary["status"] = "failed"
            failed_sources.add(relative_source)
            failures.append(
                {
                    "source": relative_source,
                    "stage": "load_or_clean",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        file_summaries.append(summary)

    report = {
        "tokenizer": "voyageai/voyage-4",
        "root": str(root),
        "source_file_count": len(sources),
        "processed_document_count": document_count,
        "chunk_count": chunk_count,
        "block_type_counts": dict(sorted(block_types.items())),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "raw_document_tokens": raw_tokens,
        "cleaned_document_tokens": cleaned_tokens,
        "chunk_content_tokens": chunk_tokens,
        "embedding_input_tokens": embedding_input_tokens,
        "embedding_skipped_chunks": embedding_skipped_chunks,
        "embedding_skipped_candidate_tokens": embedding_skipped_candidate_tokens,
        "failed_file_count": len(failed_sources),
        "failure_count": len(failures),
        "failures": failures,
        "file_summaries": file_summaries,
    }
    return report


def main() -> int:
    args = build_parser().parse_args()
    report = estimate(
        args.root,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Token estimate written to: {args.output.resolve()}")
    print(f"Source files: {report['source_file_count']}")
    print(f"Processed documents: {report['processed_document_count']}")
    print(f"Chunks: {report['chunk_count']}")
    print(f"Raw document tokens: {report['raw_document_tokens']:,}")
    print(f"Cleaned document tokens: {report['cleaned_document_tokens']:,}")
    print(f"Chunk content tokens: {report['chunk_content_tokens']:,}")
    print(f"Embedding input tokens: {report['embedding_input_tokens']:,}")
    print(f"Skipped embedding chunks: {report['embedding_skipped_chunks']}")
    print(
        "Skipped candidate tokens: "
        f"{report['embedding_skipped_candidate_tokens']:,}"
    )
    print(f"Failed files: {report['failed_file_count']}")
    print(f"Failures: {report['failure_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
