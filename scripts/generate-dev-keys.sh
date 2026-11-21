#!/usr/bin/env bash
# Generates the RS256 key pair used to sign (auth service) and verify (all services) access tokens.
# Keys are written to ./secrets (git-ignored). Existing keys are kept unless --force is given.
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)/secrets"
PRIVATE="$DIR/jwt_private.pem"
PUBLIC="$DIR/jwt_public.pem"

if [[ -f "$PRIVATE" && "${1:-}" != "--force" ]]; then
  echo "Keys already exist in $DIR (use --force to replace them)."
  exit 0
fi

mkdir -p "$DIR"
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$PRIVATE" 2>/dev/null
openssl pkey -in "$PRIVATE" -pubout -out "$PUBLIC"
chmod 600 "$PRIVATE"
chmod 644 "$PUBLIC"
echo "Wrote $PRIVATE and $PUBLIC"
