#!/bin/bash
# Region-level driver for the GridLens multi-tool search -- the middle
# ground between the original mega-batch (30-46 countries in one
# continuous session -- context grew too large, one crash lost 1h+ of
# work with zero findings written) and a strict one-country-per-session
# split (very safe, but 200 sessions means repeating setup overhead 200
# times). Groups by the existing `region` column in the checklist (UN
# M49-style sub-regions, e.g. Caribbean=14 countries, North America=3,
# Baltics=3) -- a natural, already-present grouping of a handful of
# countries per session.
#
# Usage: bash run_region_search.sh <BATCH_ID>   e.g. MTS1-A
set -u
BATCH_ID="${1:?Usage: run_region_search.sh <BATCH_ID>}"
cd ~/code/plexos-catalogue-web || exit 1
mkdir -p research/logs/regions

TEMPLATE=$(cat research/REGION_SEARCH_PROMPT.md)

# Regions for this batch, each with its still-not_started countries, in
# checklist order. One line per region: "RegionName|country1,country2,..."
mapfile -t REGION_LINES < <(
  python3 - "$BATCH_ID" <<'PYEOF'
import csv, sys
from collections import OrderedDict

batch_id = sys.argv[1]
batch_countries = set()
with open("research/country_batch_map.csv") as f:
    for row in csv.DictReader(f):
        if row["batch_id"] == batch_id:
            batch_countries.add(row["country"])

regions = OrderedDict()
with open("research/multi_tool_search_checklist.csv") as f:
    for row in csv.DictReader(f):
        if row["country"] in batch_countries and row["overall_status"] == "not_started":
            regions.setdefault(row["region"], []).append(row["country"])

for region, countries in regions.items():
    print(f"{region}|{','.join(countries)}")
PYEOF
)

echo "=== $BATCH_ID: ${#REGION_LINES[@]} regions remaining at $(date) ==="

for LINE in "${REGION_LINES[@]}"; do
  REGION="${LINE%%|*}"
  COUNTRIES_CSV="${LINE#*|}"
  IFS=',' read -r -a COUNTRY_ARR <<< "$COUNTRIES_CSV"

  COUNTRIES_LIST=""
  for C in "${COUNTRY_ARR[@]}"; do
    COUNTRIES_LIST="${COUNTRIES_LIST}- ${C}
"
  done

  SAFE_NAME=$(echo "$REGION" | tr -c 'A-Za-z0-9' '_' | sed 's/_*$//')
  LOG="research/logs/regions/${BATCH_ID}_${SAFE_NAME}.log"
  echo "=== Starting region '${REGION}' (${#COUNTRY_ARR[@]} countries, ${BATCH_ID}) at $(date) ==="

  PROMPT="${TEMPLATE//\{REGION\}/$REGION}"
  PROMPT="${PROMPT//\{BATCH_ID\}/$BATCH_ID}"
  PROMPT="${PROMPT//\{COUNTRIES_LIST\}/$COUNTRIES_LIST}"

  hermes -p implementer chat -q "$PROMPT" > "$LOG" 2>&1
  RC=$?

  if [ $RC -ne 0 ]; then
    echo "=== region '${REGION}' exited with code $RC at $(date) -- check $LOG ==="
  else
    echo "=== Finished region '${REGION}' at $(date) ==="
  fi
done

echo "=== $BATCH_ID: all remaining regions processed at $(date) ==="
