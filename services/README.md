# BrewPass Services

Four FastAPI services and a shared library. Architecture and trade-offs: [ADR 0002](../docs/adr/0002-microservices.md).

| Service    | Package            | Database            | Public routes (via gateway)                  |
| ---------- | ------------------ | ------------------- | -------------------------------------------- |
| `common`   | `brewpass_common`  | —                   | —                                            |
| `auth`     | `auth_service`     | `brewpass_auth`     | `/api/v1/auth/*`, `/api/v1/users/*`          |
| `catalog`  | `catalog_service`  | `brewpass_catalog`  | `/api/v1/shops*`                             |
| `commerce` | `commerce_service` | `brewpass_commerce` | `/api/v1/subscriptions*`, `/api/v1/orders*`  |
| `payment`  | `payment_service`  | `brewpass_payment`  | `/api/v1/payments*`                          |

## Local development

```bash
scripts/setup-dev.sh            # keys, .env, services/.venv with every package installed
docker compose up --build       # db + services (hot reload) + gateway on :8080
scripts/test.sh                 # ruff + pytest for every service
scripts/smoke.sh                # end-to-end checks through the gateway
```

Run a single service's tests: `cd services/auth && ../.venv/bin/pytest`. Each suite recreates its own `<database>_test` database on the local PostgreSQL.

## Conventions

- **Layers:** `api` (routers) → `services` (business logic) → `repositories` (data access) → `models`.
- **Envelope:** every response is `{ "success": bool, "data": ..., "error": { "code", "message", "details" } | null }`.
- **Errors:** raise `AppError` subclasses from `brewpass_common.errors` (`NotFoundError`, `ConflictError`, `UnauthorizedError`, `ForbiddenError`, `UnprocessableError`, `ServiceUnavailableError`). Validation errors become `VALIDATION_ERROR`, unexpected ones `INTERNAL_ERROR`.
- **App factory:** `brewpass_common.app.create_service_app` adds error handlers, JSON logging with `X-Request-ID`, security headers, CORS, rate limiting, `/health` and docs at `/api/v1/docs/<service>`.
- **Auth in any service:** `CurrentPrincipal` (user id + role from a verified RS256 token) and `Depends(require_roles(UserRole.SHOP_OWNER))` from `brewpass_common.security`.
- **Internal routes:** live under `/internal`, require `Depends(require_internal_token)` and are called with `brewpass_common.internal_client.InternalClient`. The gateway never exposes them.
- **No cross-service foreign keys:** store the other service's id as a plain UUID (and a snapshot of display data when history must stay readable).
- **Rate limits:** per client IP; stricter per route with `@limiter.limit("5/minute")`.

## Migrations

Each service has its own Alembic setup (`services/<name>/alembic`). From the service directory:

```bash
../.venv/bin/alembic revision --autogenerate -m "describe change"   # then review the file
../.venv/bin/alembic upgrade head
../.venv/bin/alembic check                                           # fails on model/migration drift
```

In Docker, every service runs `alembic upgrade head` (and its seed when `SEED_ON_START=true`) before starting.

## Authentication flow

1. `POST /api/v1/auth/register` with `{"phone_number": "0555 123 45 67"}` creates the account on first use and sends a one-time code. Outside production the code is always **`1234`** and is never returned by the API.
2. `POST /api/v1/auth/verify-otp` returns an RS256 access token (15 min), a refresh token (30 days) and the user, including `profile_completed`.
3. Send `Authorization: Bearer <access_token>` to any service; in Swagger use **Authorize**.
4. `POST /api/v1/auth/refresh` rotates the pair; re-using an old refresh token revokes every session of that user. `POST /api/v1/auth/logout` revokes a refresh token.
5. `GET/PATCH /api/v1/users/me` reads and completes the profile.

## Demo accounts (seed)

| Role       | Phone                                            |
| ---------- | ------------------------------------------------ |
| Admin      | +905550000001                                    |
| Customer   | +905550000100                                    |
| Shop owner | +905550000011 … +905550000016 (one per shop)     |
