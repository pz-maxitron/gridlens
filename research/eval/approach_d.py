#!/usr/bin/env python3
"""Approach D -- retrieval-first, LLM-as-judge search pipeline (no agent loop).

A fully independent alternative to the agentic per-(country, tool) sessions:

  1. PLAN    one LLM call enumerates the country's likely stakeholders (grid
             operator, regulator, ministry, utilities, universities,
             consultancies, investors...) incl. local-language names, plus a
             handful of generic queries (ReWOO-style plan-then-execute).
  2. SEARCH  code -- not the LLM -- fans every entity-first query
             ("<entity>" <tool>) out across THREE search engines (Keenable,
             Exa, Parallel) and fuses the results (multi-engine retrieval =
             reach). Network-bound and threaded; never touches the LLM slot.
  3. FILTER  deterministic: drop hits that don't mention the tool at all,
             drop our own catalogue (circular), rank by how many
             engines/queries agreed.
  4. JUDGE   the LLM reads small batches of hits and extracts
             {organization, role, status, verbatim quote}.
  5. GROUND  code checks every quote is a VERBATIM substring of the
             retrieved text; anything else is rejected as a possible
             hallucination. Confirmed also requires the tool name inside
             the quote itself.
  6. FILTER2 classify evidence_kind; reject name collisions, data inputs,
             market coverage, and foreign orgs without a named local client.
  7. WRITE   dedupe by normalized organization name, write through
             scripts/research_helpers.py (same schema/validation as every
             other method).

Run with the eval venv (needs httpx + requests for Hermes' keyless search
backends):
  ~/.cache/gridlens-eval-venv/bin/python research/eval/approach_d.py EVAL-D Germany PLEXOS

Environment:
  D_VARIANT:   "d2" (b17afdc prompt + acceptance) or "d3" (current, default).
  LLM_BACKEND: "local" (default, gateway) or "hermes:<profile>".
"""
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

import requests

sys.path.insert(0, "/home/gmk/.hermes/hermes-agent")
import plugins.web.keyless_mcp as web  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LLM_URL = "http://127.0.0.1:39789/v1/chat/completions"
LLM_MODEL = "Qwen3.6-35B-A3B-UD-Q4_K_M"

# --- Usage logging globals (set in main, read by _log_usage) ---
CUR = {"batch_id": "", "country": "", "tool": ""}


def _gateway_key():
    """Read the local gateway key from the implementer profile at runtime."""
    cfg = Path.home() / ".hermes/profiles/implementer/config.yaml"
    m = re.search(r"^\s*api_key:\s*(\S+)", cfg.read_text(encoding="utf-8"), re.M)
    return m.group(1).strip("'\"") if m else ""


LLM_KEY = _gateway_key()
ENGINES = ["keenable", "exa", "parallel"]
ALIASES = {
    "PLEXOS": ["plexos"],
    "PyPSA": ["pypsa"],
    "PROMOD": ["promod"],
    "Bid3": ["bid3", "bid 3"],
    "SDDP": ["sddp"],
}
VENDOR = {
    "PLEXOS": "Energy Exemplar",
    "PyPSA": "open-source, TU Berlin / KIT / Open Energy Transition",
    "PROMOD": "Hitachi Energy, formerly ABB",
    "Bid3": "Aurora Energy Research",
    "SDDP": "PSR",
}
SELF_REF = ("gridlens.org", "esm-usage-catalog", "open-energy-transition/gridlens", "pz-maxitron/gridlens")
CATEGORIES = ["utility_iso_rto", "utility_tso", "utility_generation", "utility_distribution",
              "consultancy", "vendor", "academic_research", "think_tank", "industry_association",
              "government_agency", "government_regulator", "international_body", "development_bank",
              "ngo_foundation", "energy_company_diversified", "project_developer", "other"]
ROLES = ["direct_user", "commissioner", "consultant_modeler", "research_user", "subject_of_study", "qa_reviewer"]
TOOLCAT = {"PLEXOS": "planning_expansion", "PyPSA": "energy_system_optimization",
           "PROMOD": "planning_expansion", "Bid3": "market_simulation",
           "SDDP": "planning_expansion"}
