#!/bin/bash
# Master orchestrator for the GridLens multi-tool search, all 6 batches,
# sequential (one VM = one local-model slot, no real parallelism anyway).
#
# For each batch: run the region-level pass (small country-groups per
# session, keeps context small and fast -- see run_region_search.sh),
# then a deep-dive pass (one extra targeted session per country that
# turned up enough entries to suggest a bigger market was undercounted
# by a flat country-wide search -- see run_deep_dive_search.sh).
#
# Superseded: the original per-batch single-continuous-session approach
# (research/prompts/MTS1-*.md) let context grow across 30+ countries in
# one session, which both slowed generation down progressively and meant
# one crash lost everything back to the last completed country (a real
# crash lost 1h+ of work with zero findings ever written). Also
# superseded: a strict one-session-per-country split, which was safer
# but repeats per-session setup overhead 200 times with no depth
# advantage for the large handful of countries that actually need it.
set -e
cd ~/code/plexos-catalogue-web
mkdir -p research/logs

for BATCH in MTS1-A MTS1-B MTS1-C MTS1-D MTS1-E MTS1-F; do
  echo "=== $BATCH: region pass starting at $(date) ==="
  bash research/run_region_search.sh "$BATCH"
  echo "=== $BATCH: region pass done, deep-dive pass starting at $(date) ==="
  bash research/run_deep_dive_search.sh "$BATCH" 15
  echo "=== $BATCH: fully complete at $(date) ==="
done

echo "=== ALL BATCHES COMPLETE at $(date) ==="
