#!/usr/bin/env bash
# One-shot test: register -> upgrade ke max -> generate API key -> upload
# dataset penuh -> audit -> CLI run. Jalanin dari root project:
#   bash test_pro_flow.sh
set -e
GW="http://localhost:8080"
EMAIL="demo_$(date +%s)@test.com"
PASS="pass1234"
DATASET_FULL="PetImages - Dataset yang digunakan untuk Demo/PetImages-Free-Subset.zip"

echo "== Register ($EMAIL) =="
T0=$(curl -s -X POST "$GW/api/v1/auth/register" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['access_token'])")

echo "== Upgrade ke max =="
TOKEN=$(curl -s -X POST "$GW/api/v1/auth/upgrade" -H "Authorization: Bearer $T0" -H "Content-Type: application/json" \
  -d '{"plan":"max"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['access_token'])")
echo "token plan sekarang: max (cek manual: decode JWT kalau ragu)"

echo "== Generate API key =="
APIKEY=$(curl -s -X POST "$GW/api/v1/auth/api-keys" -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['api_key'])")
echo "API key: $APIKEY"

echo "== Configure CLI =="
python3 cli/mgs.py configure --key "$APIKEY" --base-url "$GW"

echo "== mgs run (upload + audit + live progress + report + pdf) =="
python3 cli/mgs.py run "$DATASET_FULL" --pdf

echo ""
echo "=== SELESAI ==="
echo "Email akun (buat login browser): $EMAIL / $PASS  (plan: max)"
echo "Login pakai akun ini di localhost:3000 atau localhost:8501 buat cek UI-nya juga."
