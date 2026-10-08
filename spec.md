# Enterprise Copilot — Web Application Build Specification

**Purpose:** Source of truth for an AI coding agent building the web application.  
**Scope:** Frontend, backend, PostgreSQL database, file storage, authentication, authorization, tests, and local deployment.  
**UI language:** Vietnamese.  
**Code, API, database, file names, and technical documentation:** English.  
**Organization model:** Exactly one department.  
**Business roles:** `EMPLOYEE`, `MANAGER`.  
**System administrator:** `ADMIN`.

---

# 1. Core Goal

Build a real internal web application for one department.

The application must support:

- Authentication and account lifecycle.
- Role-based and ownership-based authorization.
- Personal tasks and private notes.
- Manager-assigned tasks.
- A versioned document library.
- Bookmarks.
- Internal announcements.
- Employee/Manager dashboards.
- A separate Admin Console.
- PostgreSQL persistence.
- Private file storage.
- Docker-based local deployment.
- Automated tests for critical flows and permissions.

All business data shown in the frontend must come from the backend API.

Do not replace unfinished backend functionality with frontend mock data.

---

# 2. Product Scope

## 2.1 Department

The system contains exactly one department:

```text
code: OPERATIONS
name: Phòng Vận hành
```

Do not build:

- Department creation.
- Department deletion.
- Department switching.
- Organization charts.
- Multi-company support.
- Multi-tenant support.

## 2.2 Account Model

```text
Account
├── STAFF
│   ├── EMPLOYEE
│   └── MANAGER
└── ADMIN
```

Rules:

- `EMPLOYEE` and `MANAGER` are department roles.
- `ADMIN` is a system account type, not a department role.
- Admin accounts do not belong to the department.
- The application bootstraps one Admin account.
- The Admin UI manages STAFF accounts only.
- The Admin UI must not create additional Admin accounts.

## 2.3 Explicitly Out of Scope

Do not add features that are not required by this specification.

Examples of out-of-scope modules:

- Payroll.
- Attendance.
- Leave management.
- Recruiting.
- CRM.
- Customers/orders/invoices.
- Support tickets.
- Internal chat.
- Email integration.
- Calendar integration.
- Real-time notifications.
- WebSocket features.
- Mobile applications.
- Microservices.
- Kubernetes.
- Message queues.
- Custom role builders.

---

# 3. Technology Stack

Use the following stack unless the existing repository already contains a compatible equivalent that should be preserved.

## Frontend

```text
React
TypeScript
Vite
React Router
TanStack Query
React Hook Form
Zod
Tailwind CSS
```

## Backend

```text
Python 3.12
FastAPI
Pydantic
SQLAlchemy 2.x
Alembic
```

## Data

```text
PostgreSQL 17
Private filesystem storage for uploaded files
```

## Authentication

```text
Server-side opaque sessions
HttpOnly cookies
Argon2id password hashing
CSRF protection for mutations
```

Do not use JWT for this MVP.

## Testing

```text
Backend: pytest
Frontend: Vitest + Testing Library
End-to-end: Playwright
```

## Local Deployment

```text
Docker Compose
```

Choose compatible package versions, commit lockfiles, and document the versions actually used.

---

# 4. Required Repository Structure

The exact file names may vary slightly, but keep clear boundaries between API, services, policies, persistence, and storage.

```text
enterprise-copilot/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── dashboard/
│   │   │   ├── workspace/
│   │   │   ├── department/
│   │   │   ├── knowledge/
│   │   │   ├── announcements/
│   │   │   └── admin/
│   │   ├── lib/
│   │   └── types/
│   └── tests/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── policies/
│   │   ├── storage/
│   │   └── scripts/
│   ├── migrations/
│   └── tests/
│
├── .Agent/
│   ├── PROJECT_MEMORY.md
│   ├── STATE.md
│   ├── DECISIONS.md
│   └── PHASE_LOG.md
│
├── .docs/
│   ├── ARCHITECTURE.md
│   ├── SETUP.md
│   └── DATA_ACCESS.md
│
├── compose.yaml
├── .env.example
├── .gitignore
└── README.md
```

Do not create unnecessary abstraction layers or placeholder modules that have no current use.

---

# 5. Agent Continuity Protocol

The `.Agent` directory is mandatory.

Its purpose is to let a future coding session continue from the previous phase without re-reading the entire source tree.

## 5.1 `.Agent/PROJECT_MEMORY.md`

Contains only stable project knowledge.

Examples:

- Final stack.
- Repository structure.
- Database conventions.
- Authentication approach.
- Authorization principles.
- Important service boundaries.
- Commands that are known to work.
- Stable environment requirements.

Do not store temporary progress here.

Keep this file concise. Prefer facts and short bullet points.

## 5.2 `.Agent/STATE.md`

This is the most important continuity file.

It must always describe the current implementation state.

Required format:

```md
# Current State

## Current Phase
Phase X — Name

## Status
NOT_STARTED | IN_PROGRESS | BLOCKED | COMPLETED

## Last Completed Phase
Phase X

## Completed In Current Phase
- ...

## Remaining In Current Phase
- ...

## Current Blockers
- None

## Important Files
- path/to/file — why it matters

## Database State
- latest migration:
- seed status:
- known schema notes:

## Verification
- command — PASS/FAIL/NOT_RUN

## Known Issues
- ...

## Next Action
1. ...
2. ...

## Files To Inspect Next
- ...
```

Rules:

- Update this file whenever meaningful progress changes.
- Update it before ending a coding session.
- Do not claim a test passed unless it was actually executed.
- Keep it operational and short.

## 5.3 `.Agent/DECISIONS.md`

Record implementation decisions that are not obvious from the specification.

Format:

```md
## YYYY-MM-DD — Decision title

Decision:
...

Reason:
...

Affected files:
- ...
```

Only record decisions that future agents need to know.

Do not turn this into a daily diary.

## 5.4 `.Agent/PHASE_LOG.md`

Append one short handoff entry after each completed phase.

Format:

```md
## Phase X — COMPLETED

Implemented:
- ...

Important files:
- ...

Migrations:
- ...

Verification:
- ...

Known limitations:
- ...

Next phase:
Phase X+1 — ...
```

## 5.5 Start-of-Session Rule

When continuing an existing repository, the agent must use this order:

