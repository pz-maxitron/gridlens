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
}

/** Logo file in public/logos/, when we have a usable one (tool ecosystem for open source, vendor otherwise). */
const LOGOS = new Set(['antares', 'balmorel', 'bid3', 'digsilent-powerfactory', 'plexos', 'promod', 'pscad', 'pss-e', 'pypsa', 'sddp', 'sienna', 'times']);

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
