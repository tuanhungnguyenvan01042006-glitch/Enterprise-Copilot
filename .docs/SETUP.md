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

This preserves both named volumes. To intentionally remove the local database and uploaded files:

```powershell
docker compose down -v
```

After a reset, run `docker compose up --build` again with the seed passwords set.

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