1. Read `.Agent/STATE.md`.
2. Read `.Agent/PROJECT_MEMORY.md`.
3. Read only the current phase section of this specification.
4. Read `.Agent/DECISIONS.md` only if relevant.
5. Inspect the files listed under `Files To Inspect Next`.
6. Inspect additional source files only when required to complete the current task.

Do **not** re-read or re-index the entire repository by default.

A full repository review is allowed only when:

- `.Agent/STATE.md` is missing or clearly stale.
- The repository state conflicts with the recorded state.
- A cross-cutting refactor requires it.
- The user explicitly requests it.

## 5.6 End-of-Phase Rule

Before declaring a phase complete:

1. Run the phase verification commands.
2. Fix failures that belong to the phase.
3. Update `.Agent/STATE.md`.
4. Update `.Agent/PROJECT_MEMORY.md` only if stable project knowledge changed.
5. Record new technical decisions in `.Agent/DECISIONS.md`.
6. Append the phase summary to `.Agent/PHASE_LOG.md`.
7. Stop.

Do not automatically start the next phase.

---

# 6. Authorization Model

Authorization must be enforced by the backend on every request.

Frontend route guards and hidden buttons are for user experience only.

For inaccessible records:

- Return `404` when revealing that the record exists would leak information.
- Return `403` when the user is authenticated but the entire function is unavailable to their role.

## 6.1 Employee

Employee can:

- View own dashboard.
- Create and manage own PERSONAL tasks.
- View ASSIGNED tasks assigned to them.
- Update allowed status fields on their ASSIGNED tasks.
- Create, edit, and delete own private notes.
- View and download allowed published documents.
- Bookmark allowed documents.
- Read active announcements.
- Edit own display name.
- Change own password.

Employee cannot:

- Read another user's private notes.
- Read another user's PERSONAL tasks.
- Read another user's bookmarks.
- Access Manager pages.
- Access Admin pages.
- See restricted document metadata.

## 6.2 Manager

Manager has all Employee personal capabilities plus:

- View the minimal department member list.
- Create ASSIGNED tasks for active Employees.
- View and manage all ASSIGNED tasks in the department.
- Reassign ASSIGNED tasks.
- Create and manage documents.
- Manage restricted documents.
- Create/edit/archive announcements.

Manager cannot:

- Read Employees' private notes.
- Read Employees' PERSONAL tasks.
- Read Employees' bookmarks.
- Manage passwords or roles.

Multiple Managers may exist.

All Managers have the same department-level ASSIGNED-task scope.

## 6.3 Admin

Admin can:

- View Admin dashboard.
- Create STAFF accounts.
- Edit STAFF work information.
- Change Employee ↔ Manager role.
- Lock/unlock STAFF accounts.
- Reset STAFF passwords.
- Manage all documents.
- Manage announcements.
- View audit logs.

Admin cannot:

- Use Personal Workspace.
- Read STAFF private notes.
- Read STAFF PERSONAL tasks.
- Participate in task assignment.

## 6.4 Permission Matrix

| Resource / Action | Employee | Manager | Admin |
|---|---|---|---|
| Personal dashboard | Own | Own | No |
| Admin dashboard | No | No | Yes |
| PERSONAL tasks | Own | Own | No |
| ASSIGNED tasks | Assigned to self | All department ASSIGNED | No |
| Private notes | Own | Own | No |
| Bookmarks | Own | Own | No |
| Published DEPARTMENT documents | Read | Read/manage | Read/manage |
| MANAGER_ONLY documents | No | Read/manage | Read/manage |
| Draft/archived documents | No | Manage | Manage |
| Create document/version | No | Yes | Yes |
| Department member page | No | Yes | Via user admin |
| Manage announcements | No | Yes | Yes |
| Manage STAFF accounts | No | No | Yes |
| Audit logs | No | No | Yes |

---

# 7. Routes and UI Structure

## 7.1 Routes

```text
/login
/change-password

/app
/app/dashboard
/app/workspace
/app/knowledge
/app/knowledge/:documentId
/app/profile
/app/team

/admin
/admin/overview
/admin/users
/admin/documents
/admin/documents/:documentId
/admin/announcements
/admin/audit-logs
/admin/profile
```

Rules:

- `/app/team` is Manager-only.
- `/admin/*` is Admin-only.
- Personal Workspace is STAFF-only.
- Deep URL refresh must work.

## 7.2 Sidebar

### Employee

```text
Tổng quan
Không gian cá nhân
Kho kiến thức
```

### Manager

```text
Tổng quan
Không gian cá nhân
Kho kiến thức
Quản lý phòng ban
```

### Admin

```text
Tổng quan quản trị
Tài khoản
Tài liệu
Thông báo
Nhật ký hệ thống
```

Profile and logout belong in the account menu.

## 7.3 Visual Direction

Use a clean internal SaaS dashboard style:

- Light background.
- White cards/surfaces.
- Dark blue or teal accent.
- Vietnamese-compatible typography.
- Consistent 4/8 px spacing.
- One icon set.
- Status badges must include text, not color only.
- Prefer tables, lists, forms, drawers, and modals.
- Avoid heavy gradients and decorative animation.
- Dark mode is not required.

## 7.4 Required UI States

Data screens must handle:

```text
Loading
Empty
Success
Validation error
Unauthorized/session expired
Forbidden/resource unavailable
Server error
```

Forms must refresh visible data after successful writes.

Require confirmation before destructive or security-sensitive actions.

---

# 8. Dashboard

## 8.1 Employee Dashboard

Header:

```text
Xin chào, [Full Name]
Phòng Vận hành · Employee
```

Stats:

- Open tasks: own tasks with `TODO` or `IN_PROGRESS`.
- Overdue tasks: own unfinished tasks with `due_date` before today.
- Open assigned tasks: own `ASSIGNED` tasks with `TODO` or `IN_PROGRESS`.
- Saved documents: bookmarks that still point to readable documents.

Content:

- Up to 5 priority tasks: overdue first, then nearest due date.
- 3 latest active announcements.
- Up to 5 recently updated readable documents.

Quick actions:

- Create personal task.
- Create note.
- Open document library.

## 8.2 Manager Dashboard

Includes Employee personal dashboard plus department summary:

- Active Employee count.
- Open ASSIGNED-task count.
- Overdue ASSIGNED-task count.
- Link to Department Workspace.
- Create announcement action.

Department statistics must never include Employees' PERSONAL tasks.

## 8.3 Admin Dashboard

Show:

