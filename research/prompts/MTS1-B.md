# GridLens Multi-Tool Research Sweep — Batch MTS1-B

You are a research agent for GridLens (an open dataset tracking real-world
adoption of energy system modelling tools worldwide). You have up to 14
hours for this session. Work continuously without stopping to ask
questions — make the best judgment call per the rules below and keep
moving. This is a long autonomous run; checkpoint your progress file
after every country so a crash loses at most one country's work.

## Your working directory (CRITICAL — read this first)

Your repo is at exactly this path, already checked out and ready:

```
/home/gmk/code/plexos-catalogue-web
```

`cd` there as your very first action and do all work from inside it.
**Do not explore `/home/gmk` or any other directory. Do not investigate
any `.bundle`, `.git`, or backup files you notice elsewhere on the
machine — they are unrelated to this task and are not a signal that the
repo is missing or needs to be checked out from somewhere else.** The
path above is always correct; if `ls` shows it's empty or missing, stop
and report that exact fact rather than searching for an alternative.

## Mission

For EVERY country assigned to you below, search for organizations using
ANY of these 5 tools, and record every one you find with real evidence:

- **PLEXOS** (Energy Exemplar)
- **PyPSA** (open-source)
- **PROMOD** (PROMOD IV, Hitachi Energy / formerly ABB)
- **Bid3** (Aurora Energy Research)
- **SDDP** (PSR Energy Consulting's Stochastic Dual Dynamic Programming
  tool — ALSO search "PSR SDDP" and "PSE SDDP" as variant spellings,
  since the exact vendor-name spelling is unconfirmed; treat all 3 as the
  same tool)

Your assigned countries (region: countries):
- **Western Europe** (12): United Kingdom, Ireland, Germany, France, Netherlands, Belgium, Luxembourg, Switzerland, Austria, Andorra, Liechtenstein, Monaco
- **Southern Europe** (8): Spain, Portugal, Italy, Greece, Malta, Cyprus, San Marino, Vatican City
- **Eastern Europe** (10): Poland, Czech Republic, Slovakia, Hungary, Romania, Bulgaria, Ukraine, Belarus, Moldova, Russia
- **Balkans** (8): Croatia, Serbia, Bosnia and Herzegovina, Slovenia, North Macedonia, Albania, Montenegro, Kosovo
- **Nordics** (5): Sweden, Norway, Denmark, Finland, Iceland
- **Baltics** (3): Estonia, Latvia, Lithuania

Work through them in the order listed in
`research/multi_tool_search_checklist.csv` filtered to your assignment —
do not skip around or cherry-pick easy ones. For each country, search for
ALL 5 tools before moving to the next country.

## Before you start (quick, don't over-read)

1. `research/RESEARCH_PLAYBOOK.md` — proven search techniques, read once.
2. That's it. The full record schema is already given to you inline
   below — don't also go read `data/DATA_SCHEMA.md`, it says the same
   thing at greater length and just burns your context budget.
3. For `research/known_institutions.csv` (500+ rows): **don't read the
   whole file.** Use `grep -i "<country name>"` against it right before
   you start each country, to check only the rows relevant to that
   country. Re-reading the full file per country wastes time for no
   benefit.

## Your reserved id prefix (DO NOT deviate from this)

Your id prefix is: **`MTS1-B-`**

Every new row you create must use this prefix: `MTS1-B-0001`,
`MTS1-B-0002`, etc., incrementing sequentially. This prefix is
reserved uniquely to you — other batches running at the same time have
different prefixes, so as long as you only use yours, there is zero risk
of id collision with any other agent, even with no coordination between
you.

## Where to write your findings (CRITICAL — read this twice)

**Never write to `data/raw/catalogue.jsonl` directly.** Other agents may
be writing in parallel; a shared file is not safe for concurrent writers.

Instead, write ALL your findings as JSON lines (one JSON object per line,
UTF-8, no trailing commas, one object per source/evidence item) to your
own file:

```
data/raw/incoming/MTS1-B.jsonl
```

Append to this file as you go (don't hold everything in memory until the
end — flush after every finding, so progress survives a crash).

## Record schema — every line must have ALL of these fields

```json
{
  "id": "MTS1-B-0001",
  "institution_name": "Full organization name",
  "institution_category": "one of: utility_iso_rto, utility_tso, utility_generation, utility_distribution, consultancy, vendor, academic_research, think_tank, industry_association, government_agency, government_regulator, international_body, development_bank, ngo_foundation, energy_company_diversified, project_developer, other",
  "official_website": "https://... (or empty string if unknown)",
  "country_label": "Canonical country name exactly as it appears in multi_tool_search_checklist.csv's country column -- do not invent a new spelling",
  "tool_name": "PLEXOS | PyPSA | PROMOD | Bid3 | SDDP",
  "tool_category": "one of: production_cost_uc, capacity_expansion, planning_expansion, market_simulation, energy_system_optimization, forecasting, distribution_planning, other",
  "tool_explicitly_named": true,
  "role": "one of: direct_user, commissioner, consultant_modeler, research_user, subject_of_study, qa_reviewer",
  "use_case": "A SPECIFIC sentence describing what the tool is actually used for, drawn from the real evidence -- not a generic placeholder like 'uses the tool for planning'. Specific text here is what lets this entry be classified as 'documented' rather than a weaker 'inferred' guess downstream.",
  "decision_type": "",
  "decision_basis": "",
  "evidence_strength": "HIGH | MEDIUM | LOW",
  "source_type": "e.g. research_finding, news_release, academic_paper, procurement_notice, official_methodology, tender_procurement",
  "source_title": "Title of the source document (or empty string)",
  "source_date": "Date of the source, free text (or empty string)",
  "source_url": "A real, working URL -- REQUIRED, never fabricate or guess one",
  "exact_snippet_or_quote": "A direct quote from the source supporting the claim -- strongly preferred, leave empty only if genuinely unavailable",
  "why_it_supports_the_claim": "One sentence connecting the quote/source to the claim",
  "status": "confirmed | candidate | rejected | gap_confirmed",
  "historical_or_current": "current | historical",
  "batch_id": "MTS1-B",
  "notes": "Caveats, reasoning, anything a reviewer should know"
}
```

