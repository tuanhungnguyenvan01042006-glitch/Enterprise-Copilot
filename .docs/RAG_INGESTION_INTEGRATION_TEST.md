# RAG Ingestion Integration Test

The integration test covers the pipeline up to Chunking:

`Load → Clean/Parse → Chunking`

It uses `backend/tests/fixtures/rag/handbook_sample.md`, which contains front
matter, HTML, shortcode content, a Markdown table, Mermaid, a code block, and a
long text section.

## Run the test

From `backend`:

```bash
pytest tests/integration/test_ingestion_pipeline.py -q
```

The test uses a deterministic word counter so it does not need to download the
Voyage tokenizer. It still executes the real loader, cleaner/parser, ingestion
pipeline, and chunking modules.

## Inspect output manually

From `backend`:

```bash
python -m app.scripts.inspect_ingestion \
  tests/fixtures/rag/handbook_sample.md \
  --output-dir storage/processed/integration/handbook_sample \
  --chunk-size 40 \
  --chunk-overlap 8
```

The output directory contains:

- `source.md`: original input.
- `cleaned.md`: result after Clean/Parse.
- `chunks.jsonl`: chunks with their metadata.
- `report.json`: chunk count, block types, and token range.

The script uses the real Voyage tokenizer. Use the Docker backend image if the
host Python environment does not have the project dependencies installed.
