#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:3001}"
DATA_FILE="$(dirname "$0")/machine_product_library_test_data.json"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required. Install jq first." >&2
  exit 1
fi

jq -c '.[]' "$DATA_FILE" | while IFS= read -r row; do
  echo "Seeding: $(echo "$row" | jq -r '.sn_pid')"
  curl -sS -X POST "$BASE_URL/api/v1/productCenter/machineProductLibrary" \
    -H 'Content-Type: application/json' \
    -d "$row" >/dev/null
  echo "  -> done"
done

echo "Seed completed."