- Active STAFF count.
- Employee count.
- Manager count.
- Locked account count.
- Total document file count.
- Total stored file bytes.
- 5 latest audit events.
- API/database/storage readiness.

Do not show private task/note content or private-data statistics.

---

# 9. Personal Workspace

STAFF-only.

Tabs:

```text
Tasks
Notes
Saved Documents
```

## 9.1 Tasks

Task fields:

| Field | Rule |
|---|---|
| `title` | required, 1–160 chars after trim |
| `description` | optional, max 4000 chars, plain text |
| `status` | TODO, IN_PROGRESS, DONE, CANCELLED |
| `priority` | LOW, NORMAL, HIGH; default NORMAL |
| `due_date` | optional DATE |
| `kind` | PERSONAL or ASSIGNED; backend-controlled |
| `assignee_id` | backend-controlled where required |
| `created_by` | current authenticated user |
| `revision` | optimistic concurrency integer |

Filters:

- kind
- status
- priority
- title search

Default sort:

1. nearest due date
2. tasks without a due date last

### PERSONAL Tasks

Rules:

- User creates the task for self only.
- Owner may edit title, description, priority, due date, and status.
- Owner may transition between all four statuses.
- Owner may delete the task.
- Deletion is soft delete.
- Other users, Managers, and Admin cannot read it.

### ASSIGNED Tasks

Rules:

- Only Manager creates them.
- Assignee must be an active Employee.
- Employee cannot change title, description, priority, due date, or assignee.
- Employee may transition:
  - `TODO -> IN_PROGRESS`
  - `IN_PROGRESS -> TODO`
  - `TODO -> DONE`
  - `IN_PROGRESS -> DONE`
- Employee cannot set `CANCELLED`.
- Employee cannot reopen `DONE` or `CANCELLED`.
- Manager may edit content, due date, priority, assignee, and status.
- Manager may cancel or reopen.
- ASSIGNED tasks are not permanently deleted.

When status becomes `DONE`, set `completed_at`.

When leaving `DONE`, clear `completed_at`.

## 9.2 Private Notes

Fields:

```text
title: 1–160 chars
content: max 20,000 chars
revision
created_at
updated_at
```

Features:

- Create.
- Edit.
- Delete.
- Search by title.
- Optional SQL text search within the current owner's notes.
- Manual save.
- No autosave required.
- Plain text only.

Notes are always private.

Audit may record note action metadata but never note title/content.

## 9.3 Saved Documents

Show bookmarked documents that the current user is still allowed to read.

Display:

- title
- category
- updated time
- remove bookmark action

Bookmark records may remain in the database when access is lost, but the API must not return hidden document metadata.

## 9.4 Profile

Display:

- Full name.
- Work email.
- Employee code.
- Job title.
- Department.
- Role.
- Account creation date.

User may edit:

- `full_name`
- password

Admin controls:

- email
- employee code
- job title
- role

---

# 10. Department Workspace

Manager-only route:

```text
/app/team
```

Tabs:

```text
Department Tasks
Members
```

## 10.1 Department Tasks

Only show `ASSIGNED` tasks.

Columns:

- title
- assignee
- creator
- status
- priority
- due date
- overdue flag

Filters:

- assignee
- status
- priority
- overdue

Manager actions:

- Create task for active Employee.
- Edit task content.
- Edit due date.
- Edit priority.
- Reassign to another active Employee.
- Change status.
- Cancel.
- Reopen.

After reassignment:

- Previous assignee loses access on the next request.
- New assignee gains access.

Historical tasks remain when an Employee is locked or changes role.

## 10.2 Members

Show only:

```text
Full name
Work email
Employee code
Job title
Role
Active status
```

Do not expose:

- Private notes.
- PERSONAL tasks.
- Password management.
- Role management.

---

# 11. Document Library

This module stores and serves internal documents.

## 11.1 Accepted Files

Only:

```text
.pdf
.md
.txt
```

Default maximum:

```text
10 MiB per file
```

Make the size configurable.

Reject unsupported formats.

TXT/MD must be valid UTF-8 for preview.

## 11.2 Document Metadata

| Field | Rule |
|---|---|
| `title` | required, 1–200 chars |
| `description` | optional, max 2000 chars |
| `category` | POLICY, SOP, GUIDE, REFERENCE |
| `knowledge_scope` | COMPANY, DEPARTMENT |
| `language` | vi, en, other |
| `department_id` | nullable; required for DEPARTMENT, null for COMPANY |
| `created_by` | server-controlled |
| `updated_by` | server-controlled |
| `revision` | optimistic concurrency |
| timestamps | UTC |

## 11.3 Knowledge Scope

### COMPANY

- All STAFF may read.
- Admin may manage.

### DEPARTMENT

- STAFF may read documents belonging to their own department.
- Manager of the department and Admin may manage.
- Other departments must not see:
  - title
  - metadata
  - count
  - search result
  - file

## 11.4 Lifecycle

New document:

```text
Available to authorized readers + current file
```

All uploaded documents are immediately available to authorized readers. No document status lifecycle is required for the MVP.

No permanent document/version deletion through the MVP UI.

## 11.5 Current Document File

Each document has one current file. Uploading a new file replaces the current
file and updates its metadata; historical file versions are not retained by
the MVP.

Rules:

- File bytes remain in private storage, not in PostgreSQL.
- `storage_key` is generated by the server and is never exposed to clients.
- File replacement requires `expected_revision`.
- File permissions follow the document's current knowledge scope.

## 11.6 Document List

Employee:

- Search title/description.
- Filter category/language.
- See `COMPANY` documents and `DEPARTMENT` documents from the current department.
- View detail.
- Download.
- Bookmark.

Manager:

- All Employee capabilities.
- Filter knowledge scope.
- Upload document.
- Edit metadata.
- Replace the current file.

Admin uses the same document business logic from Admin Console.

## 11.7 Detail Page

Display:

- title
- description
- category
- language
- knowledge scope
- creator/updater
- updated date
- current file metadata
- download action
- bookmark action for STAFF
- management actions when authorized

## 11.8 Preview and Download

- PDF: authenticated download is sufficient.
- MD/TXT: plain-text preview may be provided.
- Preview may be limited to 100 KiB.
- Never execute uploaded content as HTML.
- Preview/download must re-check authorization.
- Verify the requested document is readable before serving its current file.
- Never expose `storage_key` or absolute file paths.
- Downloads should use `Content-Disposition: attachment`.
- Add `X-Content-Type-Options: nosniff`.

