#!/bin/bash
# One-time continuation wrapper: the already-running region-search
# process for MTS1-A (PID passed as $1) was launched directly, not
# through run_multi_tool_search.sh, so it won't auto-chain into the
# deep-dive pass or into batches B-F. This waits for it to finish
# naturally (never kills it), then picks up exactly where
# run_multi_tool_search.sh would have: deep-dive for A, then B-F with
# both passes chained normally.
set -e
EXISTING_PID="${1:?Usage: continue_after_existing.sh <PID-of-running-MTS1-A-region-search>}"
cd ~/code/plexos-catalogue-web

echo "=== Waiting for existing MTS1-A region search (PID $EXISTING_PID) to finish at $(date) ==="
while kill -0 "$EXISTING_PID" 2>/dev/null; do
  sleep 30
done
echo "=== MTS1-A region search finished at $(date), starting deep-dive pass ==="

bash research/run_deep_dive_search.sh MTS1-A 15
echo "=== MTS1-A fully complete at $(date) ==="

for BATCH in MTS1-B MTS1-C MTS1-D MTS1-E MTS1-F; do
  echo "=== $BATCH: region pass starting at $(date) ==="
  bash research/run_region_search.sh "$BATCH"
  echo "=== $BATCH: region pass done, deep-dive pass starting at $(date) ==="
  bash research/run_deep_dive_search.sh "$BATCH" 15
  echo "=== $BATCH: fully complete at $(date) ==="
done

echo "=== ALL BATCHES COMPLETE at $(date) ==="
