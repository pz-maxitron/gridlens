"""Throttled, rotating, cached multi-engine search layer (~250 lines)."""
import hashlib, json, os, re, sqlite3, sys, threading, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
ENGINES = ["parallel", "keenable", "exa", "ddgs", "searxng"]
THROTTLE = {"parallel": 0.5, "keenable": 1.0, "exa": 2.0, "ddgs": 2.0, "searxng": 1.0, "openalex": 1.0}
CACHE_PATH = Path.home() / ".cache/gridlens-search-cache.sqlite"
COOLDOWN_DB = Path.home() / ".cache/gridlens-search-cache.sqlite"
CACHE_TTL = 30 * 86400
LOG_PATH = Path("data/raw/eval/engine_log.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Cross-process throttle / cooldown via SQLite ────────────────────────────
# Each engine's last-call timestamp and cooldown-until are stored here so that
# multiple pipelines together never exceed one pipeline's rate per engine.
_THROTTLE_DB = Path.home() / ".cache/gridlens-search-cache.sqlite"


def _init_throttle_db():
    """Create the throttle/cooldown/consec table if it does not exist."""
    _THROTTLE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_THROTTLE_DB))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS throttle ("
        "engine TEXT PRIMARY KEY, "
        "last_call REAL, "
        "cooldown_until REAL, "
        "consec_fail INTEGER DEFAULT 0"
        ")"
    )
    conn.commit()
    conn.close()


_init_throttle_db()


def _db():
    """Autocommit connection; callers open BEGIN IMMEDIATE for read-modify-write."""
    return sqlite3.connect(str(_THROTTLE_DB), timeout=30, isolation_level=None)


def _ensure_row(c, engine):
    c.execute("INSERT OR IGNORE INTO throttle (engine, last_call, cooldown_until, consec_fail) "
              "VALUES (?, 0, 0, 0)", (engine,))


# Wall-clock time (not monotonic): the table is shared across processes and
# survives reboots, so values must stay comparable after a restart.
def _cross_process_throttle(engine):
    """Reserve the next call slot for this engine across all processes, then
    sleep until it. One atomic transaction, so concurrent pipelines never share
    a slot."""
    interval = THROTTLE.get(engine, 0.2)
    c = _db()
    try:
        c.execute("BEGIN IMMEDIATE")
        _ensure_row(c, engine)
        last = c.execute("SELECT COALESCE(last_call, 0) FROM throttle WHERE engine=?", (engine,)).fetchone()[0]
        now = time.time()
        slot = max(now, last + interval)
        c.execute("UPDATE throttle SET last_call=? WHERE engine=?", (slot, engine))
        c.execute("COMMIT")
    finally:
        c.close()
    if slot > now:
        time.sleep(slot - now)


def _cross_process_cooldown_check(engine):
    """True if the engine is not on cooldown."""
    c = _db()
    try:
        row = c.execute("SELECT COALESCE(cooldown_until, 0) FROM throttle WHERE engine=?", (engine,)).fetchone()
    finally:
        c.close()
    return not row or row[0] <= time.time()


def _cross_process_cooldown_set(engine, _now=None):
    """Cooldown of 60 s doubling per consecutive failure (counter already
    incremented by the caller), capped at 15 min."""
    c = _db()
    try:
        c.execute("BEGIN IMMEDIATE")
        _ensure_row(c, engine)
        consec = c.execute("SELECT COALESCE(consec_fail, 0) FROM throttle WHERE engine=?", (engine,)).fetchone()[0]
        dur = min(15 * 60, 60 * (2 ** max(consec - 1, 0)))
        c.execute("UPDATE throttle SET cooldown_until=? WHERE engine=?", (time.time() + dur, engine))
        c.execute("COMMIT")
    finally:
        c.close()


