# GridLens

[![CI](https://github.com/open-energy-transition/gridlens/actions/workflows/ci.yml/badge.svg)](https://github.com/open-energy-transition/gridlens/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)
[![Node](https://img.shields.io/badge/node-%3E%3D20-brightgreen.svg)](.nvmrc)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![AI-agent ready](https://img.shields.io/badge/AI%20agent-ready-blueviolet.svg)](AGENTS.md)

*Which tools model the grid, who uses them, and for which decisions.*

Live at **[gridlens.org](https://gridlens.org)**. GridLens collects public
evidence of which energy system models grid operators, utilities,
regulators, consultancies and researchers use, from PLEXOS to PyPSA:
thousands of documented projects for the tools in `src/data/tools.json`,
each with the organizations, countries, grid decision and a source.
Built and maintained by [Open Energy Transition](https://openenergytransition.org/).
Fully client-side: no backend, no database, no paid APIs, no API keys —
everything runs in the browser against a static dataset.

This repo is the **canonical public home** for both the app and the
dataset behind it.

## Why this repo is designed the way it is

The dataset is never finished. Organizations adopt, drop, or switch tools;
new case studies surface; existing entries get corrected or removed as
evidence is re-checked. That's expected to keep happening — by human
contributors, and by scheduled LLM research agents running the same
playbook this dataset was originally built with. So the repo is structured
so **anyone, with their own AI coding agent and zero other context, can
clone it and start contributing immediately**:

- **`AGENTS.md`** is the single entry point for an AI agent: repo map,
  commands, both contribution workflows (data + app), and the
  non-negotiables (evidence standards, no backend, changelog discipline).
- **`data/DATA_SCHEMA.md`** documents every field and enum value of
  `data/raw/catalogue.jsonl`, the one file a new finding goes into.
- **`research/RESEARCH_PLAYBOOK.md`** distills the actual search techniques
  behind the dataset — not generic advice, but what specifically worked (development-bank
  procurement APIs, non-English source search, stale-negative re-checking,
  and why).
- **`scripts/validate_dataset.py`** + **`scripts/sync_dataset.py`** turn a
  catalogue edit into a working app update deterministically — no manual
  pandas wrangling required.

See **`CONTRIBUTING.md`** for the concrete how-to, whichever kind of
contribution you're making.

## Quick start

```bash
npm install
npm run dev          # http://localhost:5173
```

```bash
npm run build          # type-check (tsc -b) + production build into dist/
npm run test            # vitest, pure-logic regression tests
npm run validate-data   # check data/raw/catalogue.jsonl before syncing
npm run sync-data       # validate, then regenerate data/catalogue_merged.csv + src/data/catalogue.json
```

Requirements: Node.js — version pinned in `.nvmrc` (`nvm use`), tested with
v26 — and npm (tested with v11). Python 3 stdlib only for the two data
scripts above (`csv`/`json`, no installs needed).

See `DEPLOYMENT.md` for how to actually publish a build (GitHub Pages,
Vercel, Netlify, or any static host — it's a zero-backend static app).

## What's inside the app

- **Overview** — most adopted tools, which tool for which grid decision,
  projects per year, a world map, notable grid decisions and who builds
  the open-source tools, plus the latest dataset changes.
- **Tool pages** (`/tools/<tool>`) — where a tool is used, for what, by
  whom, its real grid decisions, its code contributors and service
  providers.
- **Organizations** — every organization with its type, tools, countries
  and latest project; searchable and sortable.
- **Projects & data** — the full table with configurable columns; its
  download button exports the filtered projects as CSV.
- **About** — methodology and sources, plus Changelog, Contact and Legal.

Filters (country, years, tool, sector, grid decision, impact…) are shared
by every chart and kept in the URL together with each chart's own
settings, so any view can be shared as a link. Every chart has copy link,
download image (PNG) and download data (CSV) buttons.

## Repository layout

```
AGENTS.md                      AI agent entry point — read this first
CONTRIBUTING.md                Human contribution guide
CHANGELOG_MAINTENANCE.md       src/data/changelog.json convention
DEPLOYMENT.md                  How to publish a build (GitHub Pages / Vercel / Netlify / any static host)
.nvmrc                         Pinned Node version

data/
  AGENTS.md                      entry point for data agents
  raw/catalogue.jsonl            The entire dataset, one JSON object per line — edit to add any finding
  raw/incoming/                   Staging dir for parallel research batches (see merge_batches.py)
  schema.json                     machine-checkable field contract (required fields, enums)
  catalogue_merged.csv            generated, do not hand-edit
  DATA_SCHEMA.md                  field reference + evidence standards
  contributor_orgs.json           GitHub company names mapped to organizations (code contributions)

research/
  AGENTS.md                       entry point for research agents
  RESEARCH_PLAYBOOK.md            proven search techniques + taxonomy discipline + parallel-agent workflow
  world_country_checklist.csv     per-country coverage tracker
  known_institutions.csv          generated on demand for research agents (npm run export-known-institutions), not committed

scripts/
  validate_dataset.py              schema/enum/duplicate/alias checks
  sync_dataset.py                  regenerates the merged dataset + the app's bundled JSON
  merge_batches.py                 merges parallel research batches into catalogue.jsonl
  export_known_institutions.py     exports research/known_institutions.csv
  fetch_contributors.py            refreshes src/data/contributors.json (code contributions per organization, from GitHub)

src/                              React + TypeScript app (Vite + Tailwind v4)
  data/catalogue.json              generated, what the app actually imports
  data/changelog.json              dataset-change feed shown in the app
  data/tools.json                  the tracked tools (vendor, licence, categories, last search)
  types.ts, App.tsx, lib/, components/, sections/, pages/
```

## Tech stack

React 19 + TypeScript + Vite + Tailwind v4 + Recharts + `react-simple-maps`
(world map from Natural Earth via `world-atlas`, served from `public/geo/`)
+ `lucide-react` + `html-to-image` (chart PNG export, loaded on click).
No state-management library; a small router in `src/lib/router.tsx` gives
every page a real path, and the build writes one `index.html` per page so
GitHub Pages serves each with status 200.

## License

MIT, for both the code and the dataset — see `LICENSE`.
