#!/bin/bash
# Blind search-method evaluation: B (current agent prompt) vs C (B + critique
# pass) vs D (retrieval-first pipeline). 3 countries x 4 tools (SDDP
# excluded). Runs only after the main MTS1-A pipeline has stopped (single
# local Qwen slot -- nothing may run concurrently), interleaves the variants
# per (country, tool) so partial results stay comparable, then runs the
# independent validator pass and scores everything against the hidden
# catalogue. Does NOT resume the main search afterwards -- that waits for the
# results review.
#
# Usage: bash research/eval/run_eval.sh [main_driver_pid_to_wait_for]
set -u
shopt -u patsub_replacement 2>/dev/null || true  # bash>=5.2: '&' in ${x//a/b} replacements must stay literal ("Bain & Company")
WAIT_PID="${1:-}"
cd ~/code/plexos-catalogue-web || exit 1
mkdir -p research/logs/eval data/raw/eval
TIMES=research/logs/eval/timings.csv
[ -f "$TIMES" ] || echo "variant,country,tool,start,end,rc" > "$TIMES"

if [ -n "$WAIT_PID" ]; then
  echo "=== waiting for main pipeline (PID $WAIT_PID) to stop at $(date) ==="
  while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 30; done
fi
sleep 20
while pgrep -f "hermes -p implementer chat" >/dev/null; do
  echo "an implementer session is still running -- waiting"; sleep 30
done
echo "=== evaluation starting at $(date) ==="

source research/tool_hints.sh
COUNTRIES=("Germany" "Chile" "Ghana")
EVAL_TOOLS=("PLEXOS" "PyPSA" "PROMOD" "Bid3")
TEMPLATE_B=$(cat research/COUNTRY_TOOL_SEARCH_PROMPT.md)
TEMPLATE_C=$(cat research/eval/CRITIQUE_PROMPT.md)
BLIND_NOTE="**BLIND METHOD TEST.** Do not open or read any file in this repository other than
running scripts/research_helpers.py exactly as instructed -- in particular nothing under
data/ or research/. Do not use gridlens.org, esm-usage-catalog, or any GitHub copy of the
GridLens dataset as a source: they list the answers being tested, and the helper rejects them."
DPY=~/.cache/gridlens-eval-venv/bin/python

already_done() {  # variant country tool
  python3 - "$1" "$2" "$3" <<'PYEOF'
import csv, sys
v, c, t = sys.argv[1:]
try:
    rows = list(csv.DictReader(open("research/logs/eval/timings.csv")))
except FileNotFoundError:
    rows = []
print("yes" if any(r["variant"] == v and r["country"] == c and r["tool"] == t for r in rows) else "no")
PYEOF
}

run_step() {  # variant country tool timeout -- command...
  local V="$1" C="$2" T="$3" TO="$4"; shift 5
  if [ "$(already_done "$V" "$C" "$T")" = "yes" ]; then
    echo "--- $V $C/$T already done, skipping ---"; return
  fi
  local SAFE; SAFE=$(echo "$C" | tr -c 'A-Za-z0-9' '_' | sed 's/_*$//')
  local LOG="research/logs/eval/${V}_${SAFE}_${T}.log"
  echo "--- $V $C/$T starting at $(date) ---"
  local S; S=$(date +%s)
  timeout "$TO" "$@" > "$LOG" 2>&1
  local RC=$?
  echo "$V,$C,$T,$S,$(date +%s),$RC" >> "$TIMES"
  echo "--- $V $C/$T finished rc=$RC at $(date) ---"
}

for COUNTRY in "${COUNTRIES[@]}"; do
  for TOOL in "${EVAL_TOOLS[@]}"; do
    # B -- the current production prompt, blind
    P="${TEMPLATE_B//\{COUNTRY\}/$COUNTRY}"
    P="${P//\{BATCH_ID\}/EVAL-B}"
    P="${P//\{TOOL\}/$TOOL}"
    P="${P//\{TOOL_NOTE\}/${TOOL_NOTE[$TOOL]}}"
    P="${P//\{TOOL_HINT\}/${TOOL_HINT[$TOOL]}}"
    P="${P//\{TOOL_CONTEXT\}/${TOOL_CONTEXT[$TOOL]}}"
    run_step B "$COUNTRY" "$TOOL" 40m -- hermes -p implementer chat -q "$BLIND_NOTE

$P"

    # C -- critique pass layered on B's result
    PRIOR=$(python3 research/eval/prior_findings.py "$COUNTRY" "$TOOL")
    P="${TEMPLATE_C//\{COUNTRY\}/$COUNTRY}"
    P="${P//\{BATCH_ID\}/EVAL-C}"
    P="${P//\{TOOL\}/$TOOL}"
    P="${P//\{TOOL_NOTE\}/${TOOL_NOTE[$TOOL]}}"
    P="${P//\{TOOL_CONTEXT\}/${TOOL_CONTEXT[$TOOL]}}"
    P="${P//\{BLIND_NOTE\}/$BLIND_NOTE}"
    P="${P//\{PRIOR_FINDINGS\}/$PRIOR}"
    run_step C "$COUNTRY" "$TOOL" 30m -- hermes -p implementer chat -q "$P"

    # D -- fully independent retrieval pipeline
    run_step D "$COUNTRY" "$TOOL" 60m -- "$DPY" research/eval/approach_d.py EVAL-D "$COUNTRY" "$TOOL"
  done
done
echo "=== search phase done at $(date) ==="

# Contamination check: did any agent session open the dataset anyway? (The
# blind note itself is echoed into every log, so only look for actual file
# paths of the answer key, which the prompts never mention.)
echo "=== contamination check ==="
grep -lE "catalogue\.jsonl|known_institutions|data/raw" research/logs/eval/[BC]_*.log 2>/dev/null \
  | sed 's/^/POSSIBLY CONTAMINATED: /' || echo "none found"

bash research/eval/validate_eval.sh
python3 research/eval/score_eval.py
echo "=== evaluation complete at $(date) -- main search NOT resumed (awaiting review) ==="
