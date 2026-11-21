import toolsData from '../data/tools.json';

export interface ToolInfo {
  name: string;
  vendor: string;
  license: 'open_source' | 'proprietary';
  licenseName?: string;
  url: string;
  /** GitHub organizations holding the tool's ecosystem of repositories (open-source tools). */
  github_orgs?: string[];
  /** What the tool is built for (ids from toolCategories.ts). */
  categories: string[];
  /** Day (YYYY-MM-DD) its projects were last searched for; absent if it has had no dedicated search yet. */
  last_searched?: string;
}

/** Logo file in public/logos/, when we have a usable one (tool ecosystem for open source, vendor otherwise). */
const LOGOS = new Set(['antares', 'balmorel', 'bid3', 'digsilent-powerfactory', 'plexos', 'promod', 'pscad', 'powsybl', 'pss-e', 'pypsa', 'sddp', 'sienna', 'times']);

export function logoOf(slug: string): string | undefined {
  return LOGOS.has(slug) ? `/logos/${slug}.png` : undefined;
}

/** The tools GridLens tracks (src/data/tools.json); sync_dataset.py publishes only these. */
export const TOOLS = toolsData as ToolInfo[];
const BY_NAME = new Map(TOOLS.map((t) => [t.name, t]));

export function toolInfo(name: string): ToolInfo | undefined {
  return BY_NAME.get(name);
}

export function isOpenSource(name: string): boolean {
  return BY_NAME.get(name)?.license === 'open_source';
}

export const LICENSE_LABELS: Record<string, string> = {
  open_source: 'Open source',
  proprietary: 'Proprietary',
};

/** The tools by when they were last searched, oldest first; never-searched tools first of all. */
export function searchFreshness(tools: ToolInfo[] = TOOLS): { name: string; lastSearched?: string }[] {
  return tools
    .map((t) => ({ name: t.name, lastSearched: t.last_searched }))
    .sort((a, b) => (a.lastSearched ?? '').localeCompare(b.lastSearched ?? '') || a.name.localeCompare(b.name));
}

/** The most recent search of any tool: when the catalogue was last updated. */
export function catalogueUpdated(tools: ToolInfo[] = TOOLS): string | undefined {
  return tools.map((t) => t.last_searched).filter(Boolean).sort().at(-1);
}
