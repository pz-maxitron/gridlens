# Research playbook

How to find, verify, and add new organizations to the dataset — distilled
from ~25 research waves (Nov 2026) that grew the PLEXOS-specific dataset
from 0 to 419 confirmed organizations across 149 countries. Written for an
LLM agent (or a human) picking this up cold, with no other context.

## The loop

1. Pick a gap: an untracked country, a tool/region/sector not yet covered,
   or a `status=rejected`/`gap_confirmed` row worth re-checking (see "stale
   negatives" below).
2. Search using one or more of the techniques below. Prefer techniques that
   haven't been tried yet for this gap over repeating an exhausted one.
3. For each finding, write down: the organization, the country, the role
   (see `data/DATA_SCHEMA.md`), the source URL, and — critically — enough
   of a quote/paraphrase in `notes` that a future reviewer doesn't have to
   re-fetch the source to understand why it counts as evidence.
4. Append one JSON line to `data/raw/catalogue.jsonl` (one unified file
   for every tool, not just PLEXOS) with
   `status=confirmed` only if the evidence is solid; use `status=candidate`
   for a lead that needs a second look, `status=rejected` for a dead end
   (keep it, don't delete — see below).
5. Update `research/world_country_checklist.csv`: mark the country's
   `checklist_status` (`covered` / `gap_confirmed` / `candidate_pending` /
   `not_started`).
6. Run `npm run validate-data` then `npm run sync-data`.
7. Add an entry to `src/data/changelog.json` per `CHANGELOG_MAINTENANCE.md`
   — every add/remove/reclassify gets a dated entry there, in the same
   session as the data change.
8. `npm run build` to confirm nothing broke, then commit everything
   together (raw CSV diff + regenerated merged CSV/JSON + changelog entry).

## Tool context — what each tool actually is (read before searching)

Understanding *why* an organization would use a tool narrows down *who*
to search for far better than pattern-matching the tool's name alone:

- **PLEXOS (Energy Exemplar)** — integrated market simulation:
  production-cost modeling, capacity expansion, transmission planning.
  Typical users: system operators/ISOs/RTOs (market design/adequacy
  studies), utilities' long-term resource-planning (IRP) teams, energy
  regulators, generation owners/investors (asset valuation), and
  consultancies doing commissioned studies for any of the above. Look in:
  IRP filings, system adequacy studies, generation/transmission expansion
  plans.
- **PyPSA (open source)** — free, Python-based power-system optimization
  toolbox (capacity expansion + dispatch). Academic/research-institute
  origin; increasingly adopted by universities, government-funded
  national labs, think tanks/NGOs doing decarbonization-pathway studies,
  and — more recently — regulators/utilities piloting it as a
  no-license-cost alternative. Look in: academic energy-system papers,
  government "net zero"/pathway scenario reports, GitHub forks
  configuring PyPSA for a specific country.
- **PROMOD (PROMOD IV, Hitachi Energy, formerly ABB)** — detailed hourly
  unit-commitment/dispatch and market simulation. Historically the
  dominant tool for North American ISO/RTO market studies (PJM, MISO,
  SPP, ERCOT, NYISO, ISO-NE) and US utility IRPs. Strongly North
  America-centric — lower prior elsewhere, though multinational
  consultancies sometimes use it for studies outside NA.
- **Bid3 (Aurora Energy Research)** — fundamental power-market modeling
  for price forecasting and asset valuation, used primarily BY AURORA
  ITSELF as a consultancy to produce bespoke studies FOR clients
  (investors, developers, utilities, regulators). **Important nuance:**
  evidence is often "Aurora performed analysis for Client X using Bid3",
  not Client X owning a Bid3 license — both Aurora (as
  consultant_modeler/direct_user) and the client (as
  commissioner/subject_of_study) can be legitimate separate rows per the
  schema. Strongest presence in Europe (UK, Germany, Nordics) but
  expanding — check Aurora's regional office pages per country.
- **SDDP (PSR)** — stochastic dual dynamic programming for hydro-thermal
  scheduling and long-term expansion planning under hydrological
  uncertainty — especially relevant for hydro-heavy grids. Typical users:
  national system operators (especially where hydropower dominates, e.g.
  Brazil's ONS, which co-developed it), government energy-planning
  agencies, regional planning councils, utilities with major hydro
  assets. PSR's own deployment-country list (below) is a strong prior.

## Search methodology (preferred order, not just technique list)

A researcher doesn't just type "<tool> <country>" into a search box — that
style of query mostly surfaces generic listicles and third-party
mentions. Work in this order instead:

1. **Entity-first.** Enumerate the country's known grid operator(s),
   major utilities, and energy regulator BEFORE searching for the tool.
   Then search those specific entities' own technical documents (IRPs,
   system studies, tender notices, "methodology" sections) for the tool
   name — `"<entity name>" "<tool name>"`, or `site:<entity's own
   domain> <tool name>` if the domain is known. This is the single
   strongest evidence class (see technique #1 below) and the reason it's
   listed first here too.
2. **Industry conference proceedings.** Utility/ISO engineers present
   real case studies at technical conferences, routinely naming their
   tools in methodology sections — a much higher signal-to-noise source
   than generic search:
   - **ESIG** (Energy Systems Integration Group) — `site:esig.energy
     <tool name>`.
   - **IEEE PES** (Power & Energy Society) — search `"<tool name>" IEEE
     PES <country>` or `site:ieeexplore.ieee.org <tool name> <country>`.
   - **CIGRE** (International Council on Large Electric Systems) —
     search `"<tool name>" CIGRE <country>`.
3. **Official vendor references** — case studies, client lists, webinar
   recordings (see techniques #4/#7/#10 below). Useful as a *lead*, not
   final evidence on their own (except the vendor's own deployment-country
   lists, which are a reasonable prior for where to look, not proof of a
   specific organization).
4. **Generic web search** (tool name + country) — try this last; it's the
   lowest signal-to-noise of the four and mostly surfaces the same
   third-party mentions a more targeted search would catch with a cleaner
   hit.

## Search techniques that have actually worked

Roughly in order of how much they've produced, based on this dataset's
build history:

1. **The organization's own first-person documents.** National grid
   operators, regulators, and utilities often publish their own planning
   documents, tender notices, or press releases stating which tool they use
   ("la UPME adquirió la herramienta PLEXOS" — Colombia's own 2020-2034
   expansion plan). This is the strongest evidence class and should be
   tried first, not last.
2. **Multilateral development bank procurement-notice APIs.** The World
   Bank's structured API
   (`search.worldbank.org/api/v2/procnotices?qterm=PLEXOS`) returns an
   authoritative, exhaustive count — not a sample — and was the single most
   productive technique discovered in this project (found GRIDCo/Ghana,
   confirmed Pakistan/Senegal/Indonesia entities, and definitively closed
   out large swaths of the search space as genuine negatives). IDB has a
   similar CKAN-based open-data API (`data.iadb.org`). ADB and AfDB have
   procurement databases but are harder to query programmatically
   (client-side JS / bot-protection / CSRF forms as of Nov 2026 — may be
   easier from a different network/browser environment; worth retrying
   rather than assuming still-blocked).
3. **LinkedIn staff-profile and job-posting search.** Searching for staff
   job titles/descriptions mentioning the tool by name at a target
   organization. Effective for confirming direct use when no public
   document exists.
4. **Vendor case-study archives.** Tool vendors (Energy Exemplar for
   PLEXOS, etc.) publish client case studies — useful as a *lead*, but
   weaker evidence than the organization's own words; verify with a second,
   independent source before marking `status=confirmed` on a vendor
   mention alone.
5. **Non-English-language search.** Searching national planning documents
   in the country's own language (Spanish, Portuguese, French, Arabic,
   etc.) found real hits in Latin America and Francophone Africa that
   English-only queries missed entirely. If a country's own-language
   government/utility planning-document site exists, searching it directly
   in that language is worth trying before giving up on a country.
6. **Academic paper acknowledgements/author affiliations.** Papers citing a
   country's PLEXOS model often credit the commissioning agency or the
   consultancy that built it in the acknowledgements, even when neither has
   a public-facing announcement.
7. **Vendor's own case-study/press pages, browsed directly, not just
   searched generically.** Searching "Bid3 Aurora Energy Research
   <country>" tends to surface weak/generic case studies elsewhere, but
   the vendor's own `/resources` or `/media` section (e.g.
   `auroraer.com/resources/aurora-insights`) carries dated, first-party,
   specific press releases naming real transactions and markets — found a
   confirmed-quality lead (a named US financing deal, three named states)
   this way that generic search missed entirely.
8. **Government-funded national-lab report repositories.** In the US,
   `site:osti.gov <tool name>` surfaces DOE-funded collaborative studies
   that explicitly name the modeling tool used, often for a named regional
   consortium (e.g. a SERC-region study using PROMOD). Most countries have
   an analogous public repository (a national energy research institute,
   a government open-data portal) — worth searching directly by name
   rather than only generic web search.
9. **Regional planning body's own "modeling suite" presentations.**
   Regional transmission/grid planning councils (e.g. the US Northwest
   Power and Conservation Council) publish their own slide decks naming
   every tool in their modeling suite by name and vendor — a single PDF
   can confirm a tool's usage with a direct first-party quote. Search
   `"<regional council name>" modeling suite OR "production cost"
   <tool name>`.
10. **The vendor's OWN marketing material listing deployment countries.**
    Some vendors (notably PSR, maker of SDDP) publish their own slide
    decks/brochures that list every country or region where their tool is
    deployed, in one place — see "SDDP: known deployment countries" below.
    This is a high-leverage shortcut: check for this kind of document for
    each of the 5 tools before assuming a country-by-country sweep is the
    only way to find leads.

## Tool-specific high-leverage sources (found during the US multi-tool wave)

- **SDDP (PSR)**: PSR's own marketing material ("Stochastic Programming
  Models for Energy Planning", psr-inc.com) explicitly lists deployment
  countries: **Americas** — all of South and Central America, United
  States, Canada, Dominican Republic. **Europe** — Austria, Spain, France,
  Scandinavia, Belgium, Turkey, the Balkans. **Asia** — provinces in China
  (Shanghai, Sichuan, Guangdong, Shandong), India, Philippines, Singapore,
  Malaysia, Kyrgyzstan, Sri Lanka, Tajikistan, Vietnam. **Oceania** — New
  Zealand. **Africa** — Morocco, Tanzania, Namibia, Egypt, Angola, Sudan,
  Ethiopia, Ghana. Treat this as a strong prior, not a substitute for
  verification: it confirms SDDP usage SOMEWHERE in that country, but the
  specific organization still needs to be found and cited per the normal
  evidence standards (search `"<country>" SDDP OR OptGen PSR` as the first
  technique for any of these countries).
- **PyPSA**: beyond the project's own academic maintainers, check for
  regulatory bodies quietly adopting it for official scenario work (e.g. a
  GitHub changelog config file named after a real agency's demand
  scenario is a real signal, not noise) and cross-industry "landscape
  assessment" PDFs (GridLab/RMI-style reports comparing open-source vs.
  commercial tools) which often name several real adopters in one
  document across multiple tools at once, not just PyPSA.
- **Bid3 (Aurora Energy Research)**: Aurora itself has country-specific
  legal entities (e.g. "Aurora Energy Research LLC (USA)") that do direct
  market-analytics work locally — their own press releases name specific
  deals/projects/states, which is stronger evidence than a generic vendor
  case-study mention of a third-party client.
- **PROMOD (Hitachi Energy)**: regional transmission organizations'
  "Market Efficiency" analysis documents (PJM-style) are a reliable
  first-party source, and DOE OSTI reports often name a named regional
  consortium using it for a specific study.

## Role taxonomy discipline

See `data/DATA_SCHEMA.md` for the full definitions. The two mistakes this
project made and fixed:
- `subject_of_study` was initially never used (an unwritten "exclude rather
  than subject_of_study" convention had calcified across early batches) —
  it's a legitimate role for an organization passively modeled in someone
  else's study. Don't over-apply it either: only use it when there's no
  plausible direct-user/commissioner role for the same organization.
- `consultant_modeler` vs. `research_user` is a judgment call when an
  academic institution works alongside a commissioning agency as a
  co-equal partner rather than a hired vendor — lean `research_user` in
  that case (see the NEXT Group/South Korea reclassification in
  `src/data/changelog.json`).

## Stale negatives: when to re-check a rejection

A `status=rejected` or `gap_confirmed` row is not necessarily permanent.
Re-check when:
- A new search technique becomes available that wasn't tried before (e.g.
  a country was searched 4 times in English and rejected, but never in its
  own language — this reversed Colombia/UPME after 4 prior negatives).
- Significant time has passed and the organization may have adopted the
  tool since the last check.
Don't re-check a rejection with the *same* technique that already produced
it — that just re-confirms the same negative and wastes effort.

## Avoiding duplicates

Before adding a row, check `research/known_institutions.csv` (regenerate
it fresh with `npm run export-known-institutions` before a new wave) for
the same institution name (watch for alias spellings — "National Grid ESO"
renamed to "NESO", abbreviations vs. full names) and the same country
under a different spelling (`scripts/validate_dataset.py` flags known
alias clusters, but new ones can appear — add them to the
`COUNTRY_ALIASES` list in that script if found). This file is also what
you should hand to every parallel research agent as context in the
workflow below, so they don't waste effort re-finding (or, worse,
near-duplicating under a slightly different name) organizations that are
already confirmed.

