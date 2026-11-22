# Changelog maintenance

GridLens's landing page and `/about/changelog` page show a feed of **dataset
content changes only** — new organizations, removed organizations, role
reclassifications, and country-coverage expansions. It deliberately does
**not** show app/UI changes (new features, redesigns, bug fixes, icon
changes, etc.): it is modeled directly on artificialanalysis.ai's own `/changelog`, which is 100% new
models/evaluations/methodology updates, zero entries about their own site's
UI.

## When to add an entry

Whenever the underlying dataset changes in one of these ways, add a new
entry to `src/data/changelog.json` in the **same commit/session** as the
data change:

- A new organization is added to the catalogue (confirmed direct_user,
  commissioner, consultant_modeler, researcher, or subject_of_study role)
- An organization is removed (evidence didn't hold up on review)
- An organization's role/classification is corrected (e.g. consultant_modeler
  -> research_user, or a rejected->confirmed reversal)
- Country coverage changes (new countries added to the tracked checklist,
  or a country's status changes)

Do **not** add an entry for: UI redesigns, new app features/pages, bug
fixes, performance work, dependency bumps, copy/grammar fixes. Those are
normal commits, not changelog-worthy.

## Entry format

Each entry in `src/data/changelog.json`:
```json
{
  "date": "7 Nov 2026",
  "tag": "added",
  "title": "UPME (Colombia) confirmed as a PLEXOS direct user",
  "description": "One sentence: what changed and the evidence/reason, specific enough to be useful."
}
```
- `tag` is one of: `added` (new org), `removed`, `reclassified`, `coverage`
  (country-list changes). Add a new tag + its style in
  `src/pages/Changelog.tsx`'s `TAGS` map if a genuinely
  new category is needed — don't force an awkward fit into the existing 4.
- `date` uses real, known dates (`D Mon YYYY`) pulled from the actual
  change record (e.g. the commit or pull request that changed the data).
  Never invent a specific day you don't actually know — fall back to a
  month or range (`"Oct–Nov 2026"`) instead of fabricating false precision.
- `title` should name the actual organization/entity, not a vague summary
  ("GRIDCo (Ghana Grid Company Limited) added", not "New African entity
  added").
- New entries go at the **top** of the array (most recent first) — the
  component doesn't sort, it trusts array order.

## Where the source of truth lives

`data/raw/catalogue.jsonl` in this repo is the dataset; there is no other
copy. Write the changelog entry from the rows you add, remove or change in
that file (organization names, countries, dates), not from memory.
