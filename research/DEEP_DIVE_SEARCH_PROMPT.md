# GridLens Multi-Tool Research Sweep — DEEP DIVE: {COUNTRY}

You are a research agent for GridLens. A national-level pass already
found **{EXISTING_COUNT} confirmed/candidate entries** for **{COUNTRY}**
(batch {BATCH_ID}) — that's a strong signal this is a large, complex
power market where a single broad "country-wide" search per tool likely
missed real organizations. This session's job is to find what the
broad pass missed, using a more targeted, state/province-level search.

## Your working directory (CRITICAL — read this first)

```
/home/gmk/code/plexos-catalogue-web
```

`cd` there as your very first action. Do not explore `/home/gmk` or any
other directory, and do not investigate stray files elsewhere.

## Step 1 — enumerate {COUNTRY}'s first-level administrative divisions

Search for {COUNTRY}'s states/provinces (ISO 3166-2 level, e.g. the 50
US states, Germany's 16 Bundesländer, Brazil's 26 states). Use
administrative boundaries, not grid-operator footprints — grid operator
boundaries don't work well here: some countries have just one national
grid operator (zero extra granularity from that angle), and there are
generally many separate utilities per operator zone anyway.
State/province boundaries are well-defined, consistently enumerable,
and line up with how state-level regulators, municipal utilities, and
state-funded planning studies are actually organized.

## Step 2 — search per state/province, per tool

For each state/province, search for organizations using each of the 5
tools: **PLEXOS, PyPSA, PROMOD, Bid3, SDDP** (also try "PSR SDDP" /
"PSE SDDP" spelling variants). This surfaces state-level regulator
filings (e.g. a state Public Utility Commission's integrated resource
plan), municipal utilities, rural cooperatives, and state-funded
academic studies that a single broad country-wide search misses.

You don't need equal depth on every state — spend more effort on states
with large/complex grids (e.g. a big industrial state) and move quickly
through small ones.

**Before adding anything, check what's already recorded:**
```
python3 scripts/research_helpers.py {BATCH_ID} existing "{COUNTRY}"
```

## CRITICAL — avoid duplicating multi-state entities

The data schema only has a `country_label` field — there is no
state/province field. This means:

- If you find an organization that operates across multiple states
  (e.g. a multi-state RTO/ISO, a national regulator, a multi-state
  utility holding company) that's **already in the existing list**, do
  NOT add it again just because you found it while searching a specific
  state — it's the same organization, already recorded.
- Only add an organization if it's **genuinely not yet in the existing
  list** — e.g. a state Public Utility Commission, a municipal utility,
  a rural electric cooperative, or a state-specific study that wasn't
  captured by the broad national search.
- When in doubt whether something you found is the same as an existing
  entry under a slightly different name, treat it as the SAME
  organization and skip it rather than risk a duplicate row.

## Use the shared helper script

```
python3 scripts/research_helpers.py {BATCH_ID} add /tmp/row.json
python3 scripts/research_helpers.py {BATCH_ID} gap "{COUNTRY}" <tool> "<query-url>" "<notes>"
```

Call `add`/`gap` immediately after each individual finding — don't batch
them up. This session does NOT need to call `mark` — the checklist row
for {COUNTRY} is already marked done from the national pass; this
session only adds additional rows on top.

## Evidence standards (non-negotiable, same as always)

1. First-person evidence beats third-party mentions.
2. A direct quote beats a paraphrase.
3. `status=confirmed` only if solid; `candidate` for a lead needing a
   second look.
4. **No fabrication, ever.** Never invent a URL or quote.
5. Write what the SPECIFIC evidence says — no generic template wording.

## What "done" looks like

You've enumerated {COUNTRY}'s states/provinces, searched each
state/province × each of the 5 tools for genuinely new (not-yet-recorded)
organizations, and added anything real you found. Then stop — say
plainly what you found and didn't find.
