#!/usr/bin/env python3
"""Shared research-recording helpers for the GridLens multi-tool search.

One copy of this script is used by every batch and every country session
-- agents should call it directly instead of writing their own validation/
append logic (that used to cost real time per session for no benefit; this
is the single source of truth for the record schema).

Usage (from repo root):
  python3 scripts/research_helpers.py <BATCH_ID> existing <country>
      - print existing catalogue rows for this country + our 5 tools (dedup check)
  python3 scripts/research_helpers.py <BATCH_ID> add <json-file>
      - validate + append JSON object to data/raw/incoming/<BATCH_ID>.jsonl, print assigned id
  python3 scripts/research_helpers.py <BATCH_ID> gap <country> <tool|ALL> <query-url> <notes>
      - write one gap_confirmed row (institution = tool description placeholder)
  python3 scripts/research_helpers.py <BATCH_ID> mark <country> <P> <Py> <PR> <B> <S>
      - update that country's row in research/multi_tool_search_checklist.csv (values:
        found_confirmed | found_candidate | no_evidence); sets overall_status=done
  python3 scripts/research_helpers.py <BATCH_ID> count <country>
      - print total confirmed+candidate rows for this country (catalogue + all
        incoming/*.jsonl) -- used to decide if a country needs a deep-dive pass
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKLIST = ROOT / "research/multi_tool_search_checklist.csv"
CATALOGUE = ROOT / "data/raw/catalogue.jsonl"
TOOLS = ["PLEXOS", "PyPSA", "PROMOD", "Bid3", "SDDP"]
TOOL_COL = {
    "PLEXOS": "PLEXOS_status", "PyPSA": "PyPSA_status", "PROMOD": "PROMOD_status",
    "Bid3": "Bid3_status", "SDDP": "PSE_SDDP_status",
}
REQUIRED = [
    "institution_name", "institution_category", "official_website",
    "country_label", "tool_name", "tool_category", "tool_explicitly_named",
    "role", "use_case", "decision_type", "decision_basis", "evidence_strength",
    "source_type", "source_title", "source_date", "source_url",
    "exact_snippet_or_quote", "why_it_supports_the_claim", "status",
    "historical_or_current", "batch_id", "notes",
]
CATEGORIES = {
    "utility_iso_rto", "utility_tso", "utility_generation", "utility_distribution",
    "consultancy", "vendor", "academic_research", "think_tank", "industry_association",
    "government_agency", "government_regulator", "international_body", "development_bank",
    "ngo_foundation", "energy_company_diversified", "project_developer", "other",
}
TOOLCATS = {
    "production_cost_uc", "capacity_expansion", "planning_expansion", "market_simulation",
    "energy_system_optimization", "forecasting", "distribution_planning", "other",
}
ROLES = {
    "direct_user", "commissioner", "consultant_modeler", "research_user",
    "subject_of_study", "qa_reviewer",
}
STATUSES = {"confirmed", "candidate", "rejected", "gap_confirmed"}
TOOLCAT = {
    "PLEXOS": "planning_expansion", "PyPSA": "energy_system_optimization",
    "PROMOD": "planning_expansion", "Bid3": "market_simulation", "SDDP": "planning_expansion",
}
TOOL_DESC = {
    "PLEXOS": "PLEXOS (Energy Exemplar)",
    "PyPSA": "PyPSA (open-source)",
    "PROMOD": "PROMOD IV (Hitachi Energy)",
    "Bid3": "Bid3 (Aurora Energy Research)",
    "SDDP": "PSR SDDP",
}


def incoming_path(batch_id):
    return ROOT / f"data/raw/incoming/{batch_id}.jsonl"


def next_id(batch_id):
    path = incoming_path(batch_id)
    prefix = f"{batch_id}-"
    n = 0
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                i = json.loads(line).get("id", "")
            except json.JSONDecodeError:
                continue
            if i.startswith(prefix):
                m = re.match(rf"{re.escape(prefix)}(\d+)$", i)
                if m:
                    n = max(n, int(m.group(1)))
    return f"{prefix}{n + 1:04d}"


def _validate(r, batch_id, is_gap=False):
    errs = []
    for f in REQUIRED:
        if f not in r:
            errs.append(f"missing field: {f}")
    for f in ("decision_type", "decision_basis"):
        if r.get(f) not in ("", None):
            errs.append(f"{f} must be empty string")
    if r.get("batch_id") != batch_id:
        errs.append(f"batch_id must be {batch_id}")
    if r.get("tool_name") not in TOOLS:
        errs.append(f"bad tool_name: {r.get('tool_name')!r}")
    if r.get("institution_category") not in CATEGORIES:
        errs.append(f"bad institution_category: {r.get('institution_category')!r}")
    if r.get("tool_category") not in TOOLCATS:
        errs.append(f"bad tool_category: {r.get('tool_category')!r}")
    if r.get("role") not in ROLES:
        errs.append(f"bad role: {r.get('role')!r}")
    if r.get("status") not in STATUSES:
        errs.append(f"bad status: {r.get('status')!r}")
    if r.get("evidence_strength") not in ("HIGH", "MEDIUM", "LOW"):
        errs.append(f"bad evidence_strength: {r.get('evidence_strength')!r}")
    if r.get("historical_or_current") not in ("current", "historical"):
        errs.append(f"bad historical_or_current: {r.get('historical_or_current')!r}")
    u = r.get("source_url")
    if not (isinstance(u, str) and u.startswith("http")):
        errs.append(f"source_url must be a real http(s) URL, got: {u!r}")
    if not isinstance(r.get("tool_explicitly_named"), bool):
        errs.append("tool_explicitly_named must be bool")
    if not is_gap and r.get("status") == "confirmed" and not r.get("exact_snippet_or_quote"):
        errs.append("confirmed row has no quote")
    if not is_gap and not r.get("institution_name"):
        errs.append("institution_name required (non-gap)")
    return errs


def _append(r, batch_id):
    rid = next_id(batch_id)
    r["id"] = rid
    path = incoming_path(batch_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rid


def cmd_existing(country):
    if not CATALOGUE.exists():
        print("(catalogue missing)")
        return
    for line in CATALOGUE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("country_label", "").strip() == country and r.get("tool_name", "").strip() in TOOLS:
            print(f"{r.get('tool_name',''):8s} | {r.get('institution_name','')[:80]} | {r.get('status','')} | {r.get('id','')}")


def cmd_add(batch_id, json_path):
    r = json.loads(Path(json_path).read_text(encoding="utf-8"))
    r.pop("id", None)
    errs = _validate(r, batch_id)
    if errs:
        print("REJECTED: " + "; ".join(errs))
        sys.exit(2)
    rid = _append(r, batch_id)
    print(f"OK {rid} {r['country_label']} / {r['tool_name']} / {r['institution_name'][:60]} [{r['status']}]")


def cmd_gap(batch_id, country, tool, url, notes):
    tools = TOOLS if tool == "ALL" else [tool]
    for t in tools:
        r = {
            "institution_name": TOOL_DESC[t],
            "institution_category": "other",
            "official_website": "",
            "country_label": country,
            "tool_name": t,
            "tool_category": TOOLCAT[t],
            "tool_explicitly_named": False,
            "role": "subject_of_study",
            "use_case": "No evidence found of any organization in this country using this tool.",
            "decision_type": "",
            "decision_basis": "",
            "evidence_strength": "LOW",
            "source_type": "research_finding",
            "source_title": "",
            "source_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "source_url": url,
            "exact_snippet_or_quote": "",
            "why_it_supports_the_claim": "The search recorded at source_url returned no usable evidence for this country+tool combination.",
            "status": "gap_confirmed",
            "historical_or_current": "current",
            "batch_id": batch_id,
            "notes": notes,
        }
        errs = _validate(r, batch_id, is_gap=True)
        if errs:
            print(f"REJECTED gap {t}: " + "; ".join(errs))
            sys.exit(2)
        rid = _append(r, batch_id)
        print(f"OK {rid} {country} / {t} gap_confirmed")


def cmd_count(country):
    """Total confirmed+candidate rows for this country across the merged
    catalogue AND any not-yet-merged incoming/*.jsonl files (so a deep-dive
    decision can be made right after a session finishes, before the next
    merge-batches run)."""
    count = 0
    sources = [CATALOGUE] + sorted((ROOT / "data/raw/incoming").glob("*.jsonl"))
    for path in sources:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (r.get("country_label", "").strip() == country
                    and r.get("tool_name", "").strip() in TOOLS
                    and r.get("status") in ("confirmed", "candidate")):
                count += 1
    print(count)


def cmd_mark(country, *vals):
    overall = vals[-1] if len(vals) == 6 else "done"
    tool_vals = vals[:5]
    lines = CHECKLIST.read_text(encoding="utf-8").splitlines()
    out = []
    done = False
    for ln in lines:
        if ln.split(",")[0] == country:
            parts = ln.split(",")
            assert len(parts) == 8, parts
            for i, v in enumerate(tool_vals, start=2):
                parts[i] = v
            parts[7] = overall
            out.append(",".join(parts))
            done = True
        else:
            out.append(ln)
    CHECKLIST.write_text("\n".join(out) + "\n", encoding="utf-8")
    if not done:
        print("COUNTRY NOT FOUND IN CHECKLIST")
        sys.exit(2)
    print("marked", country, "overall_status=" + overall)


def cmd_auto_mark(country):
    """Compute each tool's checklist status directly from the data (no LLM
    judgment needed): found_confirmed if any confirmed row exists for that
    country+tool, found_candidate if only candidate rows exist, no_evidence
    if a gap_confirmed row exists (a real search completed, genuinely
    nothing found). If a tool has NO row at all (its session crashed
    before writing anything, or hasn't run yet), its existing checklist
    value is left untouched rather than being overwritten to no_evidence
    -- that would wrongly conflate 'never actually searched' with 'searched
    and confirmed negative', and would silently skip a real retry.
    overall_status only becomes 'done' once all 5 tools have SOME
    resolved value (not 'not_started'); otherwise it stays 'not_started'
    so the country is picked up again next time to retry just the
    still-missing tool(s)."""
    best = {t: None for t in TOOLS}  # None | "gap" | "candidate" | "confirmed"
    sources = [CATALOGUE] + sorted((ROOT / "data/raw/incoming").glob("*.jsonl"))
    for path in sources:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("country_label", "").strip() != country:
                continue
            t = r.get("tool_name", "").strip()
            if t not in TOOLS:
                continue
            status = r.get("status")
            rank = {"confirmed": 3, "candidate": 2, "gap_confirmed": 1}.get(status, 0)
            cur_rank = {"confirmed": 3, "candidate": 2, "gap": 1, None: 0}[best[t]]
            if rank == 3:
                best[t] = "confirmed"
            elif rank == 2 and cur_rank < 2:
                best[t] = "candidate"
            elif rank == 1 and cur_rank < 1:
                best[t] = "gap"

    existing_row = None
    for ln in CHECKLIST.read_text(encoding="utf-8").splitlines():
        if ln.split(",")[0] == country:
            existing_row = ln.split(",")
            break
    if existing_row is None:
        print("COUNTRY NOT FOUND IN CHECKLIST")
        sys.exit(2)
    existing_vals = existing_row[2:7]

    status_map = {"confirmed": "found_confirmed", "candidate": "found_candidate", "gap": "no_evidence"}
    vals = []
    for i, t in enumerate(TOOLS):
        if best[t] is not None:
            vals.append(status_map[best[t]])
        else:
            vals.append(existing_vals[i])  # leave untouched -- crashed/not yet run

    overall = "done" if all(v != "not_started" for v in vals) else "not_started"
    cmd_mark(country, *vals, overall)
    print("computed:", dict(zip(TOOLS, vals)), "overall_status=" + overall)


def main():
    batch_id = sys.argv[1]
    cmd = sys.argv[2]
    if cmd == "existing":
        cmd_existing(sys.argv[3])
    elif cmd == "add":
        cmd_add(batch_id, sys.argv[3])
    elif cmd == "gap":
        cmd_gap(batch_id, sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    elif cmd == "mark":
        cmd_mark(sys.argv[3], *sys.argv[4:9])
    elif cmd == "count":
        cmd_count(sys.argv[3])
    elif cmd == "auto_mark":
        cmd_auto_mark(sys.argv[3])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