## 11.9 Document Concurrency

Metadata updates and file replacements require `expected_revision`.

If revision is stale:

```text
409 REVISION_CONFLICT
```

The frontend must ask the user to reload current data.

---

# 12. Announcements

Fields:

```text
title: 1–160 chars
body: 1–6000 chars, plain text
department_id
created_by
updated_by
revision
created_at
updated_at
archived_at: nullable
```

Rules:

- Manager/Admin create.
- Manager/Admin edit.
- Manager/Admin archive/restore.
- STAFF read active announcements.
- No comments.
- No reactions.
- No read receipts.
- No scheduling.
- No email/push delivery.

---

# 13. Admin Console

## 13.1 STAFF Management

List:

```text
Full name
Email
Employee code
Job title
Role
Status
Created date
```

Filters:

- role
- active status

Search:

- full name
- email
- employee code

Actions:

- Create STAFF account.
- Edit work information.
- Change Employee ↔ Manager.
- Lock/unlock.
- Reset password.

Rules:

- No permanent account deletion through UI.
- Locking does not delete historical data.
- Admin cannot convert STAFF to ADMIN.
- Admin cannot lock or change its own account type.
- Always keep at least one active Manager.
- Attempting to lock/demote the last active Manager returns:
  - `409 LAST_ACTIVE_MANAGER`

Role/status changes must revoke the affected user's sessions.

## 13.2 Password Reset

Admin must re-enter their own password.

Backend generates a random temporary password.

Rules:

- Return temporary password once.
- Never log it.
- Never store plaintext.
- Set `must_change_password = true`.
- Revoke all previous sessions for the target user.

No public forgot-password flow is required.

## 13.3 Audit Logs

Display:

```text
timestamp
actor
action
entity type
entity id
result
request id
```

Filters:

- time
- actor
- action
- result

Audit logs are read-only.

Never store:

- plaintext passwords
- session tokens
- CSRF tokens
- private note content
- private task content
- entire request bodies

---

# 14. Authentication and Session Rules

## 14.1 Login

- No public registration.
- Login form uses email + password.
- No social login.
- No role selector.
- Failed login message must not reveal whether the email exists.

## 14.2 Session

Use opaque server-side sessions.

Rules:

1. Hash passwords with Argon2id.
2. Generate random session token using a cryptographically secure RNG.
3. Use at least 256 bits of token entropy.
4. Store SHA-256 hash of the session token in the database.
5. Store the original token only in an HttpOnly cookie.
6. Cookie:
   - `HttpOnly`
   - `SameSite=Lax`
   - `Path=/`
   - no Domain
7. Enable `Secure` in HTTPS/production.
8. Session absolute lifetime: 8 hours, configurable.
9. Backend checks current user active status and current role on requests.
10. Logout revokes the current session.
11. Password change revokes all sessions.
12. Never store auth credentials in localStorage/sessionStorage.

## 14.3 CSRF

Each authenticated session has its own CSRF token.

Endpoint:

```text
GET /api/v1/auth/csrf
```

Frontend sends:

```text
X-CSRF-Token
```

on:

```text
POST
PUT
PATCH
DELETE
```

Backend must:

- Validate token against the current session.
- Validate Origin against allowlist.
- Never log CSRF token.
- Avoid wildcard CORS with credentials.

## 14.4 Password Change

New password:

```text
12–128 characters
```

Require current password.

When `must_change_password = true`, user may access only:

- current identity
- CSRF endpoint
- change password
- logout

Other business APIs return:

```text
403 PASSWORD_CHANGE_REQUIRED
```

After successful change:

- clear flag
- revoke sessions
- return user to login

## 14.5 Login Throttling

For the MVP, implement simple login throttling.

Suggested limits:

```text
5 failed attempts/minute/account
20 failed attempts/minute/IP
```

Return `429` when exceeded.

A single-process in-memory limiter is acceptable for local MVP, but document that limitation.

---

# 15. Database Design

## 15.1 Global Conventions

- PostgreSQL is the source of truth.
- Business IDs use UUID, except:
  - department singleton id
  - audit log identity id
- Timestamps use `TIMESTAMPTZ` and UTC.
- `due_date` uses `DATE`.
- Business timezone: `Asia/Ho_Chi_Minh`.
- Mutable records use:
  - `revision INTEGER NOT NULL DEFAULT 1`
- Use FK, UNIQUE, NOT NULL, and CHECK where appropriate.
- Multi-row business rules belong in transactional service logic.

Required tables:

```text
departments
users
auth_sessions
tasks
notes
documents
document_bookmarks
announcements
audit_logs
```

## 15.2 `departments`

| Column | Rule |
|---|---|
| `id` | SMALLINT PK, `CHECK(id = 1)` |
| `code` | VARCHAR(50), UNIQUE, NOT NULL |
| `name` | VARCHAR(120), NOT NULL |
| timestamps | TIMESTAMPTZ |

Seed exactly one row.

## 15.3 `users`

| Column | Rule |
|---|---|
| `id` | UUID PK |
| `email` | VARCHAR(254), UNIQUE, lowercase |
| `password_hash` | TEXT NOT NULL |
| `full_name` | VARCHAR(120) NOT NULL |
| `employee_code` | VARCHAR(30), UNIQUE, nullable for Admin |
| `job_title` | VARCHAR(120), nullable |
| `account_type` | STAFF or ADMIN |
| `department_role` | EMPLOYEE or MANAGER, nullable for Admin |
| `department_id` | FK, nullable for Admin |
| `is_active` | BOOLEAN |
| `must_change_password` | BOOLEAN |
| `revision` | INTEGER |
| timestamps | TIMESTAMPTZ |

Constraints:

```text
STAFF:
  department_id = 1
  department_role IS NOT NULL
  employee_code IS NOT NULL

ADMIN:
  department_id IS NULL
  department_role IS NULL
  employee_code IS NULL
```

Never expose `password_hash` in API responses.

## 15.4 `auth_sessions`

| Column | Rule |
|---|---|
| `id` | UUID PK |
| `user_id` | FK users |
| `token_hash` | CHAR(64), UNIQUE |
| `csrf_token` | TEXT |
| `created_at` | TIMESTAMPTZ |
| `expires_at` | TIMESTAMPTZ |
| `revoked_at` | nullable TIMESTAMPTZ |

