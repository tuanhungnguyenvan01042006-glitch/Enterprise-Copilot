# Current State

## Current Phase
Phase 7 - Hardening, E2E, Docker, Documentation

## Status
IMPLEMENTED / ACCEPTANCE BLOCKED

Phase 7 code, Compose wiring, E2E test definitions, and documentation are implemented. Runtime acceptance is blocked by the local environment: Docker, Docker Compose, PostgreSQL, and a usable FastAPI/Pydantic Python runtime are unavailable.

## Completed In Current Phase
- Added frontend error boundary and accessible loading/error states.
- Added responsive hardening, focus-visible states, nginx security headers, body-size limit, health endpoint, and SPA deep-link fallback.
- Added persistent upload write checks to API readiness.
- Added Compose `seed` service and `db -> migrate -> seed -> api -> web` health-gated startup flow.
- Added API/web healthchecks, deterministic frontend image install, and Docker ignore files.
- Added Playwright critical-flow definitions and documented E2E commands.
- Updated README and `.docs` architecture/setup/data-access documentation.

## Remaining Acceptance
- Run Compose from a clean environment with non-empty seed passwords.
- Apply all migrations, run idempotent seed, and exercise real login/API authorization.
- Run PostgreSQL-backed Phase 1–7 tests, restart persistence checks, upload persistence checks, and browser E2E flows.
- Verify `docker compose down` preserves named volumes and `down -v` removes them intentionally.

## Current Blockers
- `docker` and `docker compose` are not available on PATH.
- PostgreSQL server/CLI tools are unavailable.
- Local MSYS Python 3.10 cannot import the FastAPI application because Pydantic is unavailable.
- Playwright browser binaries are not installed locally; test discovery works.

## Important Files
- `compose.yaml` - health-gated migration, seed, API, web services and named volumes.
- `frontend/nginx.conf` - SPA fallback, proxy, health endpoint, and response hardening.
- `backend/app/api/routes/health.py` - database and upload-volume readiness probe.
- `frontend/src/components/AppErrorBoundary.tsx` - runtime rendering fallback.
- `frontend/e2e/critical-flows.spec.ts` - documented critical browser flows.
- `frontend/playwright.config.ts` - E2E runner configuration.
- `README.md`, `.docs/ARCHITECTURE.md`, `.docs/SETUP.md`, `.docs/DATA_ACCESS.md` - current operational docs.

## Verification
- PASS: `python -m compileall -q app tests`.
- PASS: `npm.cmd run typecheck`.
- PASS: `npm.cmd run test:run -- --reporter=dot` (7 tests).
- PASS: `npm.cmd run build`.
- PASS: `npx playwright test --config=playwright.config.ts --list` (3 tests listed).
- PASS: Vite production-preview `/` and `/app/knowledge` requests returned HTTP 200.
- NOT_RUN/BLOCKED: Docker Compose, Alembic, seed, PostgreSQL integration, restart persistence, and browser E2E execution.

## Known Issues
- Phase 1–6 PostgreSQL-backed acceptance remains incomplete.
- Login throttling remains process-local for the MVP.
- The current document model supports COMPANY and DEPARTMENT scopes, not a separate MANAGER_ONLY scope.

## Next Action
Run the commands in `README.md` and `.docs/SETUP.md` on a Docker-enabled host, then execute `npm run e2e` from `frontend/` with the seeded credentials.
