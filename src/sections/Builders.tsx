import { useMemo, useState } from 'react';
import { ArrowUpRight } from 'lucide-react';
import { contributorsInWindow, CONTRIBUTORS, WINDOWS, windowLabel, type ContributorOrg } from '../lib/contributors';
import { Link, slug } from '../lib/router';
import { isOpenSource, TOOLS, toolInfo } from '../lib/tools';
import { useChart } from '../lib/chartFilters';
import ChartCard from '../components/chart/ChartCard';
import EmptyState from '../components/common/EmptyState';
import ToolLogo from '../components/common/ToolLogo';

const OPEN_TOOLS = TOOLS.filter((t) => t.license === 'open_source' && CONTRIBUTORS.tools[t.name]).map((t) => t.name);
const SHOWN = 12;
/** The filter panel offers only the open-source tools with code data, and their categories. */
const CHOICES = {
  toolNames: OPEN_TOOLS,
  toolCategories: [...new Set(OPEN_TOOLS.flatMap((t) => toolInfo(t)!.categories))],
};

/** The caveat shown with every contribution ranking. */
export function ContributionCaveat() {
  return (
    <p className="mt-5 border-l-2 border-ink-700 pl-3 text-xs leading-relaxed text-ink-500">
      A hint, not a verdict. Merged pull requests count only one kind of work, in these GitHub organizations, and only for
      people who name an employer on their profile. Reviews, issues, documentation, teaching, funding and the many upstream
      and downstream projects these tools depend on are not counted. Every contribution to open source is valuable.
    </p>
  );
}

/** Slider over the contribution window: 3 months to 10 years. */
export function WindowSlider({ months, onChange }: { months: number; onChange: (m: number) => void }) {
  const i = Math.max(0, WINDOWS.indexOf(months));
  return (
    <label className="flex min-w-0 flex-1 basis-64 items-center gap-3 text-xs text-ink-400 sm:min-w-72">
      <span className="shrink-0">Last</span>
      <input
        type="range" min={0} max={WINDOWS.length - 1} step={1} value={i}
        onChange={(e) => onChange(WINDOWS[Number(e.target.value)])}
        aria-valuetext={windowLabel(months)}
        className="h-1.5 min-w-0 flex-1 cursor-pointer appearance-none rounded-full bg-ink-800 accent-brand-500"
      />
      <span className="tabular w-20 shrink-0 text-sm text-ink-100">{windowLabel(months)}</span>
    </label>
  );
}

