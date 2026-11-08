#!/bin/bash
# Per-country driver for the GridLens multi-tool search. Replaces the old
# one-continuous-session-per-batch approach: that let context grow
# across 30+ countries in a single session, which both slowed the model
# down progressively and meant a crash lost everything back to the last
# completed country (observed: one crash lost 1h+ of work with zero
# findings written). This runs one FRESH hermes session per country, so
# context stays small and fast throughout, and any single failure only
# costs one country.
#
# Usage: bash run_per_country_search.sh <BATCH_ID>   e.g. MTS1-A
set -u
BATCH_ID="${1:?Usage: run_per_country_search.sh <BATCH_ID>}"
cd ~/code/plexos-catalogue-web || exit 1
mkdir -p research/logs/countries

TEMPLATE=$(cat research/COUNTRY_SEARCH_PROMPT.md)

# Countries for this batch, in checklist order, still not_started.
mapfile -t COUNTRIES < <(
  python3 - "$BATCH_ID" <<'PYEOF'
import csv, sys
batch_id = sys.argv[1]
batch_countries = set()
with open("research/country_batch_map.csv") as f:
    for row in csv.DictReader(f):
        if row["batch_id"] == batch_id:
            batch_countries.add(row["country"])

with open("research/multi_tool_search_checklist.csv") as f:
    for row in csv.DictReader(f):
        if row["country"] in batch_countries and row["overall_status"] == "not_started":
            print(row["country"])
PYEOF
)

echo "=== $BATCH_ID: ${#COUNTRIES[@]} countries remaining at $(date) ==="

for COUNTRY in "${COUNTRIES[@]}"; do
  SAFE_NAME=$(echo "$COUNTRY" | tr -c 'A-Za-z0-9' '_')
  LOG="research/logs/countries/${BATCH_ID}_${SAFE_NAME}.log"
  echo "=== Starting ${COUNTRY} (${BATCH_ID}) at $(date) ==="

  PROMPT="${TEMPLATE//\{COUNTRY\}/$COUNTRY}"
  PROMPT="${PROMPT//\{BATCH_ID\}/$BATCH_ID}"

  hermes -p implementer chat -q "$PROMPT" > "$LOG" 2>&1
  RC=$?

  if [ $RC -ne 0 ]; then
    echo "=== ${COUNTRY} exited with code $RC at $(date) -- check $LOG ==="
  else
    echo "=== Finished ${COUNTRY} at $(date) ==="
  fi
done

echo "=== $BATCH_ID: all remaining countries processed at $(date) ==="
