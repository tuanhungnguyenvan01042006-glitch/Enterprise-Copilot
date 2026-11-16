# Embedding Module — Phase 0 Contract

Phase 0 deliberately keeps the contract small. It validates chunk structure
and defines the objects passed between the future embedding stages.

## Input

The module receives a LangChain `Document` produced by Chunking.

Required `Document.metadata` fields:

- `document_id`: non-empty string
- `chunk_id`: non-empty string
- `chunk_index`: integer `>= 0`
- `block_type`: `text`, `table`, `code`, or `mermaid`
- `token_count`: integer `>= 1`
- `section_path`: string; it may be empty
- `source_start`: integer `>= 0`
- `source_end`: integer greater than `source_start`
- `knowledge_scope`: `COMPANY` or `DEPARTMENT`
- `department_id`: null for `COMPANY`, positive integer for `DEPARTMENT`
- `title`: non-empty string
- `category`: non-empty string or null

`page_content` must be a non-empty string.

`storage_key` may remain in internal chunk metadata because it belongs to
private document storage, but it is not copied into the embedding output.

## Output before model encoding

`EmbeddingItem` contains:

- `point_id`: the input `chunk_id`
- `text`: the chunk content after the minimal embedding cleanup
- `metadata`: the approved metadata fields only

The embedding cleaner removes dynamic-content placeholders, Markdown image
syntax, and Markdown link syntax from text and table chunks, including link syntax inside
inline code. It keeps useful image alt text and inline-code payloads, converts
template expressions to readable text, and removes presentation-only Markdown
formatting and icons from text and table chunks. Table rows and column delimiters
are retained; code and Mermaid blocks remain unchanged.
Only the new `EmbeddingItem.text` used for model input is cleaned; the source
`Document.page_content` and input item are not modified. The cleaner preserves
the same `point_id` and metadata.

`prepare_chunks` runs validation and cleaning for a sequence of chunks. It
returns prepared items paired with their original text, plus a list of errors
containing the input index, available document/chunk IDs, and validation reason.
Invalid chunks and chunks empty after cleaning are skipped and reported;
unexpected errors are propagated. No embedding model is called at this stage.

## Output after model encoding

`EmbeddedPoint` contains:

- `point_id`
- `vector`: a non-empty list of finite numbers
- `text`: original chunk `page_content` for retrieval/display, including icons
- `metadata`

The vector is generated from the cleaned `EmbeddingItem.text`. The
`EmbeddedPoint.text` comes from the original chunk, not the cleaned model input.

`voyage_langchain.embed_chunks` sends cleaned chunks to `voyage-4` in bounded batches and
returns points and preparation errors. Each chunk is embedded independently;
batching does not add the context of other chunks. `embed_query` uses
`voyage-4-lite`. Both request 1,024-dimensional float vectors, and truncation
is disabled to avoid silently losing text.

`app.RAG.pipeline.ingest_and_embed_document` connects ingestion, chunking and
embedding. It returns the points and errors to its caller. The upload background
task then stores valid points in Qdrant and logs skipped chunks. If a file was
replaced while its task ran, the outdated task does not write points.
Set `VOYAGE_API_KEY` in the process environment
(or `.env` for Docker Compose) before calling the Voyage API.

```python
from app.RAG.pipeline import ingest_and_embed_document
from app.RAG.Embedding.voyage_langchain import embed_query

points, errors = ingest_and_embed_document(
    "policy.md", document_id="doc-1", knowledge_scope="COMPANY",
    department_id=None, title="Policy", category=None,
    storage_key="COMPANY/doc-1/policy.md",
)
query_vector = embed_query("What is the policy?")
```

Voyage confirms that `voyage-4` and `voyage-4-lite` share an embedding space.
Evaluate retrieval on the project's documents and queries before production.

Qdrant storage belongs to the RAG pipeline and vector store, outside this
Embedding module. Model versioning, content hashing, chunk classification and
special handling by document type are not included here.