MAX_QUERIES = 60
MAX_HITS_JUDGED = 100
JUDGE_BATCH = 4
GROUP_SUFFIXES = {"group", "inc", "llc", "ltd", "corp", "corporation", "company", "consulting", "partners"}
VALID_EVIDENCE_KINDS = {"uses_tool", "commissioned", "develops_tool", "data_input",
                        "market_coverage", "person_cv", "name_collision", "other"}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def tool_context(tool):
    text = (ROOT / "research/tool_hints.sh").read_text(encoding="utf-8")
    m = re.search(r'TOOL_CONTEXT\["%s"\]="(.*?)"\n' % re.escape(tool), text, re.S)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- Usage log --
def _log_usage(backend, prompt_tokens, completion_tokens, session_id=None):
    """Append one line to data/raw/eval/D_usage.jsonl."""
    path = ROOT / "data/raw/eval/D_usage.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "batch_id": CUR["batch_id"],
            "country": CUR["country"],
            "tool": CUR["tool"],
            "backend": backend,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "session_id": session_id,
        }) + "\n")


# --------------------------------------------------------------- LLM backends
def _llm_local(prompt, max_tokens, think):
    """Call the local OpenAI-compatible gateway. Returns (out, pt, ct)."""
    body = {"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2, "max_tokens": max_tokens}
    if not think:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    headers = {"Authorization": f"Bearer {LLM_KEY}"}
    for attempt in range(3):
        try:
            r = requests.post(LLM_URL, json=body, headers=headers, timeout=900)
            if r.status_code == 400 and "chat_template_kwargs" in body:
                body.pop("chat_template_kwargs")
                continue
            r.raise_for_status()
            j = r.json()
            msg = j["choices"][0]["message"]
            out = msg.get("content") or ""
            usage = j.get("usage") or {}
            return re.sub(r"```(?:json)?", "", out).strip(), \
                   usage.get("prompt_tokens"), usage.get("completion_tokens")
        except Exception as e:  # noqa: BLE001
            log(f"LLM error (attempt {attempt + 1}): {e!r}")
            time.sleep(20)
    return "", None, None


def _llm_hermes(profile, prompt, max_tokens, think):
    """Call hermes CLI for an alternate LLM backend. Returns (out, session_id)."""
    tmp = Path(f"/tmp/hermes_prompt_{int(time.time() * 1000) % 1000000}.txt")
    try:
        tmp.write_text(prompt, encoding="utf-8")
        cmd = ["hermes", "-p", profile, "chat", "--query-file", str(tmp),
               "-Q", "--oneshot", "-t", "none"]
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=600, cwd="/tmp")
        stdout = result.stdout
        session_id = None
        lines = stdout.splitlines()
        # Strip trailing session_id: lines, keep the last value seen
        while lines and lines[-1].startswith("session_id:"):
            session_id = lines[-1].split(":", 1)[1].strip()
            lines.pop()
        out = "\n".join(lines).strip()
        return out, session_id
    finally:
        tmp.unlink(missing_ok=True)


def llm(prompt, max_tokens=4000, think=False):
    """LLM dispatcher: local gateway or hermes:<profile> with usage logging."""
    backend = os.environ.get("LLM_BACKEND", "local")
    if backend == "local":
        out, pt, ct = _llm_local(prompt, max_tokens, think)
        _log_usage("local", pt, ct)
        return out
    else:
        profile = backend.split(":", 1)[1]
        out, sid = _llm_hermes(profile, prompt, max_tokens, think)
        _log_usage(f"hermes:{profile}", None, None, session_id=sid)
        return out


def parse_json(text):
    """Pull the first JSON object/array out of an LLM reply."""
    text = re.sub(r"```(?:json)?", "", text)
    for opener, closer in (("{" , "}"), ("[", "]")):
        s = text.find(opener)
        e = text.rfind(closer)
        if s != -1 and e > s:
            try:
                return json.loads(text[s:e + 1])
            except json.JSONDecodeError:
                continue
    return None


