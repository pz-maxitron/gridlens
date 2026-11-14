"""Tests for parallel judging and cross-process throttle.

All tests are network-free.  Uses a fake LLM so no external calls are made.
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent.parent  # project root
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/gmk/.hermes/hermes-agent")

import concurrent.futures as cf


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_env():
    """Reset environment so each test starts fresh."""
    for key in ("JUDGE_CONCURRENCY", "D_VARIANT", "LLM_BACKEND"):
        os.environ.pop(key, None)


# ── Test 1: concurrency=2 and =1 produce same findings in same order ──

def test_parallel_judge_same_as_sequential(monkeypatch):
    """Parallel (concurrency=2) and sequential (concurrency=1) produce
    identical findings in identical order when the LLM returns the same answer."""
    import research.eval.approach_d as ad

    # Fake LLM: always returns the same two findings
    findings = [
        {"hit": 0, "institution_name": "Org A", "institution_category": "utility_tso",
         "role": "direct_user", "status": "confirmed",
         "quote": "Org A uses PLEXOS in Germany",
         "use_case": "Grid expansion", "evidence_strength": "HIGH",
         "source_type": "research_finding", "org_country": "Germany",
         "about_country": True, "evidence_kind": "uses_tool",
         "client_or_project": "", "why": "Yes"},
        {"hit": 1, "institution_name": "Org B", "institution_category": "academic_research",
         "role": "research_user", "status": "confirmed",
         "quote": "Org B uses PLEXOS in Germany",
         "use_case": "Analysis", "evidence_strength": "MEDIUM",
         "source_type": "academic_paper", "org_country": "Germany",
         "about_country": True, "evidence_kind": "uses_tool",
         "client_or_project": "", "why": "Yes"},
    ]

    def fake_llm(prompt, max_tokens=4000, think=False):
        return json.dumps({"findings": findings})

    monkeypatch.setattr(ad, "llm", fake_llm)
    monkeypatch.setattr(ad, "grounded", lambda q, t: True)

    # Three hits: first two match findings, third does not
    hits = [
        {"url": "https://a.com", "title": "A", "text": "Org A uses PLEXOS in Germany today"},
        {"url": "https://b.com", "title": "B", "text": "Org B uses PLEXOS in Germany today"},
        {"url": "https://c.com", "title": "C", "text": "Nothing about PLEXOS"},
    ]

    # --- Sequential path (concurrency=1) ---
    os.environ["JUDGE_CONCURRENCY"] = "1"
    # Reload module so the concurrency check picks up "1"
    import importlib
    seq_mod = importlib.reload(ad)
    seq_mod.llm = fake_llm
    seq_mod.grounded = lambda q, t: True

    seq_results = []
    batch = hits[:2]  # JUDGE_BATCH=4, so both hits fit
    for f in seq_mod.judge("Germany", "PLEXOS", batch):
        try:
            h = batch[int(f.get("hit", -1))]
        except (ValueError, IndexError, TypeError):
            continue
        quote = (f.get("quote") or "").strip()
        if not f.get("institution_name") or not seq_mod.grounded(quote, h["text"]):
            continue
        accept, reason, cap_candidate = seq_mod.accept_finding(f, quote, "Germany", "PLEXOS")
        if not accept:
            continue
        names_tool = any(a in quote.lower() for a in seq_mod.ALIASES["PLEXOS"])
        status = "confirmed" if f.get("status") == "confirmed" and names_tool else "candidate"
        seq_results.append((f["institution_name"], status))

    # --- Parallel path (concurrency=2) ---
    os.environ["JUDGE_CONCURRENCY"] = "2"
    par_mod = importlib.reload(ad)
    par_mod.llm = fake_llm
    par_mod.grounded = lambda q, t: True

    par_results = []
    judge_tasks = []
    for i in range(0, len(batch), par_mod.JUDGE_BATCH):
        judge_tasks.append((i, "Germany", "PLEXOS", batch[i:i + par_mod.JUDGE_BATCH]))

    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(par_mod._judge_one, args): args[0] for args in judge_tasks}
        judge_results = {}
        for fut in cf.as_completed(futures):
            idx, batch_findings = fut.result()
            judge_results[idx] = batch_findings

    for idx in sorted(judge_results):
        _, _, _, batch_for_idx = judge_tasks[idx]
        for f in judge_results[idx]:
            try:
                h = batch_for_idx[int(f.get("hit", -1))]
            except (ValueError, IndexError, TypeError):
                continue
            quote = (f.get("quote") or "").strip()
            if not f.get("institution_name") or not par_mod.grounded(quote, h["text"]):
                continue
            accept, reason, cap_candidate = par_mod.accept_finding(f, quote, "Germany", "PLEXOS")
            if not accept:
                continue
            names_tool = any(a in quote.lower() for a in par_mod.ALIASES["PLEXOS"])
            status = "confirmed" if f.get("status") == "confirmed" and names_tool else "candidate"
            par_results.append((f["institution_name"], status))

    # Assertions
    assert par_results == seq_results, (
        f"Parallel ≠ Sequential\n  parallel: {par_results}\n  seq:      {seq_results}"
    )
    assert len(par_results) == 2, f"Expected 2 findings, got {len(par_results)}"
    assert par_results[0] == ("Org A", "confirmed")
    assert par_results[1] == ("Org B", "confirmed")


# ── Test 2: cross-process throttle spacing ──

def test_cross_process_throttle_spacing():
    """Calling the throttle for one engine sleeps at least the configured
    interval on successive calls."""
    from research.eval.search_engines import (
        _cross_process_throttle, _cross_process_cooldown_check,
        THROTTLE, _THROTTLE_DB, _init_throttle_db,
    )

    # Reset DB
    _init_throttle_db()
    conn = sqlite3.connect(str(_THROTTLE_DB))
    conn.execute("DELETE FROM throttle")
    conn.commit()
    conn.close()

    interval = THROTTLE.get("exa", 0.2)

    # Burn history so the second call will see a last_call
    _cross_process_throttle("exa")
    _cross_process_throttle("exa")

    # Time two consecutive calls
    _cross_process_throttle("exa")
    t2 = time.monotonic()
    _cross_process_throttle("exa")
    t3 = time.monotonic()

    elapsed = t3 - t2
    assert elapsed >= interval * 0.5, (
        f"Expected >= {interval * 0.5:.2f}s gap, got {elapsed:.3f}s"
    )


# ── Test 3: cross-process cooldown visibility ──

def test_cross_process_cooldown_visibility():
    """A cooldown set in one process is visible to another via SQLite."""
    from research.eval.search_engines import (
        _cross_process_cooldown_set, _cross_process_cooldown_check,
        _cross_process_consec_inc, _THROTTLE_DB, _init_throttle_db,
    )

    _init_throttle_db()
    conn = sqlite3.connect(str(_THROTTLE_DB))
    conn.execute("DELETE FROM throttle")
    conn.commit()
    conn.close()

    # Parent sets a long cooldown
    _cross_process_consec_inc("test_engine")
    _cross_process_consec_inc("test_engine")  # consec=2
    _cross_process_cooldown_set("test_engine", time.monotonic())

    # Child sees it
    child_code = textwrap.dedent('''
        import sys
        sys.path.insert(0, "/home/gmk/code/gridlens-dev-parallel")
        sys.path.insert(0, "/home/gmk/.hermes/hermes-agent")
        from research.eval.search_engines import _cross_process_cooldown_check
        print(_cross_process_cooldown_check("test_engine"))
    ''')

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(child_code)
        tmp_path = f.name

    proc = subprocess.run(
        [sys.executable, tmp_path],
        capture_output=True, text=True, timeout=10,
    )
    os.unlink(tmp_path)

    child_result = proc.stdout.strip()
    assert child_result == "False", (
        f"Child should see cooldown as active, got: {child_result}"
    )