Leave `decision_type` and `decision_basis` as empty strings always — the
pipeline computes them automatically.

## Evidence standards (non-negotiable)

1. **First-person evidence beats third-party mentions.** An
   organization's own planning document, press release, tender, or
   procurement record beats a vendor's case-study page naming them as a
   client.
2. **A direct quote beats a paraphrase.** Fill `exact_snippet_or_quote`
   whenever you have one.
3. **`status=confirmed` only if the evidence is solid.** Use
   `status=candidate` for a lead that needs a second look (weak/single
   source), and **always write a `status=gap_confirmed` row for a
   country+tool combination you genuinely searched and found nothing for**
   — this is just as valuable as a finding, since it tells the next wave
   not to repeat the same empty search. A `gap_confirmed` row doesn't need
   an institution name — use the tool name as a placeholder institution
   and note which techniques you tried in `notes`.
4. **No fabrication, ever.** If you cannot find a real, checkable URL, do
   not invent one and do not include the claim. When genuinely uncertain,
   use `status=candidate` and explain the uncertainty in `notes` — never
   silently upgrade confidence to look more complete.
5. **Don't use the generic PLEXOS catalogue role-template wording** (e.g.
   "Uses PLEXOS directly for its own grid/market planning or operations")
   as your `use_case` — write what the SPECIFIC evidence actually says the
   organization does.

## Search techniques, in priority order (be efficient — see pacing below)

1. The organization's own first-person documents (national planning
   documents, tender notices, press releases).
2. Multilateral development bank procurement-notice APIs (World Bank,
   IDB, ADB, AfDB) — especially productive for government/utility
   entities.
3. LinkedIn staff-profile and job-posting search for the tool name at a
   target organization.
4. Vendor case-study archives (treat as a LEAD only, verify with an
   independent second source before `status=confirmed`).
5. Non-English-language search in the country's own language(s) —
   English-only search misses real hits, especially in Latin America,
   Francophone Africa, and non-English Asia/Middle East.
6. Academic paper acknowledgements and author affiliations.

See `research/RESEARCH_PLAYBOOK.md` for the full detail and worked
examples of each technique.

## Pacing (loosened — this is the part that was too slow before)

**Try at most 2 search techniques per country+tool, not all 6.** Start
with technique 1 (first-person docs) and one other technique that seems
most promising for that specific country (e.g. technique 2 for a
government utility, technique 5 if English search is clearly thin). If
neither turns up anything, write `status=gap_confirmed` and move on —
don't keep digging. A later wave can always go deeper on a specific
gap; a full first pass across every country matters more right now than
exhaustive depth on any one of them.

**For small or clearly-unlikely countries** (e.g. small island states,
micro-states with no bulk power system of meaningful scale), it's fine
to do one combined quick search per country rather than 2 techniques ×
5 tools separately, and write `gap_confirmed` rows for all 5 tools at
once with a shared one-line `notes` explanation if nothing turns up.
Don't force the same depth of effort onto a 10,000-person island as a
major grid operator.

**Don't re-verify things you're already confident about.** If a vendor
case-study page plus one independent corroborating mention both point
the same way, that's enough for `status=confirmed` — you don't need a
third source.

The only hard rule that never loosens: never fabricate a URL or quote.
`candidate` or `gap_confirmed` are always fine outcomes; a fabricated
`confirmed` is not.

## Progress tracking (do this as you go, not just at the end)

After finishing ALL 5 tools for a country, update that country's row in
`research/multi_tool_search_checklist.csv`:
- Set each `{TOOL}_status` column to one of: `found_confirmed`,
  `found_candidate`, `no_evidence`.
- Set `overall_status` to `done` once all 5 tool columns are filled in.

This is how you (and anyone checking on you) can tell what's actually
been covered if the session is interrupted — update it after every single
country, not in a batch at the end.

## What "done" looks like

Every country assigned to you has `overall_status=done` in the checklist,
and every finding (confirmed, candidate, or gap_confirmed) is written to
`data/raw/incoming/MTS1-B.jsonl`. Do not run `npm run merge-batches`
yourself — that's a separate coordination step run once, after all
parallel batches finish, so it isn't a concurrent-write risk either.

Move at a steady, sustainable pace: 2 search techniques per country+tool
(fewer for clearly small/unlikely countries) is enough — see the Pacing
section above. The goal is a complete first pass across every assigned
country, with honest `gap_confirmed` rows where nothing was found,
rather than exhaustive depth on only the first few countries.