# -------------------------------------------------------- Judge prompts ------
def judge_prompt_d2(country, tool, batch):
    """D2 judge prompt from commit b17afdc (no evidence_kind / client_or_project)."""
    blocks = "\n\n".join(
        f"### HIT {i}\nURL: {h['url']}\nTEXT:\n{h['text']}"
        for i, h in enumerate(batch)
    )
    return f"""You are an evidence analyst. Below are web search hits. For each hit, decide
whether it is evidence that a SPECIFIC organization uses, commissioned,
developed, or studied with the software {tool} ({VENDOR[tool]}) in relation
to {country} (an organization based in {country}, or work about {country}'s
energy system).

Rules:
- "quote" MUST be copied character-for-character from the hit TEXT (one
  continuous sentence or phrase, max ~300 characters). Never paraphrase,
  never combine fragments. Quotes that are not verbatim are discarded.
- status "confirmed" only if the quote itself names {tool} and the
  organization's use of it is explicit; otherwise "candidate".
- Ignore hits that only mention {tool} generically (vendor marketing with no
  named {country} organization, tool comparisons, job ads with no
  organization named, unrelated countries).
- One hit may name several organizations -- list each separately.
- institution_category one of: {", ".join(CATEGORIES)}
- role one of: {", ".join(ROLES)}
- "org_country": the country where the organization is based (e.g., "Germany", "France"), or "multinational" for an international company.
- "about_country": true if the evidence is explicitly about {country}'s energy system or work for a {country} organization, else false.

Reply with JSON only:
{{"findings": [{{"hit": 0, "institution_name": "...", "institution_category": "...",
"role": "...", "status": "confirmed|candidate", "quote": "...",
"use_case": "one specific sentence", "evidence_strength": "HIGH|MEDIUM|LOW",
"source_type": "official_methodology|academic_paper|news_release|tender_procurement|research_finding",
"org_country": "country name or multinational", "about_country": true,
"why": "one sentence"}}]}}
Return {{"findings": []}} if no hit qualifies.

{blocks}"""


def judge_prompt_d3(country, tool, batch):
    """D3 judge prompt (current behaviour with evidence_kind and client_or_project)."""
    blocks = "\n\n".join(
        f"### HIT {i}\nURL: {h['url']}\nTEXT:\n{h['text']}"
        for i, h in enumerate(batch)
    )
    return f"""You are an evidence analyst. Below are web search hits. For each hit, decide
whether it is evidence that a SPECIFIC organization uses, commissioned,
developed, or studied with the software {tool} ({VENDOR[tool]}) in relation
to {country} (an organization based in {country}, or work about {country}'s
energy system).

Rules:
- "quote" MUST be copied character-for-character from the hit TEXT (one
  continuous sentence or phrase, max ~300 characters). Never paraphrase,
  never combine fragments. Quotes that are not verbatim are discarded.
- status "confirmed" only if the quote itself names {tool} and the
  organization's use of it is explicit; otherwise "candidate".
- Ignore hits that only mention {tool} generically (vendor marketing with no
  named {country} organization, tool comparisons, job ads with no
  organization named, unrelated countries).
- One hit may name several organizations -- list each separately.
- institution_category one of: {", ".join(CATEGORIES)}
- role one of: {", ".join(ROLES)}
- "org_country": the country where the organization is based (e.g., "Germany", "France"), or "multinational" for an international company.
- "about_country": true if the evidence is explicitly about {country}'s energy system or work for a {country} organization, else false.
- "evidence_kind": one of uses_tool (the organization runs or licenses {tool}), commissioned (it paid for or received a study done with {tool}), develops_tool (it builds/maintains {tool} or a {tool} model), data_input (its data or dataset is only an input to {tool} or a {tool}-based model), market_coverage (a vendor product, dataset or forecast covers its market or system, but it is not shown using {tool}), person_cv (a person's CV, LinkedIn or bio), name_collision (the name resembles {tool} but it is a different thing), other.
- "client_or_project": the {country} client organization or {country} project named in the quote, copied as written in the quote; "" if none.

Reply with JSON only:
{{"findings": [{{"hit": 0, "institution_name": "...", "institution_category": "...",
"role": "...", "status": "confirmed|candidate", "quote": "...",
"use_case": "one specific sentence", "evidence_strength": "HIGH|MEDIUM|LOW",
"source_type": "official_methodology|academic_paper|news_release|tender_procurement|research_finding",
"org_country": "country name or multinational", "about_country": true,
"evidence_kind": "...", "client_or_project": "...",
"why": "one sentence"}}]}}
Return {{"findings": []}} if no hit qualifies.

{blocks}"""


