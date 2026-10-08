# Architecture

## Runtime

The stack has four Compose services:

```text
browser -> web/nginx -> api/FastAPI -> PostgreSQL
                          |
                          +-> uploads_data
```

Only nginx publishes port `8080`. Nginx serves the built React SPA, proxies `/api/` to FastAPI, supplies the `/healthz` check, and falls back unknown frontend paths to `index.html` for deep links.

FastAPI exposes `/api/v1`, uses one SQLAlchemy session per request, and keeps authentication in opaque server-side sessions stored in `auth_sessions`. Alembic owns the schema; application startup never creates or drops tables.

## Startup order

`db` must pass `pg_isready`. `migrate` then runs `alembic upgrade head`. `seed` creates the demo identities idempotently. The API is considered healthy only when both PostgreSQL and the upload volume are usable. Web waits for the API health check.

## Storage

PostgreSQL data persists in `postgres_data`. Uploaded document bytes persist in `uploads_data`, under server-generated keys partitioned by document scope. The API never exposes the upload directory as static content.

## Frontend resilience

TanStack Query owns server state. Routes provide loading, empty and error states; an application error boundary handles unexpected rendering failures. The nginx fallback makes authenticated deep links reloadable in production.
