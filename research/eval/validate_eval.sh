#!/bin/bash
# Independent verification of every confirmed/candidate row found by the
# eval variants (B, C, D), using the validator profile (local Qwen). Rows
# are anonymized (no id/batch_id/notes -- the validator can't tell which
# method produced them) and processed in shuffled order. Resumable: rows
# that already have a verdict are skipped.
set -u
cd ~/code/plexos-catalogue-web || exit 1

VALIDATOR_PROFILE="${VALIDATOR_PROFILE:-validator}"
VERDICTS="${VERDICTS:-data/raw/eval/verdicts.jsonl}"
LOG_DIR="research/logs/eval/validator/${VALIDATOR_PROFILE}"
mkdir -p "$LOG_DIR"

# Unique temp file, removed at exit
TMPROWS=$(mktemp)
trap 'rm -f "$TMPROWS"' EXIT

touch "$VERDICTS"

# If command-line args given, treat them as .jsonl file list (relative to repo root)
export VALIDATE_FILES=""
if [ $# -gt 0 ]; then
  VALIDATE_FILES=$(printf '%s:' "$@" | sed 's/:$//')
fi

python3 - <<'PYEOF'
import json, random, os, sys
from pathlib import Path
done = {json.loads(l)["id"] for l in open("data/raw/eval/verdicts.jsonl") if l.strip()}
rows = []
files = os.environ.get("VALIDATE_FILES")
if files:
    for fp in files.split(":"):
        p = Path(fp)
        if p.exists():
            for l in p.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    r = json.loads(l)
                    if r.get("status") in ("confirmed", "candidate") and r["id"] not in done:
                        rows.append(r)
else:
    for v in ("EVAL-B", "EVAL-C", "EVAL-D", "EVAL-D2"):
        p = Path(f"data/raw/eval/{v}.jsonl")
        if p.exists():
            for l in p.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    r = json.loads(l)
                    if r.get("status") in ("confirmed", "candidate") and r["id"] not in done:
                        rows.append(r)
random.seed(7)
random.shuffle(rows)
with open(os.environ["TMPROWS"], "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
PYEOF

echo "=== validating $(wc -l < "$TMPROWS") rows at $(date) ==="
while IFS= read -r ROW; do
  ID=$(echo "$ROW" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
  CLEAN=$(echo "$ROW" | python3 -c '
import json,sys
r=json.load(sys.stdin)
keep=["institution_name","country_label","tool_name","role","use_case","source_url","exact_snippet_or_quote","why_it_supports_the_claim","status"]
print(json.dumps({k:r.get(k) for k in keep}, indent=2, ensure_ascii=False))')
  PROMPT="You are an independent fact-checker. Below is a record claiming an organization
uses (or commissioned / studied with) a specific energy-modelling software tool, with
a cited source URL and a quote. Your ONLY job: open the source_url (web_extract;
if it is a PDF or extraction is truncated, also try a web search for a distinctive
part of the quote) and check whether (1) the quote, or a close equivalent, is really
in the source, and (2) the source really supports that THIS organization is connected
to THIS tool for the stated country.

Do no other research. End your reply with exactly one line, one of:
VERDICT: VERIFIED
VERDICT: QUOTE_NOT_FOUND
VERDICT: URL_UNREACHABLE
VERDICT: WEAK_EVIDENCE
VERDICT: WRONG_ORGANIZATION

Record:
$CLEAN"
  LOG="${LOG_DIR}/${ID}.log"
  timeout 15m hermes -p "$VALIDATOR_PROFILE" chat -q "$PROMPT" > "$LOG" 2>&1
  V=$(grep -oE "VERDICT: *(VERIFIED|QUOTE_NOT_FOUND|URL_UNREACHABLE|WEAK_EVIDENCE|WRONG_ORGANIZATION)" "$LOG" | tail -1 | sed 's/VERDICT: *//')
  [ -z "$V" ] && V="NO_VERDICT"
  python3 -c 'import json,sys; print(json.dumps({"id":sys.argv[1],"verdict":sys.argv[2]}))' "$ID" "$V" >> "$VERDICTS"
  echo "$ID -> $V"
done < "$TMPROWS"
echo "=== validation done at $(date) ==="