Indexes:

```text
token_hash
user_id
expires_at
```

## 15.5 `tasks`

| Column | Rule |
|---|---|
| `id` | UUID PK |
| `department_id` | FK |
| `kind` | PERSONAL / ASSIGNED |
| `title` | VARCHAR(160) |
| `description` | TEXT nullable |
| `status` | TODO / IN_PROGRESS / DONE / CANCELLED |
| `priority` | LOW / NORMAL / HIGH |
| `assignee_id` | FK users |
| `created_by` | FK users |
| `due_date` | DATE nullable |
| `completed_at` | nullable TIMESTAMPTZ |
| `deleted_at` | nullable TIMESTAMPTZ |
| `revision` | INTEGER |
| timestamps | TIMESTAMPTZ |

Rules:

```text
PERSONAL => created_by = assignee_id
status = DONE <=> completed_at IS NOT NULL
```

Immutable after creation:

```text
kind
created_by
department_id
```

Indexes:

```text
(assignee_id, kind, status)
(department_id, kind, status)
due_date
```

Normal business queries exclude soft-deleted rows.

## 15.6 `notes`

| Column | Rule |
|---|---|
| `id` | UUID PK |
| `owner_id` | FK users |
| `title` | VARCHAR(160) |
| `content` | TEXT |
| `revision` | INTEGER |
| timestamps | TIMESTAMPTZ |

Index:

```text
(owner_id, updated_at)
```

## 15.7 `documents`

| Column | Rule |
|---|---|
| `id` | UUID PK |
| `knowledge_scope` | COMPANY / DEPARTMENT |
| `department_id` | nullable FK; required for DEPARTMENT |
| `title` | VARCHAR(200) |
| `description` | TEXT nullable |
| `category` | POLICY / SOP / GUIDE / REFERENCE |
| `language` | vi / en / other |
| `created_by` | FK users |
| `updated_by` | FK users |
| `original_filename` | VARCHAR(255) |
| `storage_key` | TEXT UNIQUE |
| `mime_type` | VARCHAR(100) |
| `size_bytes` | BIGINT > 0 |
| `checksum_sha256` | CHAR(64) |
| `uploaded_by` | FK users |
| `uploaded_at` | TIMESTAMPTZ |
| `revision` | INTEGER |
| timestamps | TIMESTAMPTZ |

Rules:

```text
COMPANY => department_id IS NULL
DEPARTMENT => department_id IS NOT NULL
```

Indexes:

```text
(knowledge_scope, department_id)
updated_at
category
```

File bytes are stored privately outside PostgreSQL; this table stores only
metadata and the server-generated storage key.

## 15.8 `document_bookmarks`

| Column | Rule |
|---|---|
| `user_id` | FK users |
| `document_id` | FK documents |
| `created_at` | TIMESTAMPTZ |

Primary key:

```text
(user_id, document_id)
```

## 15.10 `announcements`

| Column | Rule |
|---|---|
| `id` | UUID PK |
| `department_id` | FK |
| `title` | VARCHAR(160) |
| `body` | TEXT |
| `created_by` | FK users |
| `updated_by` | FK users |
| `archived_at` | nullable TIMESTAMPTZ |
| `revision` | INTEGER |
| timestamps | TIMESTAMPTZ |

Index:

```text
(department_id, archived_at, created_at)
```

## 15.11 `audit_logs`

| Column | Rule |
|---|---|
| `id` | BIGINT identity PK |
| `actor_id` | nullable FK users |
| `action` | VARCHAR(80) |
| `entity_type` | VARCHAR(50) nullable |
| `entity_id` | VARCHAR(80) nullable |
| `result` | SUCCESS / DENIED / FAILURE |
| `request_id` | VARCHAR(80) |
| `details` | JSONB |
| `created_at` | TIMESTAMPTZ |

Example actions:

```text
LOGIN_SUCCEEDED
LOGIN_FAILED
USER_CREATED
USER_ROLE_CHANGED
USER_DEACTIVATED
PASSWORD_RESET
DOCUMENT_CREATED
DOCUMENT_VERSION_ADDED
DOCUMENT_VISIBILITY_CHANGED
DOCUMENT_STATUS_CHANGED
TASK_ASSIGNED
TASK_STATUS_CHANGED
NOTE_CREATED
NOTE_UPDATED
ACCESS_DENIED
```

`details` must use an allowlist.

Never dump entire request bodies.

---

# 16. REST API

Base path:

```text
/api/v1
```

## 16.1 General Rules

- JSON request/response except upload/download.
- Use `snake_case`.
- Reject undeclared request fields.
- Invalid UUID -> `422`.
- All list endpoints use server-side pagination.
- Default `page_size = 20`.
- Maximum `page_size = 100`.
- Search query `q` max 200 characters.
- Counts must be calculated after authorization filtering.
- Return DTOs, not raw ORM models.

List response:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

Error response:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Không tìm thấy tài nguyên hoặc bạn không có quyền truy cập.",
    "details": null
  },
  "request_id": "server-generated-request-id"
}
```

HTTP status usage:

| Code | Meaning |
|---|---|
| 200 | successful read/update |
| 201 | successful create |
| 204 | successful delete/logout/remove bookmark |
| 401 | unauthenticated/expired/revoked session |
| 403 | function forbidden/CSRF/password-change-required |
| 404 | resource missing or unreadable |
| 409 | revision/unique/business conflict |
| 413 | file too large |
| 415 | unsupported file type |
| 422 | validation failure |
| 429 | login throttle |
| 503 | required infrastructure dependency unavailable |

## 16.2 Auth and Profile

```text
POST   /auth/login
GET    /auth/me
GET    /auth/csrf
POST   /auth/logout
POST   /auth/change-password

GET    /me/profile
PATCH  /me/profile
```

`PATCH /me/profile` accepts:

```text
full_name
expected_revision
```

## 16.3 Dashboard and Personal Workspace

```text
GET     /dashboard

GET     /me/tasks
POST    /me/tasks
GET     /me/tasks/{id}
PATCH   /me/tasks/{id}
DELETE  /me/tasks/{id}

GET     /me/notes
POST    /me/notes
GET     /me/notes/{id}
PATCH   /me/notes/{id}
DELETE  /me/notes/{id}

