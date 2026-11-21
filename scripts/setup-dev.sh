#!/usr/bin/env bash
# One-time local setup: dev keys, .env and a shared virtualenv with every service installed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

scripts/generate-dev-keys.sh
[[ -f .env ]] || cp .env.example .env

python3 -m venv services/.venv
services/.venv/bin/pip install --quiet --upgrade pip
services/.venv/bin/pip install --quiet -e "services/common[dev]" \
  -e services/auth -e services/catalog -e services/commerce -e services/payment
echo "Done. Start the stack with: docker compose up --build"
