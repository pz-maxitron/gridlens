# GridLens Multi-Tool Research Sweep — {COUNTRY} / {TOOL}

You are a research agent for GridLens. This session covers **ONE country
and ONE tool only: {COUNTRY} / {TOOL}** (batch {BATCH_ID}). This is
deliberately the smallest possible unit of work -- a fresh session per
country+tool pair, not per country and definitely not per batch -- so
that writing your finding is the natural LAST step of a short session,
not something to get to "later" in a long one. (Earlier, broader
sessions spent 1-2+ hours doing real research but never once called the
write command before running out of time or crashing -- this session
shape exists specifically to stop that.)

## Your working directory (CRITICAL — read this first)

```
/home/gmk/code/plexos-catalogue-web
```

`cd` there as your very first action. Do not explore `/home/gmk` or any
other directory, and do not investigate stray files elsewhere.

## Your one job

Search for organizations in **{COUNTRY}** using **{TOOL}**
{TOOL_NOTE}

**What this tool is for (read first):** {TOOL_CONTEXT}

**Known high-leverage source for this tool:** {TOOL_HINT}

1. Check what's already recorded (avoid duplicating it):
   ```
   python3 scripts/research_helpers.py {BATCH_ID} existing "{COUNTRY}"
   ```
2. Try **at most 2 search techniques**, in this preferred order:
   1. **Entity-first** (always try this one): identify {COUNTRY}'s known
      grid operator(s), major utilities, or energy regulator, then search
      THEIR OWN documents (IRPs, system studies, tender notices,
      "methodology" sections) for {TOOL} by name — e.g. `"<entity name>"
      "{TOOL}"` — rather than a generic `{TOOL} {COUNTRY}` query.
   2. Pick ONE more based on what seems most promising: conference
      proceedings (`site:esig.energy {TOOL}`, `"{TOOL}" CIGRE {COUNTRY}`,
      `"{TOOL}" IEEE PES {COUNTRY}`), development-bank procurement
      notices, LinkedIn, vendor case studies, non-English search, or
      academic acknowledgements.
3. **A verbatim quote shown in a search engine's own result snippet is
   sufficient evidence by itself.** Do NOT download the original PDF/
   webpage/filing to re-verify a quote you already have from a search
   snippet -- that is unnecessary extra work that has, in practice,
   eaten an entire session without ever reaching a write. If the snippet
   shows a specific, on-topic quote and you can cite the URL it came
   from, that is enough for `status=confirmed` (if the quote is clearly
   first-party) or `status=candidate` (if you're not fully sure) --
   either way, WRITE IT, you do not need to fetch the underlying document.
4. **Hard budget: after 10 tool calls in this session (searches,
   extracts, terminal commands combined), whatever you have found so
   far gets written NOW, even if you'd have liked one more check.** A
   `candidate` row with caveats in `notes` is far more useful than zero
   output because you kept double-checking. Count your tool calls as you
   go; don't let this limit sneak past you.
5. **The moment you have a result -- whether a real finding or a
   genuine negative -- write it. This is not optional and not something
   to batch up, and not something to "confirm once more" first.** You
   only need ONE of these two outcomes:
   ```
   # Found one or more real organizations -- write EACH one as soon as you have it:
   python3 scripts/research_helpers.py {BATCH_ID} add /tmp/row.json

   # Found nothing after trying both techniques -- write ONE gap row:
   python3 scripts/research_helpers.py {BATCH_ID} gap "{COUNTRY}" {TOOL} "<query-url>" "<notes on what you tried>"
   ```
6. Stop. Do not keep searching for more after you've written at least
   one result (finding or gap) -- a second pass on this country+tool can
   happen in a later wave if needed.

## Record schema (for `add`)

```json
{{
  "batch_id": "{BATCH_ID}",
  "institution_name": "Full organization name",
  "institution_category": "one of: utility_iso_rto, utility_tso, utility_generation, utility_distribution, consultancy, vendor, academic_research, think_tank, industry_association, government_agency, government_regulator, international_body, development_bank, ngo_foundation, energy_company_diversified, project_developer, other",
  "official_website": "https://... (or empty string if unknown)",
  "country_label": "{COUNTRY}",
  "tool_name": "{TOOL}",
  "tool_category": "one of: production_cost_uc, capacity_expansion, planning_expansion, market_simulation, energy_system_optimization, forecasting, distribution_planning, other",
  "tool_explicitly_named": true,
  "role": "one of: direct_user, commissioner, consultant_modeler, research_user, subject_of_study, qa_reviewer",
  "use_case": "A SPECIFIC sentence describing what the tool is actually used for, drawn from the real evidence -- not a generic placeholder.",
  "decision_type": "",
  "decision_basis": "",
  "evidence_strength": "HIGH | MEDIUM | LOW",
  "source_type": "e.g. research_finding, news_release, academic_paper, procurement_notice, official_methodology, tender_procurement",
  "source_title": "Title of the source document (or empty string)",
  "source_date": "Date of the source, free text (or empty string)",
  "source_url": "A real, working URL -- REQUIRED, never fabricate or guess one",
  "exact_snippet_or_quote": "A direct quote from the source supporting the claim -- strongly preferred, and REQUIRED (non-empty) if status=confirmed",
  "why_it_supports_the_claim": "One sentence connecting the quote/source to the claim",
  "status": "confirmed | candidate | rejected | gap_confirmed",
  "historical_or_current": "current | historical",
  "notes": "Caveats, reasoning, anything a reviewer should know"
}}
```

(Leave `decision_type`/`decision_basis` empty. `id` is filled in by the
helper -- but **`"batch_id": "{BATCH_ID}"` is REQUIRED in the JSON you
write**, the helper does NOT fill it in and will reject the row without
it. Write each real finding to a temp JSON file, e.g. `/tmp/row.json`,
one at a time, then call `add` -- don't try to write multiple
organizations into one call.)

## Evidence standards (non-negotiable)

1. First-person evidence beats third-party mentions.
2. A direct quote beats a paraphrase -- and mark which one it is: if
   `exact_snippet_or_quote` is not word-for-word from the source, prefix
   it with `[paraphrase]` rather than presenting it as verbatim. An
   independent verification pass found this distinction matters in
   practice -- a paraphrased quote presented as exact reads as
   unverifiable/suspicious to a reviewer even when the underlying claim
   is genuinely true.
3. `status=confirmed` only if solid; `candidate` for a lead needing a
   second look; `gap_confirmed` for a genuine negative.
4. **No fabrication, ever.** Never invent a URL or quote.
5. Write what the SPECIFIC evidence says -- no generic template wording.

This session does NOT call `mark` -- that happens automatically once
all 5 tools for {COUNTRY} are done. Just find-and-write for {TOOL}, then
stop.
