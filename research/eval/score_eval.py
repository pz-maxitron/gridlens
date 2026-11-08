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


def load(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def tokens(name):
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    acr = set(re.findall(r"\(([a-z0-9&\- ]{2,12})\)", n))
    n = re.sub(r"\(.*?\)", " ", n)
    toks = [t for t in re.sub(r"[^a-z0-9 ]", " ", n).split() if t not in STOP]
    acronym = "".join(t[0] for t in toks) if len(toks) >= 2 else ""
    return set(toks), {a.replace(" ", "") for a in acr} | ({acronym} if acronym else set()), " ".join(toks)


def same_org(a, b):
    ta, aa, sa = tokens(a)
    tb, ab, sb = tokens(b)
    if not sa or not sb:
        return False
    if sa == sb:
        return True
    if (aa & ab) or (sa.replace(" ", "") in ab) or (sb.replace(" ", "") in aa):
        return True
    small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if len(small) >= 2 and small <= big:
        return True
    return difflib.SequenceMatcher(None, sa, sb).ratio() >= 0.85


def orgs(rows):
    out = defaultdict(list)  # (country, tool) -> [row]
    for r in rows:
        if r.get("status") in ("confirmed", "candidate"):
            out[(r["country_label"], r["tool_name"])].append(r)
    return out


def main():
    truth_rows = [r for r in load(ROOT / "data/raw/catalogue.jsonl")
                  if r.get("country_label") in COUNTRIES and r.get("tool_name") in TOOLS
                  and r.get("status") in ("confirmed", "candidate")]
    truth = orgs(truth_rows)
    verdict = {v["id"]: v["verdict"] for v in load(EVAL / "verdicts.jsonl")}
    b, c_add, d = load(EVAL / "EVAL-B.jsonl"), load(EVAL / "EVAL-C.jsonl"), load(EVAL / "EVAL-D.jsonl")
    variants = {"B (agent, current prompt)": b, "C (B + critique pass)": b + c_add, "D (retrieval pipeline)": d}

    timings = list(csv.DictReader(open(ROOT / "research/logs/eval/timings.csv"))) \
        if (ROOT / "research/logs/eval/timings.csv").exists() else []
    minutes = defaultdict(float)
    crashes = defaultdict(int)
    for t in timings:
        m = (int(t["end"]) - int(t["start"])) / 60
        minutes[t["variant"]] += m
        if t["rc"] != "0":
            crashes[t["variant"]] += 1
    var_minutes = {"B (agent, current prompt)": minutes["B"],
                   "C (B + critique pass)": minutes["B"] + minutes["C"],
                   "D (retrieval pipeline)": minutes["D"]}
    var_crash = {"B (agent, current prompt)": crashes["B"],
                 "C (B + critique pass)": crashes["B"] + crashes["C"],
                 "D (retrieval pipeline)": crashes["D"]}

    n_truth = sum(len(v) for v in truth.values())
    lines = ["# Blind search-method evaluation: B vs C vs D", "",
             f"Test countries: {', '.join(COUNTRIES)}. Tools: {', '.join(TOOLS)} (SDDP excluded).",
             f"Ground truth: {n_truth} known organizations from the catalogue (hidden from all methods).", ""]
    summary = []
    detail = []
    for name, rows in variants.items():
        found = orgs(rows)
        hit, novel, n_orgs, verified, judged = 0, 0, 0, 0, 0
        for key in set(truth) | set(found):
            t_names = [r["institution_name"] for r in truth.get(key, [])]
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
            novel_orgs = [u for u in uniq if not any(same_org(u["institution_name"], t) for t in t_names)]
            novel += len(novel_orgs)
            detail.append(f"| {name.split(' ')[0]} | {key[0]} | {key[1]} | "
                          f"{len(matched_truth)}/{len(t_names)} | "
                          f"{'; '.join(matched_truth) or '-'} | "
                          f"{'; '.join(u['institution_name'] + ' [' + verdict.get(u['id'], '?') + ']' for u in novel_orgs) or '-'} |")
        mins = var_minutes[name]
        summary.append((name, hit, n_truth, novel, n_orgs, verified, judged, mins, var_crash[name]))

    lines += ["## Summary", "",
              "| Variant | Recall of known orgs | Novel orgs | Unique orgs | Validator VERIFIED | Minutes | Min per verified row | Crashed sessions |",
              "|---|---|---|---|---|---|---|---|"]
    for name, hit, nt, novel, n_orgs, ver, judged, mins, cr in summary:
        rec = f"{hit}/{nt} ({100 * hit / nt:.0f}%)" if nt else "-"
        vr = f"{ver}/{judged} ({100 * ver / judged:.0f}%)" if judged else "-"
        per = f"{mins / ver:.1f}" if ver else "-"
        lines.append(f"| {name} | {rec} | {novel} | {n_orgs} | {vr} | {mins:.0f} | {per} | {cr} |")
    lines += ["", "Adoption rule (agreed up front): a variant replaces B only if recall improves by >=10 points,",
              "VERIFIED share drops by <=5 points, and minutes per verified finding is <=1.5x B's.", "",
              "## Per country/tool (for manual review of the fuzzy name matching)", "",
              "| Variant | Country | Tool | Known found | Matched known orgs | Novel orgs [validator verdict] |",
              "|---|---|---|---|---|---|"] + detail
    d_stats = load(EVAL / "D_stats.jsonl")
    if d_stats:
        lines += ["", "## Approach D pipeline stats", "", "| Country | Tool | Queries | Engine calls | URLs | Mention tool | Grounded | Rejected (not verbatim) | Written | Min |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for s in d_stats:
            lines.append(f"| {s['country']} | {s['tool']} | {s['queries']} | {s['engine_calls']} | {s['unique_urls']} | "
                         f"{s['hits_mentioning_tool']} | {s['grounded_findings']} | {s['rejected_ungrounded']} | {s['orgs_written']} | {s['minutes']} |")
    text = "\n".join(lines) + "\n"
    (ROOT / "research/eval/RESULTS.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