/** Organizations ranked by pull requests merged in the window; each name links to the organization. */
export function ContributorBars({ orgs, showTools, limit = SHOWN }: { orgs: ContributorOrg[]; showTools?: boolean; limit?: number }) {
  const [all, setAll] = useState(false);
  if (orgs.length === 0) return <EmptyState title="No contributions from named organizations in this period" message="Widen the time window." />;
  const shown = all ? orgs : orgs.slice(0, limit);
  const max = Math.max(1, ...orgs.map((o) => o.prs));
  return (
    <>
      <ol className="group/list space-y-3 sm:space-y-1">
        {shown.map((o, i) => (
          <li key={o.name}
            className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1.5 rounded-lg px-2 py-1 transition-[opacity,background-color] hover:bg-ink-800/50 group-hover/list:opacity-50 hover:!opacity-100 sm:grid-cols-[minmax(12rem,20rem)_1fr_auto]">
            <span className="flex min-w-0 items-center gap-3 text-sm">
              <span className="tabular w-5 shrink-0 text-xs text-ink-600">{i + 1}</span>
              <span className="min-w-0">
                {o.url ? (
                  <a href={o.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-ink-100 underline decoration-ink-700 underline-offset-4 hover:text-ink-50 hover:decoration-brand-500">
                    {o.name}<ArrowUpRight size={12} className="shrink-0 text-ink-500" />
                  </a>
                ) : <span className="text-ink-100">{o.name}</span>}
                {showTools && (
                  <span className="mt-0.5 flex flex-wrap gap-x-2">
                    {o.tools.map((t) => <Link key={t} href={`/tools/${slug(t)}`} className="text-[11px] text-ink-500 hover:text-ink-200">{t}</Link>)}
                  </span>
                )}
              </span>
            </span>
            <span className="tabular whitespace-nowrap text-right text-xs text-ink-400 sm:order-last sm:w-44 self-start sm:self-center">
              <span className="text-sm text-ink-100">{o.prs.toLocaleString('en')}</span> <span className="sm:hidden">PRs</span><span className="hidden sm:inline">merged PRs · {o.people} {o.people === 1 ? 'person' : 'people'}</span>
            </span>
            <div className="col-span-2 h-1.5 rounded-sm bg-ink-800/60 sm:col-span-1 sm:h-[18px]" aria-hidden="true">
              <div className="h-full rounded-sm bg-gradient-to-r from-brand-600 to-brand-400 transition-[width] duration-500" style={{ width: `${Math.max(1.5, (100 * o.prs) / max)}%` }} />
            </div>
          </li>
        ))}
      </ol>
      {orgs.length > limit && (
        <button type="button" onClick={() => setAll((a) => !a)} className="mt-4 h-9 rounded-full border border-ink-700 px-4 text-xs text-ink-300 hover:text-ink-50">
          {all ? 'Show fewer' : `Show all ${orgs.length}`}
        </button>
      )}
    </>
  );
}

/** Where the counted pull requests come from, and when the data was fetched. */
export function ContributionSource({ tools }: { tools: string[] }) {
  const orgs = tools.flatMap((t) => CONTRIBUTORS.tools[t]?.githubOrgs ?? []);
  const repos = tools.reduce((n, t) => n + (CONTRIBUTORS.tools[t]?.repositories ?? 0), 0);
  return (
    <p className="mt-3 text-xs text-ink-500">
      Pull requests merged into {repos} repositories of{' '}
      {orgs.map((o, i) => (
        <span key={o}>{i > 0 && (i === orgs.length - 1 ? ' and ' : ', ')}<a className="text-ink-300 hover:text-ink-100" href={`https://github.com/${o}`} target="_blank" rel="noreferrer">github.com/{o}</a></span>
      ))}
      , by the organization on each author’s public GitHub profile. Updated {CONTRIBUTORS.generated}.
    </p>
  );
}

/**
 * Who builds the open-source tools: organizations ranked by their people's pull requests merged into each
 * tool's GitHub organizations over a window the reader picks (default 12 months). The tool, tool-category and
 * licence filters apply; others (country, sector…) say nothing about who writes the code.
 */
export default function Builders() {
  const { filters } = useChart('builders');
  const [months, setMonths] = useState(12);
  const tools = OPEN_TOOLS.filter((t) =>
    (filters.toolName === 'All' || filters.toolName === t) &&
    (filters.toolCategory === 'All' || toolInfo(t)!.categories.includes(filters.toolCategory)) &&
    filters.license !== 'proprietary');
  const key = tools.join();
  const orgs = useMemo(() => contributorsInWindow(tools, months), [key, months]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <ChartCard
      id="builders"
      title="Who builds the open-source tools"
      description="Organizations whose people had the most pull requests merged into each tool’s code. Working with them also supports the tools everyone uses."
      fields={['toolName', 'toolCategory', 'license']}
      choices={CHOICES}
      actions={<WindowSlider months={months} onChange={setMonths} />}
    >
      {(['country', 'sector', 'orgType', 'period'] as const).some((k) => filters[k] !== 'All') && (
        <p className="mb-4 text-xs text-ink-500">Code contributions are not tied to a country, sector or study year, so those filters don’t change this ranking.</p>
      )}
      {tools.length === 0 ? (
        <EmptyState title="No open-source tool matches these filters"
          message={filters.toolName !== 'All' && !isOpenSource(filters.toolName) ? `${filters.toolName} is proprietary: its code and contributors are not public.` : 'Change the tool or category filter.'} />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2">
            {tools.map((t) => (
              <Link key={t} href={`/tools/${slug(t)}#builders`} className="flex items-center gap-1.5 text-xs text-ink-400 hover:text-ink-50">
                <ToolLogo name={t} size={16} />{t}
              </Link>
            ))}
          </div>
          <ContributorBars orgs={orgs} showTools={tools.length > 1} />
          <ContributionSource tools={tools} />
        </>
      )}
      <ContributionCaveat />
    </ChartCard>
  );
}
