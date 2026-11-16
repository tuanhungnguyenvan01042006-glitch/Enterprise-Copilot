# file này có vai trò là để test pipeline từ ingest (load)--> chunking với dữ liệu mẫu ( tự tạo ra)
import json
from pathlib import Path
from uuid import UUID

from app.RAG.Chunking import markdown_tables, recursive_text
from app.RAG.Chunking import pipeline as chunking_pipeline
from app.RAG.Ingestion.pipeline import ingest_document


FIXTURE = Path(__file__).parents[1] / "fixtures" / "rag" / "handbook_sample.md"
DOCUMENT_ID = UUID("22222222-2222-2222-2222-222222222222")


def count_words(text: str) -> int:
    """Keep this integration test deterministic and offline."""

    return len(text.split())


def test_realistic_document_runs_load_clean_parse_and_chunk(
    tmp_path: Path, monkeypatch
) -> None:
    """Run the real ingestion pipeline and persist inspectable artifacts."""

    monkeypatch.setattr(recursive_text, "count_voyage_tokens", count_words)
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    monkeypatch.setattr(chunking_pipeline, "count_voyage_tokens", count_words)

    preview_dir = tmp_path / "integration-output"
    chunks = ingest_document(
        FIXTURE,
        document_id=DOCUMENT_ID,
        knowledge_scope="DEPARTMENT",
        department_id=7,
        title="Engineering Handbook",
        category="ENGINEERING",
        storage_key="DEPARTMENT/7/document/handbook_sample.md",
        chunk_size=40,
        chunk_overlap=8,
        preview_dir=preview_dir,
    )

    cleaned = (preview_dir / "cleaned.md").read_text(encoding="utf-8")
    records = [
        json.loads(line)
        for line in (preview_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    report = json.loads((preview_dir / "report.json").read_text(encoding="utf-8"))

    assert (preview_dir / "source.md").read_text(encoding="utf-8") == FIXTURE.read_text(
        encoding="utf-8"
    )
    assert chunks
    assert len(records) == len(chunks)

    # Clean/Parse assertions: remove noise but retain useful policy content.
    assert "title: Example Engineering Handbook" not in cleaned
    assert "maintainer note" not in cleaned
    assert "<div" not in cleaned
    assert "</div>" not in cleaned 
    assert "Working style" in cleaned
    assert "Important:" in cleaned
    assert "[request policy](/policies/request)" in cleaned
    assert "[Embedded or dynamic content unavailable in source]" in cleaned

    # Chunking assertions: preserve structures, context, and traceability.
    metadata = [record["metadata"] for record in records]
    assert [item["chunk_index"] for item in metadata] == list(range(len(metadata)))
    assert len({item["chunk_id"] for item in metadata}) == len(metadata)
    assert {item["block_type"] for item in metadata} >= {"text", "table", "mermaid"}
    assert any("| Intake | Requester |" in record["page_content"] for record in records)
    assert any("A[Request] --> B{Review}" in record["page_content"] for record in records)
    assert any("def publish_change" in record["page_content"] for record in records)
    assert any(
        item["section_path"] == "Engineering Handbook > Implementation notes"
        for item in metadata
    )
    assert all(item["token_count"] > 0 for item in metadata)
    assert all(
        0 <= item["source_start"] < item["source_end"] <= len(cleaned)
        for item in metadata
    )
    assert all(record["page_content"].strip() for record in records)

    assert report == {
        "document_id": str(DOCUMENT_ID),
        "chunk_count": len(chunks),
        "block_type_counts": {
            "code": 1,
            "mermaid": 1,
            "table": 1,
            "text": len(chunks)
            - 3,
        },
        "min_token_count": min(item["token_count"] for item in metadata),
        "max_token_count": max(item["token_count"] for item in metadata),
        "chunk_size": 40,
        "chunk_overlap": 8,
    }

    # Stable IDs are important for re-running ingestion without duplicating points.
    repeated_chunks = ingest_document(
        FIXTURE,
        document_id=DOCUMENT_ID,
        knowledge_scope="DEPARTMENT",
        department_id=7,
        title="Engineering Handbook",
        category="ENGINEERING",
        storage_key="DEPARTMENT/7/document/handbook_sample.md",
        chunk_size=40,
        chunk_overlap=8,
        preview_dir=tmp_path / "integration-output-second-run",
    )
    assert [chunk.metadata["chunk_id"] for chunk in chunks] == [
        chunk.metadata["chunk_id"] for chunk in repeated_chunks
    ]
