# RAG Token Estimate

Use `estimate_embedding_tokens.py` to estimate voyage-4 tokens for a Markdown
corpus:

```bash
python -m app.scripts.estimate_embedding_tokens \
  /path/to/corpus/content/handbook \
  --output storage/processed/token-estimate.json \
  --chunk-size 700 \
  --chunk-overlap 70
```

The report contains four useful totals:

- `raw_document_tokens`: tokens in the original Markdown.
- `cleaned_document_tokens`: tokens after Clean/Parse.
- `chunk_content_tokens`: tokens in chunk content before Embedding Cleaner.
- `embedding_input_tokens`: tokens actually accepted by Embedding Cleaner and
  ready for the embedding model. This is the main estimate for embedding cost.

The report also records files that fail during Chunking or Embedding Cleaner.
Those files must be fixed or intentionally excluded before treating the
embedding total as a complete-corpus number.

The existing `token-estimate.json` was produced with BGE-M3; rerun the script
to obtain a Voyage estimate. Counts do not include any API prompt or overhead.
