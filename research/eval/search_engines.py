"""Throttled, rotating, cached multi-engine search layer (~250 lines)."""
import hashlib, json, os, re, sqlite3, sys, threading, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
ENGINES = ["parallel", "keenable", "exa", "ddgs", "searxng"]
THROTTLE = {"parallel": 0.5, "keenable": 1.0, "exa": 2.0, "ddgs": 2.0, "searxng": 1.0, "openalex": 0.2}
CACHE_PATH = Path.home() / ".cache/gridlens-search-cache.sqlite"
CACHE_TTL = 30 * 86400
LOG_PATH = Path("data/raw/eval/engine_log.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── State (module-level) ───────────────────────────────────────────────────
_rr = [0]  # round-robin cursor
_locks = {"cd": threading.Lock(), "co": threading.Lock(), "th": threading.Lock(), "lg": threading.Lock()}
_cooldowns: dict[str, float] = {}
_consec: dict[str, int] = {}
_last: dict[str, float] = {}

# ── Cooldown / throttle helpers ────────────────────────────────────────────
def _engine_ok(name):
    with _locks["cd"]:
        return _cooldowns.get(name, 0) <= time.monotonic()

def _engine_fail(name):
    with _locks["cd"]:
        with _locks["co"]:
            _consec[name] = _consec.get(name, 0) + 1
        dur = min(15 * 60, 60 * (2 ** _consec[name]))
        _cooldowns[name] = time.monotonic() + dur

def _engine_okay(name):
    with _locks["cd"]:
        _cooldowns.pop(name, None)
    with _locks["co"]:
        _consec[name] = 0

def _throttle(name):
    with _locks["th"]:
        last = _last.get(name, 0)
        wait = THROTTLE.get(name, 0.2) - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        _last[name] = time.monotonic()

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
    results = r.json().get("results", [])
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
        return hits, status

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
    try:
        url = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per-page={limit}"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=30) as resp:
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
    except Exception:
        _engine_fail("openalex")
        _log("openalex", query, "failed", 0, time.monotonic() - t0)
        return [], "failed"