GET     /me/bookmarks
PUT     /me/bookmarks/{document_id}
DELETE  /me/bookmarks/{document_id}
```

Creating through `/me/tasks` always creates `PERSONAL`.

For Employee PATCH on ASSIGNED task, only allow:

```json
{
  "expected_revision": 3,
  "status": "DONE"
}
```

Reject unauthorized fields instead of silently ignoring them.

## 16.4 Department Workspace

```text
GET    /department/members
GET    /department/tasks
POST   /department/tasks
GET    /department/tasks/{id}
PATCH  /department/tasks/{id}
```

Manager-only.

Only ASSIGNED tasks are exposed here.

## 16.5 Documents

```text
GET    /documents
POST   /documents
GET    /documents/{id}
PATCH  /documents/{id}

POST   /documents/{id}/file
GET    /documents/{id}/file/download
GET    /documents/{id}/file/preview
```

Document creation uses multipart:

```text
metadata: JSON string
file: binary
```

File replacement includes:

```text
file
expected_revision
```

Document response should include server-calculated UI permissions:

```json
{
  "permissions": {
    "can_edit": false,
    "can_upload_file": false,
    "can_bookmark": true
  }
}
```

These flags help the UI but never replace backend authorization.

## 16.6 Announcements

```text
GET    /announcements
POST   /announcements
PATCH  /announcements/{id}
```

No permanent DELETE.

PATCH requires `expected_revision`.

## 16.7 Admin

```text
GET    /admin/overview

GET    /admin/users
POST   /admin/users
GET    /admin/users/{id}
PATCH  /admin/users/{id}
POST   /admin/users/{id}/reset-password

GET    /admin/audit-logs
```

Reset password request:

```json
{
  "admin_password": "..."
}
```

## 16.8 Health

```text
GET /health/live
GET /health/ready
```

`ready` checks:

- database connectivity
- basic storage readiness

Health responses must not expose:

- database URL
- DB credentials
- absolute storage paths
- stack traces

---

# 17. Optimistic Concurrency

The following mutable resources use `revision`:

- profile
- users
- tasks
- notes
- documents
- announcements

PATCH requests require:

```text
expected_revision
```

Conditional update must include both authorization scope and revision.

Conflict response:

```json
{
  "error": {
    "code": "REVISION_CONFLICT",
    "message": "Dữ liệu đã được cập nhật. Vui lòng tải lại trước khi lưu.",
    "details": null
  },
  "request_id": "server-generated-request-id"
}
```

DELETE for notes/PERSONAL tasks also requires `expected_revision`, passed consistently as a query parameter.

Bookmarks do not require revision.

---

# 18. Backend Implementation Rules

## 18.1 Responsibilities

```text
Router/API:
  validate request
  obtain current principal
  call service
  return DTO

Service:
  business rules
  transactions
  state transitions

Policy:
  authorization and query scope

Storage:
  secure file validation/read/write

Database:
  persistence
  constraints
  indexes
```

Do not place the whole application in `main.py` or in routers.

Use one SQLAlchemy Session per request/unit of work.

Commit/rollback explicitly.

Do not share a global SQLAlchemy Session across concurrent requests.

## 18.2 Authorization Before Data Exposure

Examples:

```text
Private note:
WHERE note.id = :requested_id
AND note.owner_id = :current_user_id
```

```text
Employee document:
WHERE department_id = 1
AND knowledge_scope = 'DEPARTMENT'
```

Pagination, search, counts, and statistics must operate on already-authorized queries.

Do not fetch broad data and filter it in the frontend.

---

# 19. File Storage

Files must be stored outside the public webroot.

Example storage key:

```text
documents/{document_uuid}/{version_uuid}.pdf
```

Server generates all path components.

Never use `original_filename` as the storage path.

Upload flow:

1. Check authorization.
2. Check size and supported extension/type.
3. Write to a server-generated temporary path.
4. Calculate SHA-256.
5. Lock/check document revision when required.
6. Move file to final private storage.
7. Insert database metadata/version.
8. Commit.
9. On failure, rollback and clean unreferenced temporary/final files.

Filesystem and PostgreSQL do not share one atomic transaction.

Implement an explicit orphan-file inspection/cleanup command with a dry-run mode.

Do not automatically delete files at application startup.

---

# 20. Migration and Seed

## 20.1 Migration

- Alembic owns schema migrations.
- Do not use `drop_all/create_all` as normal startup behavior.
- Do not delete the database to bypass migration problems.
- Application startup must not silently rebuild the schema.

## 20.2 Seed

Seed must be a separate idempotent command.

Seed exactly:

```text
1 department
1 Admin
1 Manager
6 Employees
```

Emails:

```text
admin@example.test
manager@example.test
employee01@example.test
...
employee06@example.test
```

Employee codes:

```text
Manager: M001
Employees: E001–E006
```

Admin has no employee code.

Seed passwords come from environment variables.

Development demo seed may set `must_change_password=false`.

Admin-created/reset accounts must still use `must_change_password=true`.

Seed sample business data:

- Each STAFF: 3 PERSONAL tasks.
- Each STAFF: 2 private notes.
- 6 ASSIGNED tasks across useful statuses.
- Some overdue open tasks.
- 2 announcements.
- 10 sample documents with valid current files:
  - 8 `DEPARTMENT`
  - 2 `COMPANY`
- Some valid bookmarks.

Running seed again must not:

- duplicate entities
- reset changed passwords
- overwrite edited notes/tasks
- delete existing data
- revert document permissions/status

A destructive demo reset must be a separate explicit command and must be blocked in production.

---

# 21. Frontend Rules

- All business data comes from API.
- Do not store tasks, notes, documents, or role data in localStorage.
- localStorage may store harmless UI preferences such as collapsed sidebar state.
- TanStack Query keys must be scoped so data from one account cannot leak into another session.
- Clear sensitive query/cache state on logout/account change.
- On session expiration:
  - clear sensitive in-memory state
  - redirect to login
- Frontend validation should match backend validation.
- Show field-level validation errors.
- Disable submit while request is pending.
- Prevent duplicate submissions.
- Handle `409` with a reload-data action.
- Prefer server-confirmed updates for security-sensitive actions.
- Never render raw HTML from:
  - notes
  - announcements
  - filenames
  - uploaded Markdown

Reusable components should include at least:

```text
AppLayout
AdminLayout
PageHeader
StatCard
DataTable
Pagination
EmptyState
ErrorState
LoadingState
ConfirmDialog
TaskForm
NoteEditor
DocumentForm
DocumentFileDetails
DocumentVisibilityBadge
UserRoleBadge
```

Responsive checks:

```text
~390 px
~768 px
~1440 px
```

---

# 22. Docker and Environment

Compose services:

```text
db
migrate
api
web
```

Rules:

- `db` uses a named PostgreSQL volume.
- uploads use a separate named volume.
- restart/recreate must preserve data.
- `api` starts only after DB readiness and successful migrations.
- default deployment exposes only the web entry point.
- do not expose PostgreSQL directly to the public internet.
- do not automatically run `docker compose down -v`.

Example `.env.example`:

```dotenv
APP_ENV=development
APP_NAME=Enterprise Copilot
BUSINESS_TIMEZONE=Asia/Ho_Chi_Minh

