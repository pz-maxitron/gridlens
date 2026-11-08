#!/bin/bash
# Continues after the standalone per-(country,tool) pass for MTS1-A
# (already running, PID passed as $1) finishes: deep-dive for A, then
# B-F with both passes chained normally.
set -e
EXISTING_PID="${1:?Usage: continue_batch_a_v2.sh <PID-of-running-MTS1-A-tool-search>}"
cd ~/code/plexos-catalogue-web

echo "=== Waiting for MTS1-A per-(country,tool) pass (PID $EXISTING_PID) at $(date) ==="
while kill -0 "$EXISTING_PID" 2>/dev/null; do
  sleep 30
done
echo "=== MTS1-A pass finished at $(date), starting deep-dive ==="

bash research/run_deep_dive_search.sh MTS1-A 15
echo "=== MTS1-A fully complete at $(date) ==="

for BATCH in MTS1-B MTS1-C MTS1-D MTS1-E MTS1-F; do
  echo "=== $BATCH: per-(country,tool) pass starting at $(date) ==="
  bash research/run_tool_search.sh "$BATCH"
  echo "=== $BATCH: pass done, deep-dive pass starting at $(date) ==="
  bash research/run_deep_dive_search.sh "$BATCH" 15
  echo "=== $BATCH: fully complete at $(date) ==="
done

echo "=== ALL BATCHES COMPLETE at $(date) ==="
