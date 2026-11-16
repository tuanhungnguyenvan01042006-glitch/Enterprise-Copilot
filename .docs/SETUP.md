# Setup and operations

## First run

```powershell
Copy-Item .env.example .env
# Set all three SEED_*_PASSWORD values in .env.
docker compose up --build
```

Open `http://localhost:8080`. The seed command is safe to run again and does not overwrite existing accounts.

## Verify the stack

```powershell
docker compose ps
Invoke-WebRequest http://localhost:8080/healthz
Invoke-WebRequest http://localhost:8080/api/v1/health/live
docker compose logs --tail=100 migrate seed api
```

`/api/v1/health/ready` is the API readiness check. It verifies a database query and a temporary write/delete probe in `UPLOAD_DIR`.

## Stop and reset

```powershell
docker compose down
```

This preserves the PostgreSQL, upload and Qdrant named volumes. To intentionally remove their data:

```powershell
docker compose down -v
```

After a reset, run `docker compose up --build` again with the seed passwords set.

## RAG vector storage

Compose runs Qdrant on `qdrant:6333` for the backend and exposes port 6333 on
localhost for development. The backend uses `VOYAGE_API_KEY`, `QDRANT_URL`,
and `QDRANT_COLLECTION`; see `.env.example`. The collection is created on the
first successful indexing attempt, with 1,024-dimensional cosine vectors.
For Python running outside Docker, use `QDRANT_URL=http://localhost:6333`.

Uploading a Markdown file starts ingestion, embedding and Qdrant indexing in a
background task after the upload commits. The response confirms the upload,
not the indexing outcome; backend logs contain failures and skipped chunks.
On successful reindex, obsolete chunks for that document are deleted after
the new points are written. Uploading a file remains successful if a later
background task fails. The bulk handbook importer does not trigger indexing.

To index existing documents, including imported handbook files, first rebuild
the API image, then run the indexing script. Start with a small batch:

```powershell
docker compose build api
docker compose up -d db qdrant
docker compose run --rm --no-deps api python -m app.scripts.index_documents --limit 3
```

Use `--offset 3 --limit 3` for the next batch, or omit both options to index
all stored documents. Rerunning a batch embeds its documents again and uses
Voyage API calls. The script reports each failure and returns a nonzero exit
code if any document failed. If a document changes during indexing, retry it.

Search the indexed collection for a manual retrieval check:

```powershell
docker compose run --rm --no-deps api python -m app.scripts.retrieve_chunks "How do I ask a question?" --top-k 5
```

This command is for internal evaluation only: it does not enforce document
permissions or filter stale metadata. Do not expose it to application users.

## Direct development

Use Python 3.12+, Node.js 20+, and a reachable PostgreSQL instance. Set `DATABASE_URL`, `MIGRATION_DATABASE_URL`, `UPLOAD_DIR`, and the seed variables before running:

```powershell
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

## E2E

Install a browser once with `npx playwright install chromium`, set the seeded employee and manager passwords, and run `npm run e2e` from `frontend/`. Use `E2E_BASE_URL` for a non-default web URL.
