#!/bin/bash
# Master orchestrator for the GridLens multi-tool search, all 6 batches,
# sequential (one VM = one local-model slot, no real parallelism anyway).
#
# For each batch: run the per-country pass (one country per session --
# see run_per_country_search.sh), then a deep-dive pass (one extra
# targeted session per country that turned up enough entries to suggest
# a bigger market was undercounted by a flat country-wide search -- see
# run_deep_dive_search.sh).
#
# History of this design, in order:
# 1. One continuous session per 30-46 country mega-batch
#    (research/prompts/MTS1-*.md). Let context grow across many
#    countries in one session, which slowed generation down
#    progressively and meant one crash lost everything back to the last
#    completed country -- a real crash lost 1h+ of work with zero
#    findings ever written.
# 2. Grouped by UN-M49-style region (3-14 countries per session --
#    run_region_search.sh). Fixed the crash-blast-radius problem, but a
#    region containing one big/rich country (e.g. North America = US +
#    Canada + Mexico) still ran 30+ minutes with zero visible progress
#    before the session finished even its first country -- not enough
#    iteration visibility.
# 3. (current) One country per session (run_per_country_search.sh).
#    Smallest practical unit: a checkpoint/log update after every single
#    country, so progress is visible quickly and any one session running
#    long is obvious fast, not discovered 30+ minutes in.
set -e
cd ~/code/plexos-catalogue-web
mkdir -p research/logs

for BATCH in MTS1-A MTS1-B MTS1-C MTS1-D MTS1-E MTS1-F; do
  echo "=== $BATCH: per-country pass starting at $(date) ==="
  bash research/run_per_country_search.sh "$BATCH"
  echo "=== $BATCH: per-country pass done, deep-dive pass starting at $(date) ==="
  bash research/run_deep_dive_search.sh "$BATCH" 15
  echo "=== $BATCH: fully complete at $(date) ==="
done

echo "=== ALL BATCHES COMPLETE at $(date) ==="