def judge(country, tool, batch):
    variant = os.environ.get("D_VARIANT", "d3")
    if variant == "d2":
        prompt = judge_prompt_d2(country, tool, batch)
    else:
        prompt = judge_prompt_d3(country, tool, batch)
    data = parse_json(llm(prompt, max_tokens=3000)) or {}
    return data.get("findings", []) if isinstance(data, dict) else []


# ------------------------------------------------------ Acceptance filters --
def accept_d2(f, country):
    """D2 acceptance: org_country == target OR (about_country AND qualifying role)."""
    org_country = (f.get("org_country") or "").strip().lower()
    about_country = bool(f.get("about_country"))
    role = f.get("role", "")
    target = country.strip().lower()
    if org_country == target:
        return True, ""
    elif about_country and role in ("consultant_modeler", "commissioner"):
        return True, ""
    return False, "WRONG_COUNTRY"


def _norm_institution(name):
    """Normalize institution name: lowercase, remove punctuation."""
    n = squash(name)
    return re.sub(r"[^\w\s]", "", n)


def _accept_d3(f, quote, country, tool):
    """D3 acceptance: evidence_kind filter + client_or_project country check."""
    evidence_kind = f.get("evidence_kind", "") or ""
    client_or_project = (f.get("client_or_project") or "").strip()
    org_country = (f.get("org_country") or "").strip().lower()
    role = f.get("role", "")
    inst_name = f.get("institution_name", "")
    target = country.strip().lower()
    tool_aliases = ALIASES.get(tool, [])

    # a) NAME_COLLISION
    if evidence_kind == "name_collision":
        return False, "NAME_COLLISION", True
    norm_inst = _norm_institution(inst_name)
    for alias in tool_aliases:
        if norm_inst == alias:
            return False, "NAME_COLLISION", True
        words = norm_inst.split()
        if len(words) >= 2 and words[0] == alias and words[1] in GROUP_SUFFIXES:
            return False, "NAME_COLLISION", True

    # b) DATA_INPUT / MARKET_COVERAGE
    if evidence_kind in ("data_input", "market_coverage"):
        return False, evidence_kind, False

    # c) Country filter
    if org_country == target:
        accept = True
    else:
        if client_or_project and client_or_project.lower() in quote.lower() \
                and role in ("consultant_modeler", "commissioner", "research_user"):
            accept = True
        else:
            return False, "WRONG_COUNTRY", False

    # d) cap_candidate
    cap_candidate = evidence_kind in ("person_cv", "other") or evidence_kind not in VALID_EVIDENCE_KINDS

    return accept, "", cap_candidate


def accept_finding(f, quote, country, tool):
    """Unified acceptance: dispatches to d2 or d3 rule."""
    variant = os.environ.get("D_VARIANT", "d3")
    if variant == "d2":
        ok, reason = accept_d2(f, country)
        return ok, reason, False
    return _accept_d3(f, quote, country, tool)


# -------------------------------------------------------------- SEARCH -----
def run_search(engine, query):
    try:
        res = getattr(web, f"{engine}_search_keyless")(query, 8)
        return [(engine, query, h) for h in (res.get("data") or {}).get("web", [])]
    except Exception as e:  # noqa: BLE001
        log(f"search error {engine}: {e!r}"[:200])
        return []


