#!/bin/bash
# Deep-dive driver: after the region-level pass marks a country "done",
# check if it turned up enough confirmed/candidate entries to suggest a
# single broad per-tool search undercounted a large/complex market (the
# dynamic trigger the user asked for, instead of a fixed country list).
# If so, run ONE additional targeted session for that country using
# grid-operator/regional-structure search instead of a flat country-wide
# search. Tracks which countries have already had a deep dive so re-runs
# don't repeat it.
#
# Usage: bash run_deep_dive_search.sh <BATCH_ID> [THRESHOLD]
set -u
BATCH_ID="${1:?Usage: run_deep_dive_search.sh <BATCH_ID> [THRESHOLD]}"
THRESHOLD="${2:-15}"
cd ~/code/plexos-catalogue-web || exit 1
mkdir -p research/logs/deep_dive
DONE_MARKER="research/.deep_dive_done"
touch "$DONE_MARKER"

TEMPLATE=$(cat research/DEEP_DIVE_SEARCH_PROMPT.md)

mapfile -t CANDIDATES < <(
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
        if row["country"] in batch_countries and row["overall_status"] == "done":
            print(row["country"])
PYEOF
)

echo "=== $BATCH_ID: ${#CANDIDATES[@]} done countries to check for deep-dive at $(date) ==="

for COUNTRY in "${CANDIDATES[@]}"; do
  MARKER_KEY="${BATCH_ID}|${COUNTRY}"
  if grep -qxF "$MARKER_KEY" "$DONE_MARKER" 2>/dev/null; then
    continue
  fi

  COUNT=$(python3 scripts/research_helpers.py "$BATCH_ID" count "$COUNTRY" 2>/dev/null)
  if ! [[ "$COUNT" =~ ^[0-9]+$ ]]; then
    echo "WARNING: could not get count for '$COUNTRY' -- skipping"
    continue
  fi

  if [ "$COUNT" -lt "$THRESHOLD" ]; then
    echo "$MARKER_KEY" >> "$DONE_MARKER"
    continue
  fi

  SAFE_NAME=$(echo "$COUNTRY" | tr -c 'A-Za-z0-9' '_' | sed 's/_*$//')
  LOG="research/logs/deep_dive/${BATCH_ID}_${SAFE_NAME}.log"
  echo "=== Deep dive: '${COUNTRY}' (count=${COUNT} >= ${THRESHOLD}) at $(date) ==="

  PROMPT="${TEMPLATE//\{COUNTRY\}/$COUNTRY}"
  PROMPT="${PROMPT//\{BATCH_ID\}/$BATCH_ID}"
  PROMPT="${PROMPT//\{EXISTING_COUNT\}/$COUNT}"

  hermes -p implementer chat -q "$PROMPT" > "$LOG" 2>&1
  RC=$?
  echo "$MARKER_KEY" >> "$DONE_MARKER"

  if [ $RC -ne 0 ]; then
    echo "=== deep dive '${COUNTRY}' exited with code $RC at $(date) -- check $LOG ==="
  else
    echo "=== Finished deep dive '${COUNTRY}' at $(date) ==="
  fi
done

echo "=== $BATCH_ID: deep-dive pass complete at $(date) ==="