def _cross_process_consec_inc(engine):
    c = _db()
    try:
        c.execute("BEGIN IMMEDIATE")
        _ensure_row(c, engine)
        c.execute("UPDATE throttle SET consec_fail = COALESCE(consec_fail, 0) + 1 WHERE engine=?", (engine,))
        c.execute("COMMIT")
    finally:
        c.close()


def _cross_process_consec_reset(engine):
    c = _db()
    try:
        c.execute("UPDATE throttle SET consec_fail = 0 WHERE engine=?", (engine,))
    finally:
        c.close()


def _cross_process_cooldown_clear(engine):
    c = _db()
    try:
        c.execute("UPDATE throttle SET cooldown_until = 0 WHERE engine=?", (engine,))
    finally:
        c.close()

# ── Polite pool ─────────────────────────────────────────────────────────────
_OPENALEX_MAILTO = os.environ.get("OPENALEX_MAILTO")
_OPENALEX_UA = f"gridlens-research (mailto:{_OPENALEX_MAILTO})" if _OPENALEX_MAILTO else "gridlens-research"

# ── State (module-level) ───────────────────────────────────────────────────
_rr = [0]  # round-robin cursor
_locks = {"cd": threading.Lock(), "co": threading.Lock(), "th": threading.Lock(), "lg": threading.Lock()}
_cooldowns: dict[str, float] = {}
_consec: dict[str, int] = {}
_last: dict[str, float] = {}

# ── Cooldown / throttle helpers (cross-process via SQLite) ─────────────────
# These wrappers keep the existing API but delegate to SQLite so two or three
# pipelines together never exceed one pipeline's rate per engine.
def _engine_ok(name):
    return _cross_process_cooldown_check(name)

def _engine_fail(name):
    _cross_process_consec_inc(name)
    _cross_process_cooldown_set(name)

def _engine_okay(name):
    _cross_process_cooldown_clear(name)
    _cross_process_consec_reset(name)

def _throttle(name):
    _cross_process_throttle(name)

# ── Cache ───────────────────────────────────────────────────────────────────
def _ckey(query, limit):
    return hashlib.sha256((" ".join(query.lower().split()) + "|" + str(limit)).encode()).hexdigest()[:16]

def _cache_get(key):
    if not CACHE_PATH.exists():
        return None
    try:
        with sqlite3.connect(str(CACHE_PATH)) as c:
            r = c.execute("SELECT value FROM cache WHERE key=? AND expires>?", (key, time.time())).fetchone()
            return json.loads(r[0]) if r else None
    except Exception:
        return None

def _cache_put(key, value):
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(CACHE_PATH)) as c:
            c.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, expires REAL)")
            c.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (key, json.dumps(value), time.time() + CACHE_TTL))
    except Exception:
        pass

# ── Logging ─────────────────────────────────────────────────────────────────
def _log(engine, query, status, n, secs):
    with _locks["lg"]:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "engine": engine,
                                "query": query, "status": status, "n": n, "secs": round(secs, 2)}) + "\n")

# ── Failure detection ──────────────────────────────────────────────────────
_FAIL_KW = ("429", "rate", "limit", "quota", "no results found")
def _is_fail_msg(msg):
    return any(kw in str(msg).lower() for kw in _FAIL_KW)

# ── Result normaliser ──────────────────────────────────────────────────────
def _norm(res, limit):
    if isinstance(res, dict):
        hits = (res.get("data") or res.get("results") or res)
        if isinstance(hits, dict):
            hits = hits.get("web") or hits.get("results") or []
    elif isinstance(res, list):
        hits = res
    else:
        hits = []
    out = []
    for h in (hits[:limit] if limit else hits):
        if isinstance(h, dict):
            out.append({"url": h.get("url", ""), "title": h.get("title", ""),
                        "text": (h.get("description") or h.get("text") or h.get("snippet") or "")[:2000]})
    return out

# ── Engine wrappers ────────────────────────────────────────────────────────
def _call_keyless(fn, query, limit):
    return fn(query, limit)

