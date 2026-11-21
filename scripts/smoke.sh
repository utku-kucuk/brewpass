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
  check "$svc health (right service, database ok)" "$svc ok" \
    "$(curl -s "$BASE/health/$svc" | json 'd["data"]["service"] + " " + d["data"]["database"]')"
  check "$svc docs" "200" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/v1/docs/$svc")"
done

check "internal routes are not exposed" "404" \
  "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/internal/shops/00000000-0000-0000-0000-000000000000")"

# Note: the auth service allows 5 sign-in requests per minute per client IP.
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

# --- Shop discovery ----------------------------------------------------------------------
SHOPS=$(curl -s "$BASE/api/v1/shops?lat=41.0222&lng=28.9765&radius=2500")
check "nearest shop to Karaköy pier" "Karaköy Brew Lab" "$(echo "$SHOPS" | json 'd["data"]["items"][0]["name"]')"
SHOP_ID=$(echo "$SHOPS" | json 'd["data"]["items"][0]["id"]')
check "shop menu" "5" "$(curl -s "$BASE/api/v1/shops/$SHOP_ID/menu" | json 'len(d["data"]["items"])')"

# --- Subscriptions + BrewPass Pay -----------------------------------------------------------
AUTH=(-H "Authorization: Bearer $ACCESS" -H 'content-type: application/json')
card() {  # card <number> -> JSON card object
  printf '{"number": "%s", "exp_month": 12, "exp_year": %d, "cvc": "123", "holder_name": "Demo Customer"}' \
    "$1" "$(( $(date +%Y) + 1 ))"
}
subscribe_body() { printf '{"plan_code": "%s", "card": %s}' "$1" "$(card "$2")"; }

check "plans are listed" "SIP,DAILY,BOTTOMLESS" \
  "$(curl -s "$BASE/api/v1/subscriptions/plans" | json '",".join(p["code"] for p in d["data"])')"

# Start from a clean state so the script can run repeatedly.
curl -s -X DELETE "$BASE/api/v1/subscriptions/me" "${AUTH[@]}" >/dev/null

BODY=$(subscribe_body DAILY 4000000000000002)
STATUS=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/api/v1/subscriptions" "${AUTH[@]}" -d "$BODY")
check "declined card is rejected" "402" "$STATUS"

BODY=$(subscribe_body DAILY 4242424242424242)
SUB=$(curl -s -X POST "$BASE/api/v1/subscriptions" "${AUTH[@]}" -d "$BODY")
check "buy Daily pass with 4242" "ACTIVE" "$(echo "$SUB" | json 'd["data"]["status"]')"
TX=$(echo "$SUB" | json 'd["data"]["payment_transaction_id"]')

ME=$(curl -s "$BASE/api/v1/subscriptions/me" "${AUTH[@]}")
check "current pass has 20 credits" "20" "$(echo "$ME" | json 'd["data"]["remaining_credits"]')"

PAYMENTS=$(curl -s "$BASE/api/v1/payments/me" "${AUTH[@]}")
check "payment history has the charge" "SUCCEEDED" \
  "$(echo "$PAYMENTS" | json "next(p['status'] for p in d['data'] if p['transaction_id'] == '$TX')")"

UPGRADED=$(curl -s -X PATCH "$BASE/api/v1/subscriptions/me" "${AUTH[@]}" -d '{"plan_code": "BOTTOMLESS"}')
check "upgrade to Bottomless is unlimited" "None" \
  "$(echo "$UPGRADED" | json 'd["data"]["remaining_credits"]')"

# --- Orders and QR pickup ------------------------------------------------------------------
PRODUCT_ID=$(curl -s "$BASE/api/v1/shops/$SHOP_ID/menu" | json 'd["data"]["items"][0]["id"]')
BODY=$(printf '{"product_id": "%s", "size": "L", "milk": "OAT"}' "$PRODUCT_ID")
ORDER=$(curl -s -X POST "$BASE/api/v1/orders" "${AUTH[@]}" -d "$BODY")

if [[ "$(echo "$ORDER" | json 'd["success"]')" != "True" ]]; then
  check "closed shop refuses orders" "SHOP_CLOSED" "$(echo "$ORDER" | json 'd["error"]["code"]')"
  echo "  skip order flow (shop is closed; set ENFORCE_OPENING_HOURS=false to test at night)"
else
  check "order placed" "PENDING" "$(echo "$ORDER" | json 'd["data"]["status"]')"
  ORDER_ID=$(echo "$ORDER" | json 'd["data"]["id"]')
  QR=$(echo "$ORDER" | json 'd["data"]["qr_payload"]')

  # The nearest shop (Karaköy Brew Lab) belongs to the seeded owner +905550000012.
  curl -s -X POST "$BASE/api/v1/auth/register" -H 'content-type: application/json' \
    -d '{"phone_number": "05550000012"}' >/dev/null
  OWNER_TOKEN=$(curl -s -X POST "$BASE/api/v1/auth/verify-otp" -H 'content-type: application/json' \
    -d '{"phone_number": "05550000012", "code": "1234"}' | json 'd["data"]["access_token"]')
  OWNER=(-H "Authorization: Bearer $OWNER_TOKEN" -H 'content-type: application/json')

  check "order in the shop's queue" "True" "$(curl -s "$BASE/api/v1/orders/incoming" "${OWNER[@]}" \
    | json "any(o['id'] == '$ORDER_ID' for o in d['data'])")"
  for STATUS in ACCEPTED PREPARING READY; do
    check "shop marks order $STATUS" "$STATUS" "$(curl -s -X PATCH "$BASE/api/v1/orders/$ORDER_ID/status" \
      "${OWNER[@]}" -d "{\"status\": \"$STATUS\"}" | json 'd["data"]["status"]')"
  done
  SCAN=$(python3 -c 'import json,sys; print(json.dumps({"qr_payload": sys.argv[1]}))' "$QR")
  check "QR scan completes pickup" "COMPLETED" "$(curl -s -X POST "$BASE/api/v1/orders/verify-qr" \
    "${OWNER[@]}" -d "$SCAN" | json 'd["data"]["status"]')"
  check "QR cannot be reused" "ALREADY_COMPLETED" "$(curl -s -X POST "$BASE/api/v1/orders/verify-qr" \
    "${OWNER[@]}" -d "$SCAN" | json 'd["error"]["code"]')"
fi

echo "All $pass checks passed."