def build_queries(country, tool, ents, extra):
    q = []
    for e in ents:
        q.append((f'"{e["name"]}" {tool}', ["exa", "keenable"]))
        ln = (e.get("local_name") or "").strip()
        if ln and ln.lower() != e["name"].lower():
            q.append((f'"{ln}" {tool}', ["exa", "keenable"]))
    generic = [
        f"{tool} {country}", f"{tool} {country} CIGRE", f"{tool} {country} IEEE",
        f"{tool} {country} ESIG", f"{VENDOR[tool].split(',')[0]} {tool} {country}",
    ] + extra
    q += [(g, ENGINES) for g in generic]
    seen, out = set(), []
    for query, engines in q:
        if query.lower() not in seen:
            seen.add(query.lower())
            out.append((query, engines))
    return out[:MAX_QUERIES]


def norm_url(u):
    return re.sub(r"[#?].*$", "", u.strip().lower()
                  .replace("http://", "https://").replace("://www.", "://")).rstrip("/")


def search_all(queries, tool):
    jobs = [(eng, query) for query, engines in queries for eng in engines]
    hits = {}
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for results in ex.map(lambda j: run_search(*j), jobs):
            for engine, query, h in results:
                url = h.get("url") or ""
                if not url.startswith("http") or any(
                        s in url.lower() for s in SELF_REF):
                    continue
                text = f"{h.get('title', '')}\n{h.get('description', '')}"
                key = norm_url(url)
                entry = hits.setdefault(key, {
                    "url": url, "title": h.get("title", ""),
                    "texts": set(), "engines": set(), "queries": set(),
                })
                entry["texts"].add(text)
                entry["engines"].add(engine)
                entry["queries"].add(query)
    aliases = ALIASES[tool]
    kept = []
    for e in hits.values():
        full = "\n".join(sorted(e["texts"], key=len, reverse=True))
        low = (full + " " + e["url"]).lower()
        if not any(a in low for a in aliases):
            continue
        e["text"] = excerpt(full, aliases)
        e["score"] = (len(e["engines"]) * 2 + len(e["queries"])
                      + sum(low.count(a) for a in aliases))
        kept.append(e)
    kept.sort(key=lambda e: e["score"], reverse=True)
    return len(jobs), len(hits), kept[:MAX_HITS_JUDGED]


def excerpt(text, aliases, window=700, cap=2500):
    """Keep the parts of a long snippet around each tool mention."""
    if len(text) <= cap:
        return text
    low = text.lower()
    spans = []
    for a in aliases:
        for m in re.finditer(re.escape(a), low):
            spans.append((max(0, m.start() - window),
                          min(len(text), m.end() + window)))
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    out = " [...] ".join(text[s:e] for s, e in merged)
    return (out or text)[:cap]


# --------------------------------------------------------------- PLAN ------
def plan(country, tool):
    prompt = f"""You are planning a web search for evidence that organizations in {country}
use the energy-modelling software {tool} ({VENDOR[tool]}).
What the tool is for: {tool_context(tool)}

List the {country} organizations most likely to use, commission, or study
{tool}: the grid/system operator(s) and market operator, the energy
regulator, the energy ministry / energy or planning agency, the largest
utilities and generation companies, universities and research institutes
active in energy-system modelling, consultancies active in {country}'s
power sector (local and international), and major investors/developers.
Give each organization's official name, and its name in {country}'s own
language if different.

Also give up to 8 extra search queries that could surface {tool} usage in
{country} (include local-language queries and conference/vendor angles).
Every query must contain the word {tool}.

Reply with JSON only:
{{"entities": [{{"name": "...", "local_name": "...", "type": "..."}}], "queries": ["..."]}}
Up to 25 entities."""
    data = parse_json(llm(prompt, max_tokens=3000)) or {}
    ents = [e for e in data.get("entities", [])
            if isinstance(e, dict) and e.get("name")][:25]
    qs = [q for q in data.get("queries", [])
          if isinstance(q, str) and tool.lower() in q.lower()][:8]
    return ents, qs