DATABASE_URL=
MIGRATION_DATABASE_URL=

SESSION_COOKIE_NAME=enterprise_copilot_session
SESSION_COOKIE_SECURE=false
SESSION_TTL_HOURS=8
ALLOWED_ORIGINS=http://localhost:8080,http://localhost:5173

UPLOAD_DIR=/app/storage/uploads
MAX_UPLOAD_BYTES=10485760

SEED_ADMIN_EMAIL=admin@example.test
SEED_ADMIN_PASSWORD=
SEED_MANAGER_PASSWORD=
SEED_EMPLOYEE_PASSWORD=
```

Production must not run with insecure cookies.

The application must fail clearly when required configuration is missing.

Do not silently fall back to SQLite or in-memory storage.

---

# 23. Logging and Security Baseline

Required:

- Backend authorization on every protected resource.
- IDOR tests.
- ORM/parameterized SQL.
- Never trust client-supplied role/owner/department values.
- CSRF checks on mutations.
- Origin allowlist.
- Private file storage.
- File extension/type/size validation.
- Do not execute uploaded files.
- Request IDs.
- Structured errors.
- No secrets in git.
- No secrets in logs.
- No stack traces or database connection strings returned to the frontend.
- Audit important account, permission, document, and task actions.
- Authenticated/private responses should use appropriate cache controls; prefer `no-store` for sensitive responses.

The MVP is not automatically considered production-security-audited.

---

# 24. Critical Acceptance Tests

Backend tests must use PostgreSQL, not a SQLite substitute.

## Authentication

- Correct login creates session.
- Wrong password returns generic failure.
- Logout invalidates session.
- Locked account loses access.
- Role change revokes sessions.
- Required password change blocks business APIs.
- Missing/invalid CSRF blocks mutation.
- Login throttling returns `429`.

## Tasks

- Employee creates PERSONAL task owned by self.
- User cannot read another user's PERSONAL task.
- Manager cannot read Employee PERSONAL task.
- Admin cannot read PERSONAL task.
- Manager assigns task to active Employee.
- Employee cannot edit protected ASSIGNED fields.
- Employee can complete allowed ASSIGNED task.
- Reassignment removes old assignee access.
- Concurrent stale revision returns `409`.

## Notes

- Owner CRUD works.
- Other Employee cannot read note.
- Manager cannot read Employee note.
- Admin cannot read STAFF note.

## Documents

- Valid upload stores real file + metadata + version.
- Invalid/oversized file is rejected cleanly.
- Employee list contains only readable documents.
- Employee cannot reveal MANAGER_ONLY metadata by guessed UUID.
- Restricted data is absent from counts/search results.
- Visibility change immediately affects subsequent access.
- Archived bookmarked document disappears from visible bookmark list.
- Version 2 does not overwrite version 1.
- Version/document mismatch is rejected.
- Concurrent upload does not duplicate version number.
- File/DB failure does not report false success.

## Admin

- STAFF cannot call Admin APIs.
- Last active Manager cannot be locked/demoted.
- Password reset revokes sessions and requires password change.
- API cannot create Admin through STAFF management.

## Audit

- Role/document-visibility changes create audit records.
- Logs never contain password/token/private note content.

## UI/Data

- Manager logout followed by Employee login does not leak cached Manager data.
- Deep URL refresh works.
- Backend outage shows a real error, not mock data.
- Restart without deleting volumes preserves DB and uploaded files.
- Running seed twice is safe.

---

# 25. Implementation Phases

The agent must implement **one phase at a time**.

The agent must stop after completing and documenting the current phase.

Do not start the next phase until explicitly requested.

---

## Phase 0 — Agent Continuity Setup

### Goal

Create the repository continuity system before implementation expands.

### Work

Create:

```text
.Agent/PROJECT_MEMORY.md
.Agent/STATE.md
.Agent/DECISIONS.md
.Agent/PHASE_LOG.md
```

Initialize them using the templates from Section 5.

Inspect the existing repository before changing code.

Record:

- current repository structure
- existing technology choices
- existing working commands
- current database state
- relevant existing files
- uncommitted user changes that must not be overwritten

### Exit Criteria

- `.Agent` files exist.
- `STATE.md` accurately describes the repository.
- No unrelated existing work was deleted.

---

## Phase 1 — Foundation, Database, Seed, Minimal Login

### Goal

Create a runnable application foundation with PostgreSQL schema, idempotent seed, and a verified demo login.

### Work

Frontend:

- Vite + React + TypeScript base.
- Basic `/login` screen.
- Minimal authenticated landing screen sufficient to verify login.

Backend:

- FastAPI application.
- Configuration loading.
- SQLAlchemy setup.
- Alembic.
- Basic error handling.
- Request ID middleware.
- Password hashing.
- Minimal session login endpoint needed for verification.

Database:

Create the required schema through Alembic migrations.

Seed:

- one department
- Admin
- Manager
- six Employees
- baseline sample data where practical

Infrastructure:

- `.env.example`
- local dev commands
- PostgreSQL configuration

### Exit Criteria

- Database is PostgreSQL.
- Alembic migration succeeds from a clean database.
- Seed succeeds.
- Seed can run a second time safely.
- Demo user can log in through the real backend.
- Frontend login uses the real API.
- Relevant tests/build checks pass.

### Required State Update

Record:

- migration revision
- seed command
- demo login verification
- exact commands that passed
- files needed for Phase 2

---

## Phase 2 — Full Authentication, Authorization, App Shell

### Goal

Complete the security and navigation foundation before business modules expand.

### Work

Backend:

- opaque sessions
- HttpOnly cookie
- CSRF endpoint/checks
- logout
- current-user endpoint
- change password
- `must_change_password`
- session revocation
- login throttling
- authorization helpers/policies
- role guards

Frontend:

- authenticated app shell
- Admin shell
- sidebar
- account menu
- route guards
- change-password flow
- session-expired handling
- account-switch cache cleanup

### Exit Criteria

- Direct API calls enforce roles.
- Employee cannot access Manager/Admin functions.
- Manager cannot access Admin functions.
- Admin cannot access Personal Workspace.
- CSRF is enforced.
- password-change-required flow works.
- revoked/locked sessions stop working.
- auth tests pass.

---

## Phase 3 — Personal Workspace

### Goal

Deliver complete STAFF personal productivity features.

### Work

Implement:

- PERSONAL tasks
- ASSIGNED task view/status updates for assignee
- private notes
- profile
- bookmark API foundation

Frontend:

- `/app/workspace`
- task list/forms/filters
- notes UI
- saved-document tab shell connected to real bookmark API
- `/app/profile`

Backend:

- ownership-scoped task queries
- ownership-scoped note queries
- revision conflicts
- soft deletion for PERSONAL tasks
- private-data audit rules

### Exit Criteria

- PERSONAL task CRUD works.
- Notes CRUD works.
- Ownership tests pass.
- Manager/Admin cannot read another STAFF user's private data.
- Revision conflict test passes.
- Data survives refresh/restart.

---

## Phase 4 — Department Workspace

### Goal

Deliver Manager task assignment and member management view.

### Work

Implement:

- `/app/team`
- member list
- ASSIGNED task list
- filters
- create assignment
- edit assignment
- reassignment
- Manager status transitions
- cancellation/reopen

### Exit Criteria

- Manager can assign to active Employee.
- Employee sees the real assignment.
- Employee can perform allowed status changes.
- Manager sees updates.
- Reassignment immediately changes access.
- Employee cannot access Manager APIs/routes.
- Department task queries never expose PERSONAL tasks.

---

## Phase 5 — Document Library and File Storage

### Goal

Deliver secure, persistent, versioned document management.

### Work

Implement:

- document metadata
- private file storage
- upload validation
- document creation
- current-file replacement
- company/department knowledge scope
- list/search/filter
- detail page
- download
- TXT/MD preview
- bookmark integration
- concurrency handling
- orphan-file inspection/cleanup command

### Exit Criteria

- Upload stores real file and DB metadata.
- Restart preserves files.
- Employee sees only allowed Company or same-Department Knowledge documents.
- Department Knowledge from another department is not leaked through list/count/detail/download.
- Bookmark visibility follows current authorization.
- File failure cleanup is verified.

---

## Phase 6 — Announcements, Dashboards, Admin Console, Audit

### Goal

Complete operational and administrative features.

### Work

Announcements:

- create/edit/archive/restore
- STAFF active-announcement view

Dashboards:

- Employee stats/content
- Manager department stats
- Admin overview

Admin:

- STAFF list/search/filter
- create STAFF
- edit STAFF
- role change
- lock/unlock
- reset password
- last-active-Manager protection

Audit:

- required events
- filters
- privacy-safe details

### Exit Criteria

- Dashboard counts come from authorized database queries.
- Admin account management works.
- Role/status changes revoke sessions.
- Last active Manager protection works transactionally.
- Password reset works securely.
- Audit does not contain secrets/private content.

---

## Phase 7 — Hardening, E2E, Docker, Documentation

### Goal

Make the web application reliable to run from a clean environment.

### Work

- Responsive pass.
- Loading/empty/error states.
- Deep-link SPA fallback.
- Full Docker Compose.
- migration startup flow.
- persistent DB volume.
- persistent upload volume.
- health checks.
- E2E flows.
- final security regression tests.
- README.
- `.docs/ARCHITECTURE.md`
- `.docs/SETUP.md`
- `.docs/DATA_ACCESS.md`

Minimum E2E flows:

### Flow A — Employee

```text
Login
-> Create PERSONAL task
-> Create note
-> Bookmark readable document
-> Refresh
-> Data remains
```

### Flow B — Assignment

```text
Manager login
-> Assign Employee A
-> Employee A login
-> Mark task DONE
-> Manager login
-> Updated state is visible
```

### Flow C — Document Authorization

```text
Manager publishes DEPARTMENT document
-> Employee can read/download
-> Manager changes to MANAGER_ONLY
-> Employee loses list/detail/bookmark/download access
```

### Flow D — Persistence

```text
Create note + upload file
-> Stop services without deleting volumes
-> Restart
-> Login
-> Note and file still exist
```

### Exit Criteria

- Clean setup works from documented commands.
- Frontend production build passes.
- TypeScript checks pass.
- Backend tests pass.
- Critical E2E tests pass.
- Restart preserves data.
- Documentation matches actual commands.
- `.Agent/STATE.md` reports final status accurately.

---

# 26. Definition of Done

The web application is complete only when:

- Required pages work with real backend data.
- Frontend does not substitute mock business data.
- PostgreSQL stores business data.
- File uploads persist across restart.
- Backend authorization is tested by direct API requests.
- Migrations work from a clean database.
- Seed is idempotent.
- Authentication/session lifecycle works.
- Critical tests pass.
- Frontend build succeeds.
- TypeScript checks succeed.
- Docker Compose starts the stack from documented instructions.
- Restart does not delete data.
- README and `.docs` reflect the actual implementation.
- `.Agent` continuity files accurately summarize the final repository.
- The agent clearly reports tests that were run and tests that were not run.

Never claim a verification passed without executing it.

---

# 27. Coding Agent Working Rules

When given this specification:

1. Treat it as the source of truth.
2. Work on only the phase requested by the user.
3. Before coding, read the `.Agent` continuity files as defined in Section 5.
4. Do not rewrite unrelated existing code.
5. Do not discard user changes.
6. Do not replace PostgreSQL with SQLite/localStorage/in-memory persistence for convenience.
7. Do not invent modules outside the current phase.
8. Keep authorization logic centralized and reusable.
9. Use real API/database integration as soon as a feature is implemented.
10. Run the relevant tests/build checks before declaring the phase complete.
11. Update `.Agent` before stopping.
12. Stop after the requested phase and wait for the next instruction.

If implementation must deviate from this specification:

- choose the smallest safe deviation,
- record it in `.Agent/DECISIONS.md`,
- mention it in the phase handoff,
- do not silently change product behavior.

---
