# Decisions

## 2026-09-16 — Keep Phase 1 limited to foundation and identity login

Decision:
Implement the schema needed by the full specification and the minimum real login/health surface, but do not expose later-phase business modules or add mock business data to the frontend.

Reason:
The requested phase is explicitly Foundation, Database, Seed, Minimal Login. The specification requires the identity seed now, while later business features must not appear functional through mocks.

Affected files:
- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/health.py`
- `backend/app/scripts/seed.py`
- `frontend/src/App.tsx`

## 2026-09-16 — Use synchronous SQLAlchemy with psycopg

Decision:
Use SQLAlchemy 2.x synchronous sessions with the `psycopg` PostgreSQL driver.

Reason:
This keeps the Phase 1 request/session and migration foundation small while still using PostgreSQL and one database session per request as required by the specification.

Affected files:
- `backend/app/db/session.py`
- `backend/requirements.txt`
- `backend/alembic/env.py`

## 2026-09-16 - Keep Compose private services private

Decision:
Compose publishes only the nginx web entry point on port 8080. The API and PostgreSQL remain internal services; Vite proxies `/api` during direct frontend development.

Reason:
This follows the specification's default deployment rule and keeps the database and backend off the host-facing surface.

Affected files:
- `compose.yaml`
- `frontend/nginx.conf`
- `frontend/vite.config.ts`

## 2026-09-17 - Resolve identity and authorization from the database per request

Decision:
Centralize current-session resolution, forced-password-change enforcement, and STAFF/Manager/Admin guards in FastAPI dependencies. Each request loads the current active user instead of trusting role data captured at login.

Reason:
Locks and role changes must take effect immediately, authorization must happen before data exposure, and future business routers need one consistent policy boundary.

Affected files:
- `backend/app/core/auth.py`
- `backend/app/api/routes/profile.py`

## 2026-09-17 - Require session CSRF token and exact Origin on authenticated mutations

Decision:
Fetch the per-session CSRF token on demand, keep it only in frontend memory, and require both that token and an exact configured Origin for logout, password change, profile mutation, and future authenticated writes.

Reason:
This follows the specification without exposing auth credentials in browser storage or allowing wildcard credentialed origins.

Affected files:
- `backend/app/core/auth.py`
- `frontend/src/lib/api.ts`

## 2026-09-17 - Establish later routes as honest shell placeholders

Decision:
Create the complete role-aware route tree and navigation in Phase 2, but render explicit not-yet-implemented empty states for Phase 3+ business modules.

Reason:
Deep links, role guards, and the shell can be verified now without fabricating business behavior or starting a later phase.

Affected files:
- `frontend/src/App.tsx`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/PlaceholderPage.tsx`

## 2026-09-22 - Keep Phase 3 on the existing schema and scope privacy in SQL

Decision:
Reuse the Phase 1 `tasks`, `notes`, and `document_bookmarks` tables without a migration. The `/me` workspace queries include the current STAFF owner/assignee and department predicates before selecting data; inaccessible records return `404`.

Reason:
The schema already contains the required revision, soft-delete, completion, and bookmark columns. Reusing it avoids unnecessary migrations and keeps private data out of application-side filtering.

Affected files:
- `backend/app/api/routes/workspace.py`
- `backend/app/schemas/workspace.py`
- `frontend/src/features/workspace/WorkspacePage.tsx`

## 2026-09-22 - Keep bookmark foundation readable before document management exists

Decision:
Expose bookmark list/add/remove now, but return only published documents that the current STAFF role can read. Document creation, publishing, and bookmark buttons in the knowledge library remain Phase 5 work.

Reason:
Phase 3 requires the saved-document tab/API foundation without starting the document-management phase or leaking restricted document metadata.

Affected files:
- `backend/app/api/routes/workspace.py`
- `frontend/src/features/workspace/WorkspacePage.tsx`

## 2026-09-22 - Reuse the task schema for the Department Workspace

Decision:
Implement Phase 4 with Manager-only `/department` routes over the existing `tasks` and `users` tables. Department task queries constrain `department_id`, `kind = ASSIGNED`, and non-deleted rows in SQL; task responses join minimal assignee/creator work identity DTOs.

Reason:
The Phase 1 schema already contains the fields needed for assignment, completion, reassignment, soft-delete exclusion, and optimistic revisions. Reusing it avoids a migration and keeps department data out of `/me` privacy scopes.

## 2026-09-23 - Implement Phase 5 over the existing document schema

Reuse the Phase 4 document scope model and existing version/bookmark tables. Store bytes only in the private upload volume with server-generated keys, and use a row lock plus document revision for safe version numbering. This keeps file metadata transactional while making filesystem cleanup explicit through a dry-run orphan command.

Affected files:
- `backend/app/api/routes/department.py`
- `backend/app/schemas/workspace.py`
- `frontend/src/features/team/TeamPage.tsx`

## 2026-09-23 - Use one scoped Document model for RAG knowledge

Decision:
Keep one `documents` table and add `knowledge_scope` with `COMPANY` and `DEPARTMENT`. Company documents have no `department_id`; department documents require one. Remove `status`, `visibility`, `tags`, and `effective_from` because the MVP treats uploaded documents as published and derives access from scope and department.

Reason:
Company and department documents share file versions, storage, bookmarks, metadata, and RAG indexing. One model avoids duplicated lifecycle and authorization code while the database constraint prevents invalid scope/department combinations.

Affected files:
- `backend/app/models/document.py`
- `backend/app/api/routes/workspace.py`
- `backend/migrations/versions/0002_simplify_document_scope.py`
- `spec.md`

## 2026-09-26 - Gate Compose startup on migration, seed, and health

Decision:
Use separate one-shot `migrate` and idempotent `seed` services, then require the API readiness check before starting nginx. Readiness checks PostgreSQL and performs a temporary write/delete probe in the upload volume.

Reason:
A clean environment must have schema, identity data, database connectivity, and persistent file storage ready before users can reach the application. Named volumes remain independent of container restarts.

Affected files:
- `compose.yaml`
- `backend/app/api/routes/health.py`
- `frontend/nginx.conf`

## 2026-09-26 - Keep browser E2E opt-in and environment-driven

Decision:
Keep Playwright flows in the frontend workspace and run them against an already-started Compose stack using `E2E_BASE_URL` and seeded credential variables.

Reason:
The E2E suite should exercise the deployed web/API boundary without silently creating or deleting user data or taking over the developer's Docker lifecycle.

Affected files:
- `frontend/playwright.config.ts`
- `frontend/e2e/critical-flows.spec.ts`
- `frontend/package.json`
