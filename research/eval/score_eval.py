#!/usr/bin/env python3
"""Score the blind method evaluation (B vs C vs D) against the known catalogue.

Ground truth = confirmed/candidate catalogue rows for the test countries and
tools (the catalogue was hidden from every method during the test).

Metrics per variant:
  reach     recall of known organizations + novel organizations (not in truth)
  quality   validator VERIFIED share of confirmed/candidate rows
  cost      minutes, minutes per verified organization, crashed sessions
Writes research/eval/RESULTS.md and prints it. Name matching is fuzzy, so the
full match table is included for manual review.
"""
import argparse
import csv
import difflib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "data/raw/eval"
COUNTRIES = ["Germany", "Chile", "Ghana"]
TOOLS = ["PLEXOS", "PyPSA", "PROMOD", "Bid3"]
STOP = {"the", "of", "and", "for", "gmbh", "ag", "sa", "s", "a", "ltd", "limited", "inc", "co",
        "company", "plc", "llc", "de", "del", "la", "y", "und", "fur", "fuer", "e", "v", "ev"}

# The page was removed; no method can find these
DEAD_TRUTH_SOURCES = ["energyexemplar.com/our-company/clients"]


def load(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _all_names(name):
    """Return the name and all parentheticals as alternative full names."""
    return [name] + re.findall(r"\(([^)]+)\)", name)


def tokens(name):
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    acr = set(re.findall(r"\(([a-z0-9&\- ]{2,12})\)", n))
    n = re.sub(r"\(.*?\)", " ", n)
    toks = [t for t in re.sub(r"[^a-z0-9 ]", " ", n).split() if t not in STOP]
    acronym = "".join(t[0] for t in toks) if len(toks) >= 2 else ""
    return set(toks), {a.replace(" ", "") for a in acr} | ({acronym} if acronym else set()), " ".join(toks)


def _tokens_match(sa, sb, aa, ab, ta, tb):
    """Return True if two tokenised org-name pairs match."""
    if not sa or not sb:
        return False
    if sa == sb:
        return True
    if (aa & ab) or (sa.replace(" ", "") in ab) or (sb.replace(" ", "") in aa):
        return True
    small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if len(small) >= 2 and small <= big:
        return True
    if difflib.SequenceMatcher(None, sa, sb).ratio() >= 0.85:
        return True
    return False


def same_org(a, b):
    """Check whether two organisation names refer to the same org.

    Text inside parentheses also counts as an alternative full name of that
    organization (match if same_org(inner, other) is true for any parenthetical,
    either side).
    """
    ta, aa, sa = tokens(a)
    tb, ab, sb = tokens(b)
    if _tokens_match(sa, sb, aa, ab, ta, tb):
        return True
    # Check parentheticals on both sides
    for na in _all_names(a):
        for nb in _all_names(b):
            tna, aca, sna = tokens(na)
            tnb, acb, snb = tokens(nb)
            if _tokens_match(sna, snb, aca, acb, tna, tnb):
                return True
    return False


def orgs(rows):
    out = defaultdict(list)  # (country, tool) -> [row]
    for r in rows:
        if r.get("status") in ("confirmed", "candidate"):
            out[(r["country_label"], r["tool_name"])].append(r)
    return out


def compute_metrics(variant_name, rows, truth, verdict, n_truth, n_truth_reachable):
    """Compute summary metrics for one variant."""
    found = orgs(rows)
    hit, hit_reachable, novel, n_orgs, verified, judged = 0, 0, 0, 0, 0, 0

    for key in set(truth) | set(found):
        t_names = [r["institution_name"] for r in truth.get(key, [])]
        t_names_reachable = [
            r["institution_name"] for r in truth.get(key, [])
            if not any(d in r.get("source_url", "") for d in DEAD_TRUTH_SOURCES)
        ]
        f_rows = found.get(key, [])
        # unique orgs found
        uniq = []
        for r in f_rows:
            if not any(same_org(r["institution_name"], u["institution_name"]) for u in uniq):
                uniq.append(r)
        n_orgs += len(uniq)
        for r in rows:
            if (r["country_label"], r["tool_name"]) == key and r.get("status") in ("confirmed", "candidate"):
                if r["id"] in verdict and verdict[r["id"]] != "NO_VERDICT":
                    judged += 1
                    verified += verdict[r["id"]] == "VERIFIED"
        matched_truth = [t for t in t_names if any(same_org(t, u["institution_name"]) for u in uniq)]
        hit += len(matched_truth)
        matched_reachable = [t for t in t_names_reachable if any(same_org(t, u["institution_name"]) for u in uniq)]
        hit_reachable += len(matched_reachable)
        novel_orgs = [u for u in uniq if not any(same_org(u["institution_name"], t) for t in t_names)]
        novel += len(novel_orgs)

    return hit, hit_reachable, n_truth, n_truth_reachable, novel, n_orgs, verified, judged


def main():
    parser = argparse.ArgumentParser(description="Score eval variants")
    parser.add_argument("--verdicts", default="data/raw/eval/verdicts.jsonl",
                        help="Path to verdicts JSONL")
    parser.add_argument("--out", default="research/eval/RESULTS.md",
                        help="Output RESULTS.md path")
    args = parser.parse_args()
    verdicts_path = Path(args.verdicts) if not Path(args.verdicts).is_absolute() else Path(args.verdicts)
    out_path = Path(args.out) if not Path(args.out).is_absolute() else Path(args.out)

    verdict = {v["id"]: v["verdict"] for v in load(verdicts_path)}

    # Load all variant data files
    b = load(EVAL / "EVAL-B.jsonl")
    c_add = load(EVAL / "EVAL-C.jsonl")
    d = load(EVAL / "EVAL-D.jsonl")
    d2 = load(EVAL / "EVAL-D2.jsonl")
    d3 = load(EVAL / "EVAL-D3.jsonl")
    d4 = load(EVAL / "EVAL-D4.jsonl")
    d4_name = "D4 (perspectives + documents + attribution check)"
    o2 = load(EVAL / "EVAL-O2.jsonl")
    o3 = load(EVAL / "EVAL-O3.jsonl")
    o4 = load(EVAL / "EVAL-O4.jsonl")

    # Map: display_name -> data
    variants = {}
    _variant_map = {
        "B (agent, current prompt)": b,
        "C (B + critique pass)": b + c_add,
        "D (retrieval pipeline)": d,
        "D2 (pipeline + country check)": d2,
        "D3 (pipeline + evidence-kind filter)": d3,
        d4_name: d4,
        "D2 on Opus 5.5": o2,
        "D3 on Opus 5.5": o3,
        "D4 on Opus 5.5": o4,
    }
    for name, data in _variant_map.items():
        if data:  # skip missing files
            variants[name] = data

    # Truth
    truth_rows = [r for r in load(ROOT / "data/raw/catalogue.jsonl")
                  if r.get("country_label") in COUNTRIES and r.get("tool_name") in TOOLS
                  and r.get("status") in ("confirmed", "candidate")]
    truth = orgs(truth_rows)
    n_truth = sum(len(v) for v in truth.values())

    # Reachable truth (exclude dead sources)
    truth_reachable = [r for r in truth_rows
                       if not any(d in r.get("source_url", "") for d in DEAD_TRUTH_SOURCES)]
    truth_reachable_keys = orgs(truth_reachable)
    n_truth_reachable = sum(len(v) for v in truth_reachable_keys.values())

    # Timings from CSV
    timings = list(csv.DictReader(open(ROOT / "research/logs/eval/timings.csv"))) \
        if (ROOT / "research/logs/eval/timings.csv").exists() else []
    minutes = defaultdict(float)
    crashes = defaultdict(int)
    for t in timings:
        m = (int(t["end"]) - int(t["start"])) / 60
        minutes[t["variant"]] += m
        if t["rc"] != "0":
            crashes[t["variant"]] += 1

    # Map variant display names to timing/crash keys
    _timing_map = {
        "B (agent, current prompt)": ("B", "B"),
        "C (B + critique pass)": ("B_C", "B_C"),
        "D (retrieval pipeline)": ("D", "D"),
        "D2 (pipeline + country check)": ("D2", "D2"),
        "D3 (pipeline + evidence-kind filter)": ("D3", "D3"),
        d4_name: ("D4", "D4"),
        "D2 on Opus 5.5": ("O2", "O2"),
        "D3 on Opus 5.5": ("O3", "O3"),
        "D4 on Opus 5.5": ("O4", "O4"),
    }

    def _get_mins(vname):
        k = _timing_map.get(vname, (vname, vname))
        if k[0] == "B_C":
            return minutes["B"] + minutes["C"]
        return minutes[k[0]]

    def _get_crash(vname):
        k = _timing_map.get(vname, (vname, vname))
        if k[0] == "B_C":
            return crashes["B"] + crashes["C"]
        return crashes[k[0]]

    lines = ["# Blind search-method evaluation: B vs C vs D", "",
             f"Test countries: {', '.join(COUNTRIES)}. Tools: {', '.join(TOOLS)} (SDDP excluded).",
             f"Ground truth: {n_truth} known organizations from the catalogue (hidden from all methods).",
             f"Dead sources excluded from reachable recall: {DEAD_TRUTH_SOURCES}", ""]
    summary = []
    detail = []
    for name, rows in variants.items():
        hit, hit_reachable, nt, ntr, novel, n_orgs, verified, judged = \
            compute_metrics(name, rows, truth, verdict, n_truth, n_truth_reachable)
        mins = _get_mins(name)
        crash = _get_crash(name)
        summary.append((name, hit, nt, hit_reachable, ntr, novel, n_orgs, verified, judged, mins, crash))

        # Per-country/tool detail
        found = orgs(rows)
        for key in sorted(set(truth) | set(found)):
            t_names = [r["institution_name"] for r in truth.get(key, [])]
            t_names_reachable = [
                r["institution_name"] for r in truth.get(key, [])
                if not any(d in r.get("source_url", "") for d in DEAD_TRUTH_SOURCES)
            ]
            f_rows = found.get(key, [])
            uniq = []
            for r in f_rows:
                if not any(same_org(r["institution_name"], u["institution_name"]) for u in uniq):
                    uniq.append(r)
            matched_truth = [t for t in t_names if any(same_org(t, u["institution_name"]) for u in uniq)]
            novel_orgs = [u for u in uniq if not any(same_org(u["institution_name"], t) for t in t_names)]
            detail.append(f"| {name.split(' ')[0]} | {key[0]} | {key[1]} | "
                          f"{len(matched_truth)}/{len(t_names)} | "
                          f"{'; '.join(matched_truth) or '-'} | "
                          f"{'; '.join(u['institution_name'] + ' [' + verdict.get(u['id'], '?') + ']' for u in novel_orgs) or '-'} |")

    lines += ["## Summary", "",
              "| Variant | Recall of known orgs | Recall (reachable) | Novel orgs | Unique orgs | Validator VERIFIED | Minutes | Min per verified row | Crashed sessions |",
              "|---|---|---|---|---|---|---|---|---|"]
    for name, hit, nt, hit_reach, ntr, novel, n_orgs, ver, judged, mins, cr in summary:
        rec = f"{hit}/{nt} ({100 * hit / nt:.0f}%)" if nt else "-"
        rec_r = f"{hit_reach}/{ntr} ({100 * hit_reach / ntr:.0f}%)" if ntr else "-"
        vr = f"{ver}/{judged} ({100 * ver / judged:.0f}%)" if judged else "-"
        per = f"{mins / ver:.1f}" if ver else "-"
        lines.append(f"| {name} | {rec} | {rec_r} | {novel} | {n_orgs} | {vr} | {mins:.0f} | {per} | {cr} |")
    lines += ["", "Adoption rule (agreed up front): a variant replaces B only if recall improves by >=10 points,",
              "VERIFIED share drops by <=5 points, and minutes per verified finding is <=1.5x B's.", "",
              "## Per country/tool (for manual review of the fuzzy name matching)", "",
              "| Variant | Country | Tool | Known found | Matched known orgs | Novel orgs [validator verdict] |",
              "|---|---|---|---|---|---|"] + detail
    d_stats = load(EVAL / "D_stats.jsonl")
    if d_stats:
        lines += ["", "## Approach D pipeline stats", "",
                  "| Batch | Country | Tool | Queries | Engine calls | URLs | Mention tool | Grounded | Rejected (not verbatim) | Written | Min |",
                  "|---|---|---|---|---|---|---|---|---|---|---"]
        for s in d_stats:
            batch = s.get("batch_id", "EVAL-D")
            lines.append(f"| {batch} | {s['country']} | {s['tool']} | {s['queries']} | {s['engine_calls']} | "
                         f"{s['hits_mentioning_tool']} | {s['grounded_findings']} | {s['rejected_ungrounded']} | "
                         f"{s['orgs_written']} | {s['minutes']} |")

    text = "\n".join(lines) + "\n"
    out_path.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
