import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from app.RAG.Chunking import markdown_tables, recursive_text
from app.RAG.Chunking import pipeline as chunking_pipeline
from app.RAG.Ingestion import pipeline as ingestion_pipeline
from app.RAG.Ingestion.pipeline import ingest_document


def count_words(text: str) -> int:
    return len(text.split())


def test_ingest_document_cleans_chunks_and_saves_development_previews(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(recursive_text, "count_voyage_tokens", count_words)
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    monkeypatch.setattr(chunking_pipeline, "count_voyage_tokens", count_words)
    settings = SimpleNamespace(
        app_env="development",
        upload_dir=tmp_path / "storage" / "uploads",
    )
    monkeypatch.setattr(ingestion_pipeline, "get_settings", lambda: settings)

    source = tmp_path / "policy.md"
    source.write_text(
        "---\n"
        "title: Source title\n"
        "---\n\n"
        "<!-- internal comment -->\n"
        "# Password Policy\n\n"
        "Use a strong password.\n",
        encoding="utf-8",
    )

    chunks = ingest_document(
        source,
        document_id=UUID("11111111-1111-1111-1111-111111111111"),
        knowledge_scope="DEPARTMENT",
        department_id=1,
        title="Password Policy",
        category=None,
        storage_key="DEPARTMENT/1/document/policy.md",
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.page_content == "# Password Policy\n\nUse a strong password."
    assert {
        key: chunk.metadata[key]
        for key in (
            "source",
            "file_name",
            "file_type",
            "document_id",
            "knowledge_scope",
            "department_id",
            "title",
            "category",
            "storage_key",
        )
    } == {
        "source": "policy.md",
        "file_name": "policy.md",
        "file_type": "markdown",
        "document_id": "11111111-1111-1111-1111-111111111111",
        "knowledge_scope": "DEPARTMENT",
        "department_id": 1,
        "title": "Password Policy",
        "category": None,
        "storage_key": "DEPARTMENT/1/document/policy.md",
    }
    assert chunk.metadata["section_path"] == "Password Policy"
    assert chunk.metadata["block_type"] == "text"
    assert chunk.metadata["chunk_index"] == 0
    assert chunk.metadata["token_count"] == count_words(chunk.page_content)
    assert chunk.metadata["source_start"] == 0
    assert chunk.metadata["source_end"] == len(chunk.page_content)
    assert chunk.metadata["chunk_id"]

    processed_dir = settings.upload_dir.parent / "processed"
    cleaned_preview = processed_dir / "cleaned" / f"{chunk.metadata['document_id']}.md"
    chunk_preview = processed_dir / "chunks" / f"{chunk.metadata['document_id']}.jsonl"
    assert cleaned_preview.read_text(encoding="utf-8") == chunk.page_content
    saved_chunks = [json.loads(line) for line in chunk_preview.read_text(encoding="utf-8").splitlines()]
    assert saved_chunks == [
        {"page_content": chunk.page_content, "metadata": chunk.metadata}
    ]


def test_ingest_document_does_not_save_previews_outside_development(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(recursive_text, "count_voyage_tokens", count_words)
    monkeypatch.setattr(markdown_tables, "count_voyage_tokens", count_words)
    monkeypatch.setattr(chunking_pipeline, "count_voyage_tokens", count_words)
    settings = SimpleNamespace(
        app_env="production",
        upload_dir=tmp_path / "storage" / "uploads",
    )
    monkeypatch.setattr(ingestion_pipeline, "get_settings", lambda: settings)

    source = tmp_path / "policy.md"
    source.write_text("# Policy\n\nKeep data safe.", encoding="utf-8")

    chunks = ingest_document(
        source,
        document_id="doc-3",
        knowledge_scope="COMPANY",
        department_id=None,
        title="Policy",
        category=None,
        storage_key="COMPANY/doc-3/policy.md",
    )

    assert chunks
    assert not (settings.upload_dir.parent / "processed").exists()
