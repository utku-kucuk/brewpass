#!/usr/bin/env bash
# End-to-end smoke test against a running stack (docker compose up), through the gateway.
set -euo pipefail

BASE="${BASE_URL:-http://localhost:8080}"
PHONE="${SMOKE_PHONE:-05550000100}"
pass=0

check() {  # check <description> <expected> <actual>
  if [[ "$2" == "$3" ]]; then
    echo "  ok   $1"
    pass=$((pass + 1))
  else
    echo "  FAIL $1 (expected '$2', got '$3')"
    exit 1
  fi
}

json() { python3 -c "import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1], {}, {'d': d}))" "$1"; }

echo "Gateway: $BASE"
check "gateway health" "ok" "$(curl -s "$BASE/health" | json 'd["data"]["status"]')"
for svc in auth catalog commerce payment; do
  check "$svc health (database ok)" "ok" "$(curl -s "$BASE/health/$svc" | json 'd["data"]["database"]')"
  check "$svc docs" "200" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/v1/docs/$svc")"
done

check "internal routes are not exposed" "404" \
  "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/internal/shops/00000000-0000-0000-0000-000000000000")"

curl -s -X POST "$BASE/api/v1/auth/register" -H 'content-type: application/json' \
  -d "{\"phone_number\": \"$PHONE\"}" >/dev/null
TOKENS=$(curl -s -X POST "$BASE/api/v1/auth/verify-otp" -H 'content-type: application/json' \
  -d "{\"phone_number\": \"$PHONE\", \"code\": \"1234\"}")
check "sign in with OTP" "True" "$(echo "$TOKENS" | json 'd["success"]')"
ACCESS=$(echo "$TOKENS" | json 'd["data"]["access_token"]')

check "profile through gateway" "Demo Customer" \
  "$(curl -s "$BASE/api/v1/users/me" -H "Authorization: Bearer $ACCESS" | json 'd["data"]["full_name"]')"
check "request id is propagated" "smoke-123" \
  "$(curl -s -D - -o /dev/null "$BASE/api/v1/users/me" -H 'X-Request-ID: smoke-123' \
     -H "Authorization: Bearer $ACCESS" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-request-id"{print $2}')"

echo "All $pass checks passed."
