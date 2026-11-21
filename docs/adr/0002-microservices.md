# ADR 0002: Split the backend into services

- **Status:** Accepted
- **Date:** 2026-11-21
- **Amends:** [ADR 0001](0001-tech-stack.md) (backend structure only; the stack is unchanged)

## Context

The backend started as one FastAPI application. BrewPass has clear business areas (identity, shop catalogue, subscriptions and orders, payments), and the project should show how those areas can be owned, deployed and scaled independently.

A full microservice split (one service per entity, message broker, sagas) would add a lot of distributed-systems complexity for little benefit at this size. The most important business rule, *placing an order uses exactly one credit*, must stay simple and safe.

## Decision

Split the backend into four services behind an API gateway:

| Service  | Owns                                              | Public routes                         |
| -------- | ------------------------------------------------- | ------------------------------------- |
| auth     | users, OTP challenges, refresh tokens             | `/api/v1/auth/*`, `/api/v1/users/*`   |
| catalog  | shops, opening hours, products (PostGIS)          | `/api/v1/shops*`                      |
| commerce | plans, subscriptions, orders, order status events | `/api/v1/subscriptions*`, `/api/v1/orders*` |
| payment  | payments (BrewPass Pay mock)                      | `/api/v1/payments*`                   |

- **Gateway:** nginx is the single entry point (`:8080`). It routes by path, propagates `X-Request-ID`, forwards the client IP and never exposes `/internal/*`.
- **Database per service:** one PostgreSQL server, one database per service. No cross-service foreign keys; references are plain UUIDs. Orders keep a snapshot of shop and product names.
- **Subscriptions and orders live together** in the commerce service, so deducting a credit stays a single local transaction with a row lock (`SELECT … FOR UPDATE`) instead of a distributed saga.
- **Authentication:** only the auth service holds the RS256 private key and issues access tokens. Every service verifies tokens locally with the public key; no per-request call to the auth service. Roles travel in the token.
- **Service-to-service calls:** synchronous HTTP to `/internal/*` routes, protected by a shared `X-Internal-Token`. Errors keep their code and status; network failures surface as `503 SERVICE_UNAVAILABLE`.
- **Shared code:** `services/common` (`brewpass-common`) holds the response envelope, errors, logging, middleware, rate limiting, token verification, the app factory, migration runner and test helpers, so every service behaves the same.
- **Seed data** uses deterministic UUIDs (`brewpass_common.seed_ids`) so, for example, the catalog can assign shops to the owners the auth service created without reading its database.

## Consequences

- Each service can be deployed, scaled and migrated on its own; failures are isolated (e.g. the catalog stays up if payments are down).
- Local development needs Docker Compose (database, four services, gateway); `scripts/setup-dev.sh`, `scripts/test.sh` and `scripts/smoke.sh` keep that manageable.
- Cross-service data is eventually consistent and needs explicit calls (e.g. commerce asks the catalog whether a product exists). Joins across services are not possible; the API composes data instead.
- No message broker yet. Real-time order updates (SSE) are a candidate for introducing Redis pub/sub later.
- Rate limits are kept in memory per service instance; a shared store (Redis) is needed before running multiple replicas.