def _parallel_fn(q, l):
    sys.path.insert(0, "/home/gmk/.hermes/hermes-agent")
    import plugins.web.keyless_mcp as _web
    return _web.parallel_search_keyless(q, l)

def _keenable_fn(q, l):
    sys.path.insert(0, "/home/gmk/.hermes/hermes-agent")
    import plugins.web.keyless_mcp as _web
    return _web.keenable_search_keyless(q, l)

def _exa_fn(q, l):
    sys.path.insert(0, "/home/gmk/.hermes/hermes-agent")
    import plugins.web.keyless_mcp as _web
    return _web.exa_search_keyless(q, l)

def _ddgs_fn(q, l):
    from ddgs import DDGS
    return DDGS().text(q, max_results=l) or []

_SEARXNG_URL = os.environ.get("GRIDLENS_SEARXNG_URL") or "http://127.0.0.1:8888"
_SEARXNG_HEALTHY = False
try:
    import requests as _req
    _r = _req.get(f"{_SEARXNG_URL}/healthz", timeout=3)  # a real search can take >2 s
    _SEARXNG_HEALTHY = _r.status_code == 200
except Exception:
    pass

def _searxng_fn(q, l):
    import requests
    r = requests.get(f"{_SEARXNG_URL}/search", params={"q": q, "format": "json"}, timeout=10)
    r.raise_for_status()
    body = r.json()
    results = body.get("results", [])
    unresponsive = body.get("unresponsive_engines", [])
    if not results and unresponsive:
        names = [f'"{u[0]}": {u[1]}' for u in unresponsive[:5]]
        raise RuntimeError(f"searxng upstreams unavailable: {', '.join(names)}")
    return [{"url": x.get("url", ""), "title": x.get("title", ""),
             "text": x.get("content", x.get("snippet", ""))} for x in results[:l]]

_FNS = {"parallel": _parallel_fn, "keenable": _keenable_fn, "exa": _exa_fn,
        "ddgs": _ddgs_fn, "searxng": _searxng_fn}

# ── PUBLIC: search() ──────────────────────────────────────────────────────
def search(query, limit=10):
    """search(query, limit=10) -> (results, status) where results=[{"url","title","text"}]."""
    active = ENGINES if _SEARXNG_HEALTHY else [e for e in ENGINES if e != "searxng"]
    start = _rr[0]
    _rr[0] = (start + 1) % len(active)

    for attempt in range(2):  # initial pass + one cooldown retry
        empty_answers = []
        engines_that_answered = set()

        for i in range(len(active)):
            engine = active[(start + i) % len(active)]
            if not _engine_ok(engine):
                continue
            _throttle(engine)
            t0 = time.monotonic()
            try:
                res = _call_keyless(_FNS[engine], query, limit)
            except Exception:
                _engine_fail(engine)
                _log(engine, query, "failed", 0, time.monotonic() - t0)
                continue

            engines_that_answered.add(engine)
            hits = _norm(res, limit)
            err = res.get("error", "") if isinstance(res, dict) else ""
            failed = (not hits) and (err and _is_fail_msg(err))

            if failed:
                _engine_fail(engine)
                _log(engine, query, "failed", 0, time.monotonic() - t0)
                continue

            _engine_okay(engine)
            status = "ok" if hits else "empty"
            k = _ckey(query, limit)
            if status == "ok":
                _cache_put(k, hits)
            _log(engine, query, status, len(hits), time.monotonic() - t0)

            if hits:
                return hits, "ok"
            empty_answers.append(engine)

        # End of pass
        if len(empty_answers) >= 2:
            return [], "empty"
        if engines_that_answered:
            # Exactly one engine answered with empty — accept it
            return [], "empty"

        # No engine was available in this pass (all on cooldown)
        if attempt == 0:
            # Wait for earliest cross-process cooldown (cap 300s)
            conn = sqlite3.connect(str(_THROTTLE_DB))
            rows = conn.execute(
                "SELECT engine, cooldown_until FROM throttle "
                "WHERE COALESCE(cooldown_until, 0) > ?", (time.time(),)
            ).fetchall()
            conn.close()
            if rows:
                wait = min(d - time.time() for _, d in rows)
                time.sleep(min(max(wait, 0), 300))
            continue

        return [], "failed"

