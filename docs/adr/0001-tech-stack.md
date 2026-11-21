# ADR 0001: Technology stack

- **Status:** Accepted
- **Date:** 2026-11-21

## Context

BrewPass needs a REST API, a relational database with location queries, and a responsive web client with an interactive map. The stack should be quick to develop with, well documented and easy to run locally.

## Decision

| Layer    | Choice                                   |
| -------- | ---------------------------------------- |
| Backend  | Python 3.12+, FastAPI, Uvicorn           |
| Database | PostgreSQL 16 with PostGIS               |
| Frontend | React 19, TypeScript, Vite               |
| Map      | Leaflet with OpenStreetMap tiles         |
| Tooling  | Ruff and pytest (backend), ESLint and Prettier (frontend), Docker Compose |

## Rationale

- **FastAPI** gives request validation via Pydantic and auto-generated OpenAPI docs out of the box, which covers input validation and API documentation with little extra code.
- **PostgreSQL + PostGIS** was chosen over SQLite:
  - *Location queries:* PostGIS `geography` columns, GiST indexes and `ST_DWithin` / `ST_Distance` give accurate, indexed "nearby shops" queries instead of hand-written Haversine math.
  - *Concurrency:* customers and shop owners write at the same time. Row-level locks (`SELECT ... FOR UPDATE`) keep credit deduction safe; SQLite locks the whole database on write.
  - *Native types:* `UUID`, `JSONB` and enums map directly to the data model.
  - The extra setup cost is one Docker Compose service.
- **React + Vite + TypeScript** is a widely used, fast-to-iterate combination with strong typing for API contracts.
- **Leaflet** is free, lightweight and needs no API key.

## Consequences

- Contributors need Docker (or a local PostgreSQL with PostGIS) to run the backend against a real database.
- Tests run against a real PostgreSQL instance, both locally and in CI.
