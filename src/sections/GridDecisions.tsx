import { useMemo, useState } from 'react';
import { ArrowUpRight } from 'lucide-react';
import type { CatalogueRecord } from '../types';
import ChartCard from '../components/chart/ChartCard';
import EmptyState from '../components/common/EmptyState';
import { useChart } from '../lib/chartFilters';
import { IMPACT_INFO, IMPACT_ORDER, projectImpact, rankProjects, type Impact } from '../lib/impact';
import { orgGroup, orgGroupLabel } from '../lib/orgTypes';
import { DECISION_INFO, DECISION_TYPES, decisionOf } from '../lib/insights';
import { Link, slug } from '../lib/router';
import { filtersToSearch } from '../lib/filterParams';

const IMPACT_DOT: Record<Impact, string> = { high: 'bg-brand-400', medium: 'bg-rose-400', low: 'bg-ink-500' };
const PAGE = 6;

function ImpactMark({ impact }: { impact: Impact }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ink-400" title={IMPACT_INFO[impact].description}>
      <span className={`h-2 w-2 rounded-full ${IMPACT_DOT[impact]}`} aria-hidden="true" />
      {IMPACT_INFO[impact].label}
    </span>
  );
}

export function ProjectRow({ r }: { r: CatalogueRecord }) {
  const text = r.summary.trim() || r.use_case.trim();
  const where = r.geo_scope === 'national'
    ? r.country_label
    : `${r.geo_scope === 'global' ? 'Global' : r.region_label || (r.countries.length > 1 ? r.countries.slice(0, 4).join(', ') : 'Multi-country')} study`;
  return (
    <li className="-mx-3 grid gap-2 rounded-xl px-3 py-4 transition-colors hover:bg-ink-800/40 sm:grid-cols-[1fr_auto] sm:gap-6">
      <div className="min-w-0">
        <p className="text-ink-50">
          {r.organizations.map((o, k) => (
            <span key={o.name}>
              {k > 0 && <span className="text-ink-600"> · </span>}
              {o.name}
              {o.role !== 'direct_user' && <span className="text-ink-500"> ({o.role.replace(/_/g, ' ')})</span>}
            </span>
          ))}
        </p>
        <p className="mt-1 text-xs text-ink-500">
          {[r.year, <Link key="t" href={`/tools/${slug(r.tool_name)}`} className="text-ink-300 hover:text-ink-50">{r.tool_name}</Link>,
            <span key="w" title={r.countries.join(', ')}>{where}</span>, orgGroupLabel(orgGroup(r)),
            r.decision_basis !== 'documented' ? 'decision inferred' : null]
            .filter(Boolean)
            .map((x, i) => <span key={i}>{i > 0 && ' · '}{x}</span>)}
        </p>
        {text && <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-300">{text}</p>}
      </div>
      <div className="flex items-center gap-4 sm:flex-col sm:items-end sm:gap-2">
        <ImpactMark impact={projectImpact(r)} />
        {r.sources[0]?.link && (
          <a href={r.sources[0].link.trim()} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-brand-300 hover:text-brand-200">
            Source <ArrowUpRight size={12} />
          </a>
        )}
      </div>
    </li>
  );
}

/**
 * The grid decisions the tools support, one decision type at a time, highest impact first.
 * With a country filter, that country's own studies come before multi-country and global ones.
 */
export default function GridDecisions() {
  const { filters, records } = useChart('decisions');
  const country = filters.country === 'All' ? undefined : filters.country;
  const counts = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of records) m.set(decisionOf(r), (m.get(decisionOf(r)) ?? 0) + 1);
    return m;
  }, [records]);
  const types = DECISION_TYPES.filter((d) => counts.get(d));
  const [picked, setPicked] = useState('All');
  const type = picked === 'All' || counts.get(picked) ? picked : 'All';
  const [shown, setShown] = useState(PAGE);
  const ranked = useMemo(
    () => rankProjects(type === 'All' ? records : records.filter((r) => decisionOf(r) === type), country),
    [records, type, country],
  );

  const tab = (id: string, label: string, n: number) => (
    <button key={id} type="button" role="tab" aria-selected={type === id} onClick={() => { setPicked(id); setShown(PAGE); }}
      className={`shrink-0 rounded-full px-3 py-1.5 text-sm transition-colors ${type === id ? 'bg-ink-50 text-ink-950' : 'text-ink-400 hover:bg-ink-800/70 hover:text-ink-100'}`}>
      {label} <span className={`tabular ml-1 text-xs ${type === id ? 'text-ink-600' : 'text-ink-600'}`}>{n}</span>
    </button>
  );

  return (
    <ChartCard
      id="decisions"
      title="Grid decisions"
      description="What the tools are actually used to decide, with the most consequential examples first: projects in which a grid operator, utility, regulator or ministry used or commissioned the modelling."
    >
      {records.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <div role="tablist" aria-label="Decision type" className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 [scrollbar-width:none]">
            {tab('All', 'All decisions', records.length)}
            {types.map((d) => tab(d, DECISION_INFO[d]?.short ?? d, counts.get(d)!))}
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-b border-ink-800/80 pb-3">
            <p className="text-sm text-ink-400">{type === 'All' ? 'All projects, highest impact first.' : DECISION_INFO[type]?.description}</p>
            <div className="flex gap-4">{IMPACT_ORDER.map((i) => <ImpactMark key={i} impact={i} />)}</div>
          </div>
          <ul className="divide-y divide-ink-800/80">
            {ranked.slice(0, shown).map((r) => <ProjectRow key={`${r.project_id}-${r.tool_name}`} r={r} />)}
          </ul>
          <div className="mt-2 flex flex-wrap gap-2">
            {shown < ranked.length && (
              <button type="button" onClick={() => setShown((n) => n + PAGE * 2)} className="h-9 rounded-full border border-ink-700 px-4 text-xs text-ink-300 hover:text-ink-50">
                Show more ({ranked.length - shown} left)
              </button>
            )}
            <Link href={`/projects${filtersToSearch(filters)}`}
              className="flex h-9 items-center rounded-full px-4 text-xs text-ink-400 hover:text-ink-50">
              Open in the project table
            </Link>
          </div>
        </>
      )}
    </ChartCard>
  );
}
