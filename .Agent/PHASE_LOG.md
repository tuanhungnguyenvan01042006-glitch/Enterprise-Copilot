# Phase Log

## Phase 0 - COMPLETED

Implemented:
- Created the required continuity files before implementation.
- Recorded the initial repository state: only `spec.md` was present.

Important files:
- `spec.md`
- `.Agent/PROJECT_MEMORY.md`
- `.Agent/STATE.md`
- `.Agent/DECISIONS.md`

Migrations:
- None.

Verification:
- Repository inspection completed.

Known limitations:
- Phase 1 implementation was not yet started at the time of this handoff.

Next phase:
Phase 1 - Foundation, Database, Seed, Minimal Login.

## Phase 1 - BLOCKED

Implemented:
- React/Vite/TypeScript frontend with a real `/login` form and authenticated landing screen.
- FastAPI app with PostgreSQL-only configuration, request IDs, structured errors, health endpoints, Argon2id password hashing, and opaque cookie sessions.
- Complete required SQLAlchemy schema and Alembic revision `0001_initial_schema`.
- Idempotent identity seed for one department, one Admin, one Manager, and six Employees.
- Docker Compose `db`, `migrate`, `api`, and `web` services with named PostgreSQL/upload volumes and only the web entry point published.

Important files:
- `compose.yaml`
- `.env.example`
- `backend/migrations/versions/0001_initial_schema.py`
- `backend/app/main.py`
- `backend/app/scripts/seed.py`
- `frontend/src/App.tsx`
- `frontend/package-lock.json`

Migrations:
- Revision created: `0001_initial_schema`.
- Not applied locally because Docker/PostgreSQL are unavailable.

Verification:
- PASS: Python compileall, SQLAlchemy metadata discovery, backend unit tests (2 passed), frontend typecheck, frontend build, frontend Vitest (1 passed), and Vite `/login` smoke request (HTTP 200).
- BLOCKED/FAIL: Docker Compose/PostgreSQL start, Alembic upgrade, seed execution, backend Uvicorn startup, and real login flow due missing Docker/PostgreSQL and incomplete local Python 3.10 runtime.

Known limitations:
- No later-phase dashboards, tasks, notes, documents, announcements, admin console, or business APIs were implemented.
- No business sample/mock data was added to the Phase 1 seed.

Next phase:
Phase 2 - Full Authentication, Authorization, App Shell, after PostgreSQL-backed Phase 1 verification is completed.

## Phase 2 - BLOCKED

Implemented:
- Database-backed principal resolution with active-account checks, current-role evaluation, forced-password-change enforcement, and reusable STAFF/Manager/Admin guards.
- Per-session CSRF endpoint and mutation checks using the CSRF header plus exact Origin validation.
- Generic login failure behavior, local MVP account/IP throttling, logout revocation, password change, all-session revocation, and profile read/update.
- Role-aware STAFF and Admin shells with required routes, Manager-only navigation, account menu, responsive layout, profile editing, and explicit placeholders for later business modules.
- Client handling for required password change, session expiry, revoked sessions, and account-switch query/CSRF cache cleanup.

Important files:
- `backend/app/core/auth.py`
- `backend/app/core/login_throttle.py`
- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/profile.py`
- `frontend/src/App.tsx`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/lib/api.ts`

Migrations:
- None. Phase 2 uses the existing `users` and `auth_sessions` schema from `0001_initial_schema`.

Verification:
- PASS: `python -m compileall -q app tests`.
- PASS: `python -m pytest -q` (5 tests).
- PASS: `npm.cmd run typecheck`.
- PASS: `npm.cmd run test:run` (5 tests).
- PASS: `npm.cmd run build`.
- BLOCKED/FAIL: FastAPI import and endpoint execution because the local MSYS Python installation lacks Pydantic.
- BLOCKED: PostgreSQL integration, migration, seed, and real multi-role auth flows because Docker/PostgreSQL are unavailable.

Known limitations:
- Login throttling is process-local and is not suitable for multiple API workers without a shared store.
- Phase 2 endpoint acceptance is not complete until real PostgreSQL-backed auth checks run.
- Phase 3+ screens are navigation placeholders only; no later-phase business feature was implemented.

Next phase:
Complete the outstanding Phase 1/2 PostgreSQL-backed acceptance checks. Do not begin Phase 3 until they pass.

## Phase 3 - BLOCKED

Implemented:
- Added SQL-scoped PERSONAL and assignee-scoped ASSIGNED task APIs with filters, status rules, revisions, completion timestamps, and soft deletion.
- Added private note CRUD/search with ownership protection and privacy-safe audit metadata.
- Added bookmark foundation APIs that filter out currently unreadable documents.
- Replaced the workspace placeholder with real task, note, and saved-document tabs; expanded the profile view.

Important files:
- `backend/app/api/routes/workspace.py`
- `backend/app/schemas/workspace.py`
- `frontend/src/features/workspace/WorkspacePage.tsx`
- `frontend/src/features/profile/ProfilePage.tsx`

Migrations:
- None. Existing `0001_initial_schema` already contains all Phase 3 tables and columns.

Verification:
- PASS: `python -m compileall -q app tests`.
- PASS: `npm.cmd run typecheck`.
- PASS: `npm.cmd run test:run -- --reporter=dot` (5 tests).
- PASS: `npm.cmd run build`.
- BLOCKED/NOT_RUN: PostgreSQL-backed API ownership/revision/restart checks because Docker/PostgreSQL and a usable FastAPI Python runtime are unavailable.

