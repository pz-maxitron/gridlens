# North America base case — plan and audit

## Goal
Make North America (US, Canada, Mexico) a high-quality, re-searched **base case** for the worldwide multi-tool sweep, then open a PR to upstream with the updated North America data.

## Phase 1: pick the search method (running now)
- Blind evaluation B (agent) vs C (agent + critique pass) vs D (retrieval pipeline) on Germany/Chile/Ghana × PLEXOS/PyPSA/PROMOD/Bid3, on Qwen3.6-35B-A3B, scored against 21 hidden known organizations.
- Output: `research/eval/RESULTS.md`. Adoption rule fixed in advance: recall +10 points, validator VERIFIED share drop of at most 5 points, cost at most 1.5× B.

## Phase 2: re-search North America with the winning method
- US, Canada, Mexico × all 5 tools (PLEXOS, PyPSA, PROMOD, Bid3, PSR SDDP).
- Merge with the 27 rows already found by the MTS1-A per-tool pass (dedupe).

## Phase 3: upgrade the existing 85 North America catalogue rows
Audit findings (2026-11-08):
- [ ] **81/85 rows have no quote, source title, source date or official website** (legacy PLEXOS-era migration). Grounded enrichment pass: fetch the source, have Qwen extract a quote about the tool, and keep it only if code confirms it appears word for word on the page; also fill title/date/website.
- [ ] **12 university rows** (ORG-VMINE-0033…0071) cite only `energyexemplar.com/our-company/clients`, which is now **404**. Re-source with independent evidence (papers, theses, course pages), or downgrade to `candidate` with a note.
- [ ] Other dead links: NV Energy IRP, Synapse PUR-2024-00184, ACE ASEAN AIMS-III → **archived copies found on web.archive.org**, so switch to the archive URL and keep the original in notes. Constellation job ad (no archive; job ads expire) and B&V staff page → find replacement evidence or downgrade.
- [ ] 11 links blocked automated checks (osti.gov, ANL, Texas PUC, Avista, APS, OPPD). Verify with a browser-style fetch.
- [ ] **Country labels**: US split across 7 variants ("United States (Massachusetts)", "United States / Global", …). Normalize to `United States` and move the detail into notes so country filters count them.
- [ ] 4 rows with blank `institution_category`.
- [ ] 4 duplicate groups: MISO (ORG-NAM-0002 / ORG-VMINE-0009), University of Victoria (ORG-NAMD-0007 / ORG-VMINE-0071), Synapse (ORG-NAMD-0012 / ORG-CONSMIN3-0007 / -0008), SENER (ESM-0038 / ESM-0039). Merge, or keep only where the role or use case differs.
- [ ] Independent validator pass (anonymized) over every North America row, plus a human spot-check sample.

## Phase 4: PR
- Branch `data/north-america-base-case` from upstream `main` (no research-tooling noise).
- `merge-batches` → `validate-data` → `sync-data` → changelog entry → `build`.
- PR description: before/after quality metrics (quote/source coverage, dead links, verified share, tools covered).
