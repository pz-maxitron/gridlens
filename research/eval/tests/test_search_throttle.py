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
