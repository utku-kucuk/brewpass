#!/usr/bin/env bash
# Lints and tests every Python service against the local PostgreSQL (docker compose up -d db).
# Each suite recreates its own `<service>_test` database.
set -euo pipefail

cd "$(dirname "$0")/../services"
PY=".venv/bin"

"$PY/ruff" check .
"$PY/ruff" format --check .
for service in common auth catalog commerce payment; do
  echo "== $service"
  (cd "$service" && "../$PY/pytest" -q)
done
