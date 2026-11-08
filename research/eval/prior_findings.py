#!/usr/bin/env python3
"""Summarize what approach B found/tried for one country+tool, for the
critique pass (approach C) to build on. Usage: prior_findings.py <country> <tool>"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
country, tool = sys.argv[1], sys.argv[2]
path = ROOT / "data/raw/eval/EVAL-B.jsonl"
lines = []
if path.exists():
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("country_label") != country or r.get("tool_name") != tool:
            continue
        if r.get("status") == "gap_confirmed":
            lines.append(f"- NOTHING FOUND by the first pass. Its notes on what it tried: {r.get('notes', '')[:600]}")
        else:
            lines.append(f"- {r.get('institution_name')} ({r.get('institution_category')}, {r.get('role')}, "
                         f"{r.get('status')}) -- source: {r.get('source_url')}")
print("\n".join(lines) if lines else "- The first pass wrote nothing (it may have crashed). Treat every stakeholder type as uncovered.")
