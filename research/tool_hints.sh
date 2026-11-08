# Shared tool metadata for the GridLens multi-tool search drivers.
# Sourced by run_tool_search.sh and run_deep_dive_search.sh so the two
# don't drift out of sync with duplicated copies.
TOOLS=("PLEXOS" "PyPSA" "PROMOD" "Bid3" "SDDP")

declare -A TOOL_NOTE
TOOL_NOTE["PLEXOS"]="(Energy Exemplar)."
TOOL_NOTE["PyPSA"]="(the open-source tool)."
TOOL_NOTE["PROMOD"]="(PROMOD IV, Hitachi Energy / formerly ABB)."
TOOL_NOTE["Bid3"]="(Aurora Energy Research)."
TOOL_NOTE["SDDP"]="(PSR Energy Consulting's Stochastic Dual Dynamic Programming tool -- ALSO search \"PSR SDDP\" and \"PSE SDDP\" as variant spellings, since the exact vendor-name spelling is unconfirmed; treat all 3 as the same tool)."

# Concrete, tool-specific leverage found during a manual quality review of
# the US results -- see research/RESEARCH_PLAYBOOK.md's "Tool-specific
# high-leverage sources" section for the full detail/sourcing.
declare -A TOOL_HINT
TOOL_HINT["PLEXOS"]="Check for a vendor case-study page (Energy Exemplar) as a LEAD, then verify independently -- PLEXOS is the most broadly documented of the 5 tools, so a plain country-name search is usually enough."
TOOL_HINT["PyPSA"]="Look beyond academic/research maintainers for REGULATORY bodies quietly adopting it for official scenario work (a config file or demand scenario named after a real agency is a real signal), and check cross-industry landscape-assessment PDFs (GridLab/RMI-style open-source-vs-commercial comparisons) which often name several real adopters in one document."
TOOL_HINT["PROMOD"]="Check regional transmission organizations' own 'Market Efficiency' or planning-assumptions documents (first-party, usually a PDF) and government-funded national-lab report repositories (e.g. site:osti.gov in the US) for named regional consortium studies."
TOOL_HINT["Bid3"]="Search Aurora Energy Research's OWN resources/media/press pages directly (e.g. auroraer.com/resources) for dated, first-party press releases naming real deals/projects in this country -- this is stronger evidence than a generic third-party vendor case-study mention, and Aurora often has a country-specific legal entity worth searching by name too."
TOOL_HINT["SDDP"]="PSR's own marketing material lists deployment countries directly: Americas (all South/Central America, US, Canada, Dominican Republic), Europe (Austria, Spain, France, Scandinavia, Belgium, Turkey, Balkans), Asia (China provinces, India, Philippines, Singapore, Malaysia, Kyrgyzstan, Sri Lanka, Tajikistan, Vietnam), Oceania (New Zealand), Africa (Morocco, Tanzania, Namibia, Egypt, Angola, Sudan, Ethiopia, Ghana). If this country is on that list, treat it as a strong prior that SOME organization here uses SDDP -- search '<country> SDDP OR OptGen PSR' first, and also check regional planning councils' own 'modeling suite' presentations (first-party slide decks naming tools directly)."

# Short purpose/typical-user context per tool -- understanding WHY an
# organization would use a tool narrows down WHO to search for, far
# better than pattern-matching the tool name alone. Full detail in
# research/RESEARCH_PLAYBOOK.md's "Tool context" section.
declare -A TOOL_CONTEXT
TOOL_CONTEXT["PLEXOS"]="Integrated market simulation (production-cost modeling, capacity expansion, transmission planning). Typical users: system operators/ISOs/RTOs, utilities' IRP teams, regulators, generation owners/investors, and consultancies doing commissioned studies for any of those."
TOOL_CONTEXT["PyPSA"]="Free, Python-based, open-source power-system optimization toolbox. Academic/research-institute origin; increasingly adopted by universities, government-funded national labs, think tanks/NGOs doing decarbonization-pathway studies, and some regulators/utilities piloting it as a no-license-cost alternative."
TOOL_CONTEXT["PROMOD"]="Detailed hourly unit-commitment/dispatch and market simulation. Historically the dominant tool for North American ISO/RTO market studies (PJM, MISO, SPP, ERCOT, NYISO, ISO-NE) and US utility IRPs -- strongly North America-centric, lower prior elsewhere."
TOOL_CONTEXT["Bid3"]="Fundamental power-market modeling for price forecasting/asset valuation, used primarily BY AURORA ITSELF (a consultancy) to produce bespoke studies FOR clients (investors, developers, utilities, regulators). IMPORTANT: evidence is often 'Aurora did analysis for Client X using Bid3', not Client X owning a license -- both Aurora and the client can be legitimate separate rows. Strongest in Europe (UK, Germany, Nordics), expanding elsewhere."
TOOL_CONTEXT["SDDP"]="Stochastic dual dynamic programming for hydro-thermal scheduling and long-term expansion planning under hydrological uncertainty -- especially relevant for hydro-heavy grids. Typical users: national system operators (esp. where hydropower dominates, e.g. Brazil's ONS, which co-developed it), government energy-planning agencies, regional planning councils, utilities with major hydro assets."
