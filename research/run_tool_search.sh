#!/bin/bash
# Per-(country, tool) driver -- the smallest practical unit of work.
#
# Both earlier approaches (one continuous batch session, one
# region-per-session, one country-per-session) hit the same underlying
# behavioral problem: the local model treats "write immediately" as
# aspirational and actually does ALL its research first, planning to
# write everything at the end -- which never happens, because it either
# runs out of time or crashes first. Observed directly: 3 countries in a
# row (US, Canada, Mexico) each ran 1-4+ hours and called the helper
# script's `existing` (read-only) command exactly once, never `add` or
# `gap`, despite explicit repeated instructions.
#
# Splitting to one tool per session makes writing the natural LAST step
# of a short task instead of something to defer in a long one -- there's
# nothing else left to do after finding (or ruling out) one tool for one
# country, so there's no structural opportunity to keep "doing more
# research first".
#
# After all 5 tools are done for a country, `auto_mark` computes the
# checklist status straight from the data (no LLM call needed for that
# bookkeeping step, so it can't be skipped/forgotten either).
#
# Usage: bash run_tool_search.sh <BATCH_ID>   e.g. MTS1-A
set -u
BATCH_ID="${1:?Usage: run_tool_search.sh <BATCH_ID>}"
cd ~/code/plexos-catalogue-web || exit 1
mkdir -p research/logs/tools

TEMPLATE=$(cat research/COUNTRY_TOOL_SEARCH_PROMPT.md)

TOOLS=("PLEXOS" "PyPSA" "PROMOD" "Bid3" "SDDP")
declare -A TOOL_NOTE
TOOL_NOTE["PLEXOS"]="(Energy Exemplar)."
TOOL_NOTE["PyPSA"]="(the open-source tool)."
TOOL_NOTE["PROMOD"]="(PROMOD IV, Hitachi Energy / formerly ABB)."
TOOL_NOTE["Bid3"]="(Aurora Energy Research)."
TOOL_NOTE["SDDP"]="(PSR Energy Consulting's Stochastic Dual Dynamic Programming tool -- ALSO search \"PSR SDDP\" and \"PSE SDDP\" as variant spellings, since the exact vendor-name spelling is unconfirmed; treat all 3 as the same tool)."

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
  SAFE_COUNTRY=$(echo "$COUNTRY" | tr -c 'A-Za-z0-9' '_' | sed 's/_*$//')
  echo "=== Starting ${COUNTRY} (${BATCH_ID}) at $(date) ==="

  for TOOL in "${TOOLS[@]}"; do
    LOG="research/logs/tools/${BATCH_ID}_${SAFE_COUNTRY}_${TOOL}.log"
    echo "--- ${COUNTRY} / ${TOOL} starting at $(date) ---"

    PROMPT="${TEMPLATE//\{COUNTRY\}/$COUNTRY}"
    PROMPT="${PROMPT//\{BATCH_ID\}/$BATCH_ID}"
    PROMPT="${PROMPT//\{TOOL\}/$TOOL}"
    PROMPT="${PROMPT//\{TOOL_NOTE\}/${TOOL_NOTE[$TOOL]}}"

    hermes -p implementer chat -q "$PROMPT" > "$LOG" 2>&1
    RC=$?
    if [ $RC -ne 0 ]; then
      echo "--- ${COUNTRY} / ${TOOL} exited with code $RC at $(date) -- check $LOG ---"
    else
      echo "--- Finished ${COUNTRY} / ${TOOL} at $(date) ---"
    fi
  done

  # Bookkeeping, no LLM involved -- can't be skipped or forgotten.
  python3 scripts/research_helpers.py "$BATCH_ID" auto_mark "$COUNTRY"
  echo "=== Finished ${COUNTRY} (all 5 tools) at $(date) ==="
done

echo "=== $BATCH_ID: all remaining countries processed at $(date) ==="
