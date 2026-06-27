#!/usr/bin/env bash
# Regenerate OpenAPI specs dari running services.
# Jalankan saat docker-compose services sudah up.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$SCRIPT_DIR/openapi"

declare -A SERVICES=(
  ["dataset"]="http://localhost:8001"
  ["audit"]="http://localhost:8002"
  ["analysis"]="http://localhost:8003"
  ["report"]="http://localhost:8004"
)

echo "Generating OpenAPI specs..."

for name in dataset audit analysis report; do
  url="${SERVICES[$name]}/openapi.json"
  out="$OUT_DIR/$name.json"
  if curl -sf --max-time 5 "$url" -o "$out"; then
    echo "  [OK] $name → $out"
  else
    echo "  [SKIP] $name — service tidak dapat dijangkau di $url"
  fi
done

echo "Done. Commit docs/openapi/*.json untuk update specs di repo."
