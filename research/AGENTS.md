# AGENTS.md — research/

Before searching for new organizations, read `research/RESEARCH_PLAYBOOK.md`
in full — it has the search techniques that built this dataset. This file is just the auto-loaded
summary.

## The loop (short version)

1. Pick a gap from `world_country_checklist.csv` (`not_started` or
   `gap_confirmed` worth re-checking).
2. Search: try the organization's own first-person documents first
   (planning docs, procurement notices), then development-bank procurement
   APIs, then LinkedIn/vendor-archive/non-English-language search — see
   `RESEARCH_PLAYBOOK.md` for which have actually worked and why.
3. Add confirmed findings to `../data/raw/catalogue.jsonl` (one unified
   file for every tool) — see `../data/AGENTS.md`.
4. Update this folder's `world_country_checklist.csv` with the country's
   new status.
5. `npm run sync-data`, add a changelog entry, `npm run build`, commit.

## Running more than one agent at once

**Never write directly to `catalogue.jsonl` from multiple agents in
parallel** — see `RESEARCH_PLAYBOOK.md`'s "Running multiple research
agents in parallel" section for the full workflow. Short version: each
parallel worker gets a reserved unique id prefix and writes only to its
own file under `data/raw/incoming/`; one `npm run merge-batches` call
afterward consolidates everything with id-collision and duplicate
checking before anything touches `catalogue.jsonl`.

## Don't delete a rejected lead

A `status=rejected` row stays in `catalogue.jsonl` (not deleted) so a future wave
doesn't repeat the same dead-end search. See `RESEARCH_PLAYBOOK.md`'s
"stale negatives" section for when it's actually worth re-checking one.
