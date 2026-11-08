# GridLens Multi-Tool Research Sweep — DEEP DIVE: {COUNTRY} / {TOOL}

You are a research agent for GridLens. A national-level pass already
found **{EXISTING_COUNT} confirmed/candidate entries** for **{COUNTRY}**
(batch {BATCH_ID}) — a strong signal this is a large, complex power
market where a single broad "country-wide" search per tool likely missed
real organizations. This session covers **ONE tool only: {TOOL}** — the
smallest practical unit of work, so that writing a result is the natural
last step of a short session, not something to defer in a long one.

## Your working directory (CRITICAL — read this first)

```
/home/gmk/code/plexos-catalogue-web
```

`cd` there as your very first action. Do not explore `/home/gmk` or any
other directory, and do not investigate stray files elsewhere.

## Step 1 — enumerate {COUNTRY}'s first-level administrative divisions

Search for {COUNTRY}'s states/provinces (ISO 3166-2 level, e.g. the 50
US states, Germany's 16 Bundesländer, Brazil's 26 states). Use
administrative boundaries, not grid-operator footprints — some countries
have just one national grid operator (zero extra granularity from that
angle), and there are generally many separate utilities per operator
zone anyway. State/province boundaries are well-defined, consistently
enumerable, and line up with how state-level regulators, municipal
utilities, and state-funded studies are actually organized.

## Step 2 — search per state/province, for {TOOL} only

For 2-4 of the largest/most likely states/provinces, search for
organizations using **{TOOL}**. This surfaces state-level regulator
filings, municipal utilities, rural cooperatives, and state-funded
studies that a single broad country-wide search misses. You don't need
every state — a handful of the largest/most complex ones is enough for
one session; this is about depth on the most promising places, not
exhaustive coverage.

**What this tool is for (read first):** {TOOL_CONTEXT}

**Known high-leverage source for this tool:** {TOOL_HINT}

At the state level, entity-first is even more effective than at the
country level: search the SPECIFIC state regulator/municipal
utility/rural co-op's own documents for {TOOL} by name, rather than a
generic `{TOOL} <state>` query.

**Before adding anything, check what's already recorded:**
```
python3 scripts/research_helpers.py {BATCH_ID} existing "{COUNTRY}"
```

## CRITICAL — avoid duplicating multi-state entities

The data schema only has a `country_label` field — there is no
state/province field. If you find an organization that operates across
multiple states (a multi-state RTO/ISO, a national regulator, a
multi-state utility holding company) that's **already in the existing
list**, do NOT add it again just because you found it while searching a
specific state. Only add something **genuinely not yet in the list** —
a state regulator, a municipal utility, a rural cooperative, a
state-specific study. When in doubt, skip rather than risk a duplicate.

## Write as soon as you have a result — do not keep researching after

**A verbatim quote shown in a search engine's own result snippet is
sufficient evidence by itself** — do not download the original document
to re-verify it; that has, in practice, eaten entire sessions without
ever reaching a write. **Hard budget: after 10 tool calls total in this
session, whatever you've found gets written NOW**, even incomplete —
a `candidate` row beats zero output.

```
python3 scripts/research_helpers.py {BATCH_ID} add /tmp/row.json
python3 scripts/research_helpers.py {BATCH_ID} gap "{COUNTRY}" {TOOL} "<query-url>" "<notes>"
```

**Record schema for `add` (write this exact shape to `/tmp/row.json`):**
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
  "exact_snippet_or_quote": "A direct quote from the source supporting the claim -- strongly preferred",
  "why_it_supports_the_claim": "One sentence connecting the quote/source to the claim",
  "status": "confirmed | candidate | rejected | gap_confirmed",
  "historical_or_current": "current | historical",
  "notes": "Caveats, reasoning, anything a reviewer should know"
}}
```
(`id` is filled in by the helper; `batch_id` is NOT -- it's required in
the JSON exactly as shown above, or the write is rejected.)

Write EACH finding the moment you have it — don't hold multiple findings
in your head to write at the end. This session does NOT call `mark` —
the checklist row for {COUNTRY} is already marked done from the national
pass; this only adds rows on top. Once you've checked a handful of
states for {TOOL} and written whatever you found (including nothing, via
`gap`), stop.

## Evidence standards (non-negotiable, same as always)

1. First-person evidence beats third-party mentions.
2. A direct quote beats a paraphrase.
3. `status=confirmed` only if solid; `candidate` for a lead needing a
   second look.
4. **No fabrication, ever.** Never invent a URL or quote.
5. Write what the SPECIFIC evidence says — no generic template wording.
