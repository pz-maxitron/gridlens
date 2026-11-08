#!/bin/bash
# Master orchestrator for the GridLens multi-tool search, all 6 batches,
# sequential (one VM = one local-model slot, no real parallelism anyway).
#
# For each batch: run the per-(country,tool) pass (smallest practical
# unit of work -- see run_tool_search.sh), then a deep-dive pass (one
# extra targeted session per country that turned up enough entries to
# suggest a bigger market was undercounted by a flat country-wide search
# -- see run_deep_dive_search.sh).
#
# History of this design, in order:
# 1. One continuous session per 30-46 country mega-batch
#    (research/prompts/MTS1-*.md). Context grew across many countries in
#    one session, slowing generation down progressively; one crash lost
#    everything back to the last completed country -- a real crash lost
#    1h+ of work with zero findings ever written.
# 2. Grouped by UN-M49-style region (3-14 countries per session --
#    run_region_search.sh). Fixed the crash-blast-radius problem, but a
#    region containing one big/rich country still ran 30+ minutes with
#    zero visible progress before finishing even its first country.
# 3. One country per session, all 5 tools (run_per_country_search.sh).
#    Better iteration visibility, but exposed the REAL problem: directly
#    confirmed via log inspection that 3 countries in a row (US, Canada,
#    Mexico) each ran 1-4+ hours and called the helper script's
#    `existing` (read-only) command exactly once, never `add` or `gap` --
#    the model does ALL its research first and plans to write everything
#    at the end, which never arrives before it runs out of time or
#    crashes. Broader session scope gave it more room to defer writing,
#    not less.
# 4. (current) One (country, tool) pair per session
#    (run_tool_search.sh). Smallest possible unit: nothing left to do
#    after finding (or ruling out) ONE tool for ONE country, so writing
#    is the natural last step, not something to defer. `auto_mark`
#    computes checklist status straight from the data once all 5 tools
#    for a country are done -- no LLM call for that bookkeeping either.
set -e
cd ~/code/plexos-catalogue-web
mkdir -p research/logs

for BATCH in MTS1-A MTS1-B MTS1-C MTS1-D MTS1-E MTS1-F; do
  echo "=== $BATCH: per-(country,tool) pass starting at $(date) ==="
  bash research/run_tool_search.sh "$BATCH"
  echo "=== $BATCH: pass done, deep-dive pass starting at $(date) ==="
  bash research/run_deep_dive_search.sh "$BATCH" 15
  echo "=== $BATCH: fully complete at $(date) ==="
done

echo "=== ALL BATCHES COMPLETE at $(date) ==="