# --------------------------------------------------------------- FILTER ----
def squash(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def grounded(quote, text):
    """Quote must be a verbatim substring of the retrieved text (ellipses
    allowed to separate verbatim parts). Returns False for paraphrases."""
    q, t = squash(quote), squash(text)
    if len(q) < 15:
        return False
    parts = [p.strip(" .") for p in re.split(
        r"\.\.\.|\u2026|\[\.\.\.\]", q) if len(p.strip(" .")) >= 10]
    return bool(parts) and all(p in t for p in parts)


def org_key(name):
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\(.*?\)", " ", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    stop = {"the", "of", "and", "gmbh", "ag", "sa", "s", "a", "ltd", "limited",
            "inc", "co", "company", "plc", "llc"}
    return " ".join(t for t in n.split() if t not in stop)


# --------------------------------------------------------------- WRITE -----
def existing_keys(batch_id, country, tool):
    if batch_id.startswith("EVAL-"):
        path = ROOT / f"data/raw/eval/{batch_id}.jsonl"
    else:
        path = ROOT / f"data/raw/incoming/{batch_id}.jsonl"
    keys = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("country_label") == country and r.get("tool_name") == tool:
                    keys.add(org_key(r.get("institution_name", "")))
    return keys


def helper(*args):
    p = subprocess.run(
        ["python3", "scripts/research_helpers.py", *args],
        cwd=ROOT, capture_output=True, text=True,
    )
    return (p.stdout + p.stderr).strip()