## Running multiple research agents in parallel

Never have more than one agent write directly to `data/raw/catalogue.jsonl`
at the same time — concurrent writers to one file is a real corruption
risk (interleaved writes, lost updates). Instead:

1. **Before dispatching**, run `npm run export-known-institutions` fresh
   and give every worker the resulting `research/known_institutions.csv`
   as context (see "Avoiding duplicates" above).
2. **Reserve each worker a unique id prefix** up front, e.g. `W23-A-`,
   `W23-B-`, `W23-C-` for wave 23's three workers. Tell each worker to id
   its new rows `W23-A-0001`, `W23-A-0002`, etc. — unique prefixes make
   id collisions between workers impossible even with zero coordination
   while they run.
3. **Each worker writes only to its own file** under
   `data/raw/incoming/`, e.g. `data/raw/incoming/W23-A.jsonl` — never to
   `catalogue.jsonl` directly. See `data/raw/incoming/README.md`.
4. **Once every worker finishes**, run `npm run merge-batches` ONCE (not
   per-worker) — it checks every staged file for id collisions and likely
   institution+tool+country duplicates (against both each other and the
   existing catalogue) before writing anything, and aborts cleanly with no
   partial write if it finds a collision.
5. Then the normal pipeline: `npm run validate-data && npm run sync-data`,
   changelog entry, `npm run build`, commit.

## What "done" looks like for a research wave

Every country in `research/world_country_checklist.csv` has been searched
at least once (even a confirmed `gap_confirmed` is progress — it means a
future wave doesn't have to start from zero). A wave is genuinely
exhausted, not abandoned early, when multiple independent techniques (not
just one repeated) have come up empty.
