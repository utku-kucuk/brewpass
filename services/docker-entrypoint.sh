#!/bin/sh
# Applies the service's migrations (and optional seed data) before starting it.
set -e

echo "[$SERVICE] applying migrations"
alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ] && [ -f "${SERVICE}_service/seed.py" ]; then
  echo "[$SERVICE] loading seed data"
  python -m "${SERVICE}_service.seed"
fi

exec "$@"
