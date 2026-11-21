# BrewPass Backend

FastAPI service exposing the BrewPass REST API under `/api/v1`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

alembic upgrade head            # apply migrations
python -m app.db.seed           # idempotent seed data
uvicorn app.main:app --reload   # http://localhost:8000/api/v1/docs
pytest                          # run tests (needs the `db` service; uses `brewpass_test`)
ruff check . && ruff format --check .
```

## API conventions

- Code is layered: `app/api` (routers) → `app/services` (business logic) → `app/repositories` (data access) → `app/models`.
- Every response uses the envelope `{ "success": bool, "data": ..., "error": { "code", "message", "details" } | null }`.
- Services raise `AppError` subclasses (`NotFoundError`, `ConflictError`, `UnauthorizedError`, `ForbiddenError`, `UnprocessableError`); global handlers map them, validation errors (`VALIDATION_ERROR`) and unexpected errors (`INTERNAL_ERROR`) to the envelope.
- Each request gets an `X-Request-ID` and one structured JSON log line; security headers are added to every response.
- Rate limiting is per client IP (`RATE_LIMIT_DEFAULT`); add stricter limits with `@limiter.limit(...)`.
- OpenAPI docs: `/api/v1/docs` (Swagger UI) and `/api/v1/redoc`.

## Database

- Models live in `app/models/`; migrations in `alembic/versions/`.
- After changing a model: `alembic revision --autogenerate -m "describe change"`, review the file, then `alembic upgrade head`.
- `alembic check` fails if the models and migrations have drifted apart.

## Demo accounts (seed)

| Role       | Phone           |
| ---------- | --------------- |
| Admin      | +905550000001   |
| Customer   | +905550000100   |
| Shop owner | +905550000011 … +905550000016 (one per shop) |