# ── PUBLIC: scholarly() ───────────────────────────────────────────────────
def scholarly(query, limit=25):
    """scholarly(query, limit=25) -> (results, status) via OpenAlex."""
    k = _ckey("openalex:" + query, limit)
    cached = _cache_get(k)
    if cached is not None:
        _log("openalex", query, "cache_hit", len(cached), 0)
        return cached, "ok"

    _throttle("openalex")
    t0 = time.monotonic()

    # Build URL with optional mailto polite-pool parameter
    params = urllib.parse.urlencode({"search": query, "per-page": limit})
    url = f"https://api.openalex.org/works?{params}"

    for attempt in range(1, 4):  # up to 3 attempts
        t_req = time.monotonic()
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": _OPENALEX_UA,
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                status_code = resp.status
                # Honour Retry-After header on 429/503
                if status_code in (429, 503) and attempt < 3:
                    retry_after = resp.headers.get("Retry-After")
                    wait = 10  # default
                    if retry_after:
                        try:
                            wait = min(float(retry_after), 60)  # cap at 60 s
                        except (ValueError, TypeError):
                            pass
                    elapsed = time.monotonic() - t_req
                    _log("openalex", query, "retry", 0, round(elapsed, 2))
                    time.sleep(max(0, wait - elapsed))
                    if attempt < 3:
                        continue  # retry
                    else:
                        # last attempt got 429/503, fall through to failure handling
                        _engine_fail("openalex")
                        _log("openalex", query, "failed", 0, time.monotonic() - t0)
                        return [], "failed"

                if status_code == 200:
                    data = json.loads(resp.read().decode())

                    results = []
                    for w in data.get("results", []):
                        inv = w.get("abstract_inverted_index") or {}
                        abstract = ""
                        if inv:
                            words = []
                            for word, positions in inv.items():
                                for pos in positions:
                                    while len(words) <= pos:
                                        words.append("")
                                    words[pos] = word
                            abstract = " ".join(words)
                        results.append({"url": w.get("doi") or w.get("id", ""),
                                        "title": w.get("display_name", ""),
                                        "text": (w.get("display_name", "") + "\n" + abstract)[:2000]})
                    status = "ok" if results else "empty"
                    _engine_okay("openalex")
                    if status == "ok":
                        _cache_put(k, results)
                    _log("openalex", query, status, len(results), time.monotonic() - t0)
                    return results, status
                else:
                    # Non-429/503 error (e.g. 500)
                    _engine_fail("openalex")
                    _log("openalex", query, "failed", 0, time.monotonic() - t0)
                    return [], "failed"

        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 3:
                retry_after = e.headers.get("Retry-After")
                wait = 10
                if retry_after:
                    try:
                        wait = min(float(retry_after), 60)
                    except (ValueError, TypeError):
                        pass
                elapsed = time.monotonic() - t_req
                _log("openalex", query, "retry", 0, round(elapsed, 2))
                time.sleep(max(0, wait - elapsed))
                continue
            # Non-retriable HTTP error
            _engine_fail("openalex")
            _log("openalex", query, "failed", 0, time.monotonic() - t0)
            return [], "failed"

        except Exception:
            # Non-HTTP error (timeout, etc.) — treat as failure immediately
            _engine_fail("openalex")
            _log("openalex", query, "failed", 0, time.monotonic() - t0)
            return [], "failed"

    # Should not reach here, but just in case
    _engine_fail("openalex")
    _log("openalex", query, "failed", 0, time.monotonic() - t0)
    return [], "failed"
