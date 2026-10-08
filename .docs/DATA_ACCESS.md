# Data access and authorization

PostgreSQL is the source of truth. SQLAlchemy uses one session per request and `psycopg` as the PostgreSQL driver. Schema changes are applied only through Alembic migrations.

Authenticated requests resolve the current active user from the server-side session. Role, department, account status and forced-password-change checks are performed in reusable FastAPI dependencies. Mutations require the per-session CSRF token and an exact configured Origin.

Business queries apply visibility predicates in SQL before selecting records:

- PERSONAL tasks and notes are owner-scoped.
- ASSIGNED tasks are scoped to the current assignee.
- Department tasks and documents are scoped to the current department.
- Company knowledge is readable only when published; department knowledge additionally requires department membership.
- Bookmarks return only documents the current user can still read.

Uploaded files are private, validated by extension/MIME/size, hashed with SHA-256, and addressed with server-generated keys. Download and preview endpoints repeat the document authorization check. The orphan-file command is dry-run by default.

Audit entries contain action/result/entity metadata and request IDs, but never passwords, session tokens, CSRF tokens, file contents or private note content.