Known limitations:
- Phase 3 is implemented but not acceptance-complete until the PostgreSQL checks run.
- Document creation and knowledge-library bookmark actions remain Phase 5 scope.

Next phase:
Finish Phase 3 PostgreSQL verification, then wait for an explicit request before Phase 4.

## Phase 5 - IN_PROGRESS

Implemented:
- Added SQL-scoped document list/search/filter/detail/file APIs for Company and current-Department knowledge.
- Added Manager/Admin document creation, metadata updates, and current-file replacement with expected revisions and row locking.
- Added private staged file storage, extension/MIME/size checks, SHA-256, authenticated download, and UTF-8 MD/TXT preview.
- Partitioned private file storage by knowledge scope: `COMPANY/...` and `DEPARTMENT/{department_id}/...`.
- Added bookmark integration, knowledge library/detail UI, and orphan-file dry-run/cleanup command.
- Added `python-multipart` dependency for FastAPI multipart uploads.

Important files:
- `backend/app/api/routes/documents.py`
- `backend/app/schemas/document.py`
- `backend/app/scripts/cleanup_orphan_files.py`
- `frontend/src/features/knowledge/KnowledgePage.tsx`
- `frontend/src/features/knowledge/DocumentDetailPage.tsx`

Migrations:
- Added `0004_flatten_document_file.py` to move the latest file metadata into `documents`, remove document status, and drop `document_versions`.

Verification:
- PASS: backend `python -m compileall -q app tests`.
- PASS: frontend typecheck.
- PASS: frontend Vitest (5 tests).
- PASS: frontend production build.
- BLOCKED/NOT_RUN: PostgreSQL-backed API, restart persistence, concurrency, real multipart, and orphan cleanup acceptance because Docker/PostgreSQL are unavailable and the local Python runtime lacks Pydantic.

Next phase:
Complete PostgreSQL-backed Phase 5 acceptance before starting Phase 6.

## Phase 6 - IN_PROGRESS

Implemented:
- Added announcement list/create/edit/archive/restore APIs with Manager/Admin authorization and STAFF active-announcement visibility.
- Added STAFF and Manager dashboard API/UI with authorized task/document/announcement queries and department summaries.
- Added Admin overview API/UI with account, document, storage, readiness, and recent audit metrics.
- Added STAFF administration APIs/UI for search/filter, create, edit, role changes, lock/unlock, and secure password reset.
- Added transactional last-active-Manager protection and session revocation on role/status/password changes.
- Added read-only audit log API/UI with filters and privacy-safe action metadata.
- Added migration `0003_add_document_status.py` so Admin overview can report DRAFT/PUBLISHED/ARCHIVED document counts.

Important files:
- `backend/app/api/routes/announcements.py`
- `backend/app/api/routes/dashboard.py`
- `backend/app/api/routes/admin.py`
- `backend/app/schemas/phase6.py`
- `backend/migrations/versions/0003_add_document_status.py`
- `frontend/src/features/dashboard/DashboardPage.tsx`
- `frontend/src/features/announcements/AnnouncementsPage.tsx`
- `frontend/src/features/admin/`

Verification:
- PASS: backend Python compileall.
- PASS: frontend typecheck.
- PASS: frontend Vitest (5 tests).
- PASS: frontend production build.
- BLOCKED: backend import/API execution and PostgreSQL-backed acceptance because the local MSYS Python runtime has no compatible Pydantic wheel and Docker/PostgreSQL are unavailable.

## Phase 7 - IMPLEMENTED / ACCEPTANCE BLOCKED

Implemented:
- Added a frontend error boundary, accessible loading/error panels, focus states, and additional small-screen layout rules.
- Added nginx SPA deep-link fallback hardening, `/healthz`, upload request size limit, and baseline response security headers.
- Strengthened API readiness to verify PostgreSQL plus a write/delete probe in the persistent upload directory.
- Added Compose `seed` startup service, migration/seed/API/web dependency chain, API and web healthchecks, and preserved named database/upload volumes.
- Switched the frontend image to deterministic `npm ci` builds and added Docker ignore files.
- Added Playwright critical-flow coverage for employee persistence, manager assignment, SPA deep links, and the live health endpoint.
- Updated README and `.docs/ARCHITECTURE.md`, `.docs/SETUP.md`, and `.docs/DATA_ACCESS.md` for the Phase 7 runtime and commands.

Verification:
- PASS: backend `python -m compileall -q app tests`.
- PASS: frontend typecheck.
- PASS: frontend Vitest (7 tests).
- PASS: frontend production build.
- PASS: Playwright test discovery (3 tests listed).
- PASS: Vite production-preview root and deep-link requests returned HTTP 200.
- BLOCKED/NOT_RUN: Docker Compose config/startup, PostgreSQL migrations/seed, restart-volume persistence, and browser E2E execution because Docker/PostgreSQL and browser runtime are unavailable in this environment.

Known limitations:
- Existing Phase 1–6 PostgreSQL-backed acceptance remains outstanding.
- The current knowledge model supports COMPANY and DEPARTMENT scopes; the specification's MANAGER_ONLY example is not represented in this schema.

Next phase:
No next implementation phase. Run the documented Docker/PostgreSQL acceptance and E2E suite in an environment with Docker Desktop.
