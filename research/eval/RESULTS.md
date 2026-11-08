# Blind search-method evaluation: B vs C vs D

Test countries: Germany, Chile, Ghana. Tools: PLEXOS, PyPSA, PROMOD, Bid3 (SDDP excluded).
Ground truth: 21 known organizations from the catalogue (hidden from all methods).

## Summary

| Variant | Recall of known orgs | Novel orgs | Unique orgs | Validator VERIFIED | Minutes | Min per verified row | Crashed sessions |
|---|---|---|---|---|---|---|---|
| B (agent, current prompt) | 0/21 (0%) | 0 | 0 | - | 0 | - | 0 |
| C (B + critique pass) | 0/21 (0%) | 0 | 0 | - | 0 | - | 0 |
| D (retrieval pipeline) | 0/21 (0%) | 0 | 0 | - | 0 | - | 0 |

Adoption rule (agreed up front): a variant replaces B only if recall improves by >=10 points,
VERIFIED share drops by <=5 points, and minutes per verified finding is <=1.5x B's.

## Per country/tool (for manual review of the fuzzy name matching)

| Variant | Country | Tool | Known found | Matched known orgs | Novel orgs [validator verdict] |
|---|---|---|---|---|---|
| B | Chile | PLEXOS | 0/5 | - | - |
| B | Ghana | PLEXOS | 0/3 | - | - |
| B | Germany | PyPSA | 0/5 | - | - |
| B | Germany | PLEXOS | 0/8 | - | - |
| C | Chile | PLEXOS | 0/5 | - | - |
| C | Ghana | PLEXOS | 0/3 | - | - |
| C | Germany | PyPSA | 0/5 | - | - |
| C | Germany | PLEXOS | 0/8 | - | - |
| D | Chile | PLEXOS | 0/5 | - | - |
| D | Ghana | PLEXOS | 0/3 | - | - |
| D | Germany | PyPSA | 0/5 | - | - |
| D | Germany | PLEXOS | 0/8 | - | - |
