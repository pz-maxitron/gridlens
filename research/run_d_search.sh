#!/bin/bash
# Run Approach D search pipeline for each country+tool combination, skipping
# pairs already recorded in the .done file. Usage: bash run_d_search.sh <BATCH_ID> <country> [<country> ...]
set -u
cd /home/gmk/code/plexos-catalogue-web || exit 1
BATCH_ID="${1:?Usage: bash research/run_d_search.sh <BATCH_ID> <country> [<country> ...]}"
TOOLS="PLEXOS PyPSA PROMOD Bid3 SDDP"
mkdir -p research/logs/d
for country in "${@:2}"; do
  for tool in $TOOLS; do
    done_file="research/logs/d/${BATCH_ID}.done"
    if grep -qF "${country}|${tool}" "$done_file" 2>/dev/null; then
      echo "SKIP ${country}/${tool} (already done)"
      continue
    fi
    safe_country=$(echo "$country" | sed 's/[^a-zA-Z0-9]/_/g')
    log_file="research/logs/d/${BATCH_ID}_${safe_country}_${tool}.log"
    rc=99
    timeout 60m ~/.cache/gridlens-eval-venv/bin/python research/eval/approach_d.py "$BATCH_ID" "$country" "$tool" 2>&1 | tee "$log_file"
    rc=${PIPESTATUS[0]:-$?}
    echo "${country}/${tool} rc=${rc}"
    if [ "$rc" -eq 0 ]; then
      printf '%s\n' "${country}|${tool}" >> "$done_file"
    fi
  done
done