def main():
    batch_id, country, tool = sys.argv[1], sys.argv[2], sys.argv[3]
    CUR["batch_id"] = batch_id
    CUR["country"] = country
    CUR["tool"] = tool
    t0 = time.time()
    log(f"=== approach D: {country} / {tool} ===")
    ents, extra = plan(country, tool)
    log(f"plan: {len(ents)} entities, {len(extra)} extra queries")
    queries = build_queries(country, tool, ents, extra)
    n_jobs, n_raw, hits = search_all(queries, tool)
    log(f"search: {len(queries)} queries / {n_jobs} engine calls -> "
        f"{n_raw} unique URLs -> {len(hits)} mention {tool}")

    findings, rejected, rejected_country, rejected_filter = [], 0, 0, 0
    rej_lines = []
    variant = os.environ.get("D_VARIANT", "d3")
    for i in range(0, len(hits), JUDGE_BATCH):
        batch = hits[i:i + JUDGE_BATCH]
        for f in judge(country, tool, batch):
            try:
                h = batch[int(f.get("hit", -1))]
            except (ValueError, IndexError, TypeError):
                rejected += 1
                rej_lines.append({
                    "batch_id": batch_id, "country": country, "tool": tool,
                    "institution_name": f.get("institution_name", ""),
                    "org_country": f.get("org_country", ""),
                    "about_country": f.get("about_country", ""),
                    "role": f.get("role", ""),
                    "evidence_kind": f.get("evidence_kind", ""),
                    "client_or_project": f.get("client_or_project", ""),
                    "reason": "NOT_VERBATIM", "url": "",
                })
                continue
            quote = (f.get("quote") or "").strip()
            if not f.get("institution_name") or not grounded(quote, h["text"]):
                rejected += 1
                rej_lines.append({
                    "batch_id": batch_id, "country": country, "tool": tool,
                    "institution_name": f.get("institution_name", ""),
                    "org_country": f.get("org_country", ""),
                    "about_country": f.get("about_country", ""),
                    "role": f.get("role", ""),
                    "evidence_kind": f.get("evidence_kind", ""),
                    "client_or_project": f.get("client_or_project", ""),
                    "reason": "NOT_VERBATIM", "url": h.get("url", ""),
                })
                continue
            # Acceptance filter
            accept, reason, cap_candidate = accept_finding(f, quote, country, tool)
            if not accept:
                if reason == "WRONG_COUNTRY":
                    rejected_country += 1
                else:
                    rejected_filter += 1
                rej_lines.append({
                    "batch_id": batch_id, "country": country, "tool": tool,
                    "institution_name": f.get("institution_name", ""),
                    "org_country": f.get("org_country", ""),
                    "about_country": f.get("about_country", ""),
                    "role": f.get("role", ""),
                    "evidence_kind": f.get("evidence_kind", ""),
                    "client_or_project": f.get("client_or_project", ""),
                    "reason": reason, "url": h.get("url", ""),
                })
                continue
            names_tool = any(a in quote.lower() for a in ALIASES[tool])
            status = ("confirmed" if f.get("status") == "confirmed"
                      and names_tool else "candidate")
            if cap_candidate:
                status = "candidate"
            findings.append((f, h, quote, status, names_tool))
        log(f"judged {min(i + JUDGE_BATCH, len(hits))}/{len(hits)} hits: "
            f"{len(findings)} accepted, {rejected} rejected, {rejected_filter} filtered")
    if rej_lines:
        with (ROOT / "data/raw/eval/D_rejections.jsonl").open("a", encoding="utf-8") as fh:
            for r in rej_lines:
                fh.write(json.dumps(r) + "\n")

    rank = {"confirmed": 2, "candidate": 1}
    best = {}
    for f, h, quote, status, names_tool in findings:
        k = org_key(f["institution_name"])
        if not k:
            continue
        cur = best.get(k)
        if cur is None or rank[status] > rank[cur[3]]:
            best[k] = (f, h, quote, status, names_tool)

    seen = existing_keys(batch_id, country, tool)
    written = 0
    for k, (f, h, quote, status, names_tool) in best.items():
        if k in seen:
            continue
        row = {
            "batch_id": batch_id,
            "institution_name": f["institution_name"].strip(),
            "institution_category": (f.get("institution_category")
                                     if f.get("institution_category") in CATEGORIES
                                     else "other"),
            "official_website": "",
            "country_label": country,
            "tool_name": tool,
            "tool_category": TOOLCAT[tool],
            "tool_explicitly_named": names_tool,
            "role": f.get("role") if f.get("role") in ROLES else "subject_of_study",
            "use_case": (f.get("use_case") or "").strip()
                        or f"Evidence of {tool} use found in retrieved source.",
            "decision_type": "",
            "decision_basis": "",
            "evidence_strength": (f.get("evidence_strength")
                                  if f.get("evidence_strength") in ("HIGH", "MEDIUM", "LOW")
                                  else "MEDIUM"),
            "source_type": (f.get("source_type") or "research_finding").strip(),
            "source_title": (h.get("title") or "").strip()[:300],
            "source_date": "",
            "source_url": h["url"],
            "exact_snippet_or_quote": quote,
            "why_it_supports_the_claim": (f.get("why") or "").strip()
                                         or "Quote names the organization and the tool.",
            "status": status,
            "historical_or_current": "current",
            "notes": (f"Approach D (retrieval pipeline). Quote verified verbatim "
                      f"against retrieved text. "
                      f"Engines: {', '.join(sorted(h['engines']))}. "
                      f"Queries: {'; '.join(sorted(h['queries']))[:300]}"),
        }
        tmp = Path(f"/tmp/approach_d_{country}_{tool}.json")
        tmp.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
        out = helper(batch_id, "add", str(tmp))
        log(out)
        if out.startswith("OK"):
            written += 1
            seen.add(k)

    if written == 0 and not seen:
        url = "https://exa.ai/search?q=" + urllib.parse.quote(f"{tool} {country}")
        log(helper(batch_id, "gap", country, tool, url,
                   f"Approach D: {len(queries)} queries x engines ({n_jobs} calls), "
                   f"{n_raw} URLs, {len(hits)} mentioning {tool}, "
                   f"{len(findings)} accepted findings -- none written."))

    stats = {
        "batch_id": batch_id, "country": country, "tool": tool,
        "entities": len(ents), "queries": len(queries),
        "engine_calls": n_jobs, "unique_urls": n_raw,
        "hits_mentioning_tool": len(hits),
        "grounded_findings": len(findings),
        "rejected_ungrounded": rejected,
        "rejected_wrong_country": rejected_country,
        "rejected_filtered": rejected_filter,
        "orgs_written": written,
        "minutes": round((time.time() - t0) / 60, 1),
    }
    with (ROOT / "data/raw/eval/D_stats.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(stats) + "\n")
    log("stats:", json.dumps(stats))


if __name__ == "__main__":
    main()
