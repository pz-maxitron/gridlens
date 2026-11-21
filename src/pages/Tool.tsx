import { useMemo, useState, type ReactNode } from 'react';
import { ArrowUpRight } from 'lucide-react';
import { useChart } from '../lib/chartFilters';
import type { Filters } from '../types';
import { dateKey, formatDate } from '../lib/dates';
import { filtersToSearch } from '../lib/filterParams';
import { decisionOf, DECISION_INFO, OTHER_DECISION, organizationDirectory, projectsPerYear, serviceProviders } from '../lib/insights';
import { CONTRIBUTORS, contributorsInWindow, type Metric } from '../lib/contributors';
import { TOOLS, toolInfo, isOpenSource } from '../lib/tools';
import { projectImpact } from '../lib/impact';
import { orgGroupLabel } from '../lib/orgTypes';
import { categoryLabel, splitCategories } from '../lib/toolCategories';
import { toAtlasName } from '../lib/countryAliases';
import { OPEN_SOURCE, PROPRIETARY } from '../lib/colors';
import CoverageBar from '../components/charts/CoverageBar';
import { Link, slug } from '../lib/router';
import HorizontalBarChart from '../components/charts/HorizontalBarChart';
import WorldMap from '../components/charts/WorldMap';
import YearBars from '../components/charts/YearBars';
import ChartCard from '../components/chart/ChartCard';
import LicenseBadge from '../components/common/LicenseBadge';
import ToolLogo from '../components/common/ToolLogo';
import EmptyState from '../components/common/EmptyState';
import { ProjectRow } from '../sections/GridDecisions';
import { ContributionCaveat, ContributionSource, ContributorBars, MetricSwitch, windowMonths } from '../sections/Builders';
import { ProviderList } from '../sections/Providers';

const THIS_YEAR = new Date().getFullYear();

type Key = keyof Filters;
// A tool page is always about its tool: the tool and licence filters do not apply to it.
const TOOL_IGNORE: Key[] = ['toolName', 'license'];

/** The shared filters applied to this tool's projects, for one section (with `ignore` for filters it sets itself). */
function useToolRecords(id: string, name: string, ignore: Key[] = []) {
  const chart = useChart(id, [...TOOL_IGNORE, ...ignore]);
  const records = useMemo(() => chart.records.filter((r) => r.tool_name === name), [chart.records, name]);
  return { ...chart, records };
}

/** One section of the tool page: a card with its own filter button (filters are shared with the rest of the site). */
function Section({ id, name, title, note, fields, years = true, ignore = [], actions, className = '', children }: {
  id: string; name: string; title: string; note?: ReactNode; fields: Key[]; years?: boolean; ignore?: Key[]; actions?: ReactNode; className?: string; children: ReactNode;
}) {
  return (
    <section id={id} className={`scroll-mt-20 ${className}`}>
      <ChartCard id={id} title={title} description={note} fields={fields} years={years} ignore={[...TOOL_IGNORE, ...ignore]} actions={actions} className="flex h-full flex-col"
        scope={(r) => r.tool_name === name}>
        {children}
      </ChartCard>
    </section>
  );
}

const WHO: Key[] = ['country', 'period', 'sector', 'orgType', 'evidenceStrength', 'search'];

function Headline({ name }: { name: string }) {
  const info = toolInfo(name)!;
  const { records, catalogue } = useToolRecords('tool', name);
  const total = useMemo(() => catalogue.filter((r) => r.tool_name === name).length, [catalogue, name]);
  const orgs = useMemo(() => organizationDirectory(records).filter((o) => o.name !== info.vendor), [records, info.vendor]);
  const countries = new Set(records.flatMap((r) => r.countries)).size;
  return (
    <ChartCard id="tool" plain years fields={WHO} ignore={TOOL_IGNORE} scope={(r) => r.tool_name === name}
      description={records.length === total ? `All ${total.toLocaleString('en')} documented projects.` : `${records.length.toLocaleString('en')} of ${total.toLocaleString('en')} documented projects match the filters.`}>
      <dl className="grid grid-cols-2 gap-6 border-y border-ink-800/80 py-6 sm:grid-cols-4">
        {[
          [records.length, 'projects'],
          [orgs.length, 'organizations use it'],
          [orgs.filter((o) => o.group === 'grid_operator').length, 'of them grid or system operators', 'Transmission and distribution system operators, ISOs and RTOs.'],
          [countries, 'countries'],
        ].map(([v, l, t]) => (
          <div key={l as string} title={t as string | undefined}>
            <dd className="font-display tabular text-4xl text-ink-50 sm:text-5xl">{v}</dd>
            <dt className="mt-1 text-sm text-ink-400">{l}</dt>
          </div>
        ))}
      </dl>
    </ChartCard>
  );
}

function WhereSection({ name }: { name: string }) {
  // The map keeps every country visible so another one can be picked; the country filter only marks it.
  const { records, filters, setFilters } = useToolRecords('tool-map', name, ['country']);
  const countries = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of records) for (const c of r.countries) m.set(c, (m.get(c) ?? 0) + 1);
    return m;
  }, [records]);
  const atlas = useMemo(() => {
    const m = new Map<string, number>();
    for (const [c, n] of countries) m.set(toAtlasName(c), (m.get(toAtlasName(c)) ?? 0) + n);
    return m;
  }, [countries]);
  return (
    <Section name={name} id="tool-map" title="Where it is used" className="lg:col-span-2" ignore={['country']}
      note="Projects per country; regional and global studies count in every country they cover. Click a country to filter."
      fields={['period', 'sector', 'orgType', 'evidenceStrength', 'search']}>
      {records.length ? (
        <WorldMap valueByCountry={atlas} maxValue={Math.max(1, ...atlas.values())}
          selected={filters.country === 'All' ? undefined : toAtlasName(filters.country)}
          onSelect={(n) => { const c = [...countries.keys()].find((k) => toAtlasName(k) === n) ?? n; setFilters({ ...filters, country: filters.country === c ? 'All' : c }); }} />
      ) : <EmptyState />}
    </Section>
  );
}

function UsedForSection({ name, color }: { name: string; color: string }) {
  const { records } = useToolRecords('tool-purpose', name);
  const decisions = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of records) if (decisionOf(r) !== OTHER_DECISION) m.set(decisionOf(r), (m.get(decisionOf(r)) ?? 0) + 1);
    return [...m].map(([d, c]) => ({ name: DECISION_INFO[d]?.short ?? d, count: c })).sort((a, b) => b.count - a.count);
  }, [records]);
  // Projects whose source names no decision are counted below the bars, not as a bar that would dwarf the others.
  const unspecified = records.filter((r) => decisionOf(r) === OTHER_DECISION).length;
  return (
    <Section name={name} id="tool-purpose" title="Used for" note="Projects per kind of grid decision, where the source names one."
      fields={['country', 'period', 'sector', 'orgType', 'evidenceStrength']}>
      {decisions.length
        ? <HorizontalBarChart data={decisions} colorOf={() => color} unit="projects" />
        : <EmptyState title="No decision named in these projects’ sources" />}
      <CoverageBar known={records.length - unspecified} unknown={unspecified} knownLabel="projects with a named decision" unknownLabel="decision not specified, not shown" />
    </Section>
  );
}

function PerYearSection({ name, color }: { name: string; color: string }) {
  // A timeline: the study-year filter does not apply.
  const { records } = useToolRecords('tool-years', name, ['period', 'undated']);
  const undated = records.filter((r) => !r.year).length;
  return (
    <Section name={name} id="tool-years" title="Projects per year" years={false} ignore={['period', 'undated']}
      note={`Projects with a known year, ${THIS_YEAR - 14}–${THIS_YEAR}. ${THIS_YEAR} is still in progress.`}
      fields={['country', 'sector', 'orgType', 'evidenceStrength']}>
      <YearBars years={projectsPerYear(records, THIS_YEAR - 14, THIS_YEAR)} split={false} color={color} />
      <CoverageBar known={records.length - undated} unknown={undated} knownLabel="projects with a known year" unknownLabel="with an unknown year, not shown" />
    </Section>
  );
}

function UsersSection({ name }: { name: string }) {
  const info = toolInfo(name)!;
  const { records } = useToolRecords('tool-users', name);
  const orgs = useMemo(() => organizationDirectory(records).filter((o) => o.name !== info.vendor), [records, info.vendor]);
  return (
    <Section name={name} id="tool-users" title="Top users" note="Organizations with the most projects using this tool."
      fields={['country', 'period', 'sector', 'orgType']}>
      {orgs.length ? (
        <>
          <ul className="divide-y divide-ink-800/80">
            {orgs.slice(0, 10).map((o) => (
              <li key={o.name} className="-mx-2 flex items-baseline justify-between gap-4 rounded-lg px-2 py-2.5 text-sm transition-colors hover:bg-ink-800/40">
                <span className="min-w-0">
                  <span className="text-ink-100">{o.name}</span>
                  <span className="ml-2 text-xs text-ink-500">{orgGroupLabel(o.group)}</span>
                </span>
                <span className="tabular shrink-0 text-ink-400">{o.projects}</span>
              </li>
            ))}
          </ul>
          <Link href={`/organizations?tool=${encodeURIComponent(name)}`} className="mt-3 inline-block text-sm text-brand-300 hover:text-brand-200">All {orgs.length} organizations</Link>
        </>
      ) : <EmptyState />}
    </Section>
  );
}

function DecisionsSection({ name }: { name: string }) {
  const { records, filters } = useToolRecords('tool-decisions', name);
  const notable = useMemo(
    () => records
      .filter((r) => projectImpact(r) === 'high')
      .sort((a, b) => Number(decisionOf(a) === OTHER_DECISION) - Number(decisionOf(b) === OTHER_DECISION) || dateKey(b.date, b.year).localeCompare(dateKey(a.date, a.year)))
      .slice(0, 5),
    [records],
  );
  return (
    <Section name={name} id="tool-decisions" title="Real grid decisions" note="Latest projects in which a grid operator, utility, regulator or ministry used or commissioned the tool."
      fields={['country', 'period', 'sector', 'search']}>
      {notable.length ? <ul className="-my-4 divide-y divide-ink-800/80">{notable.map((r) => <ProjectRow key={r.project_id} r={r} />)}</ul> : <EmptyState title="None documented for these filters" />}
      <Link href={`/projects${filtersToSearch({ ...filters, toolName: name })}`} className="mt-3 inline-block text-sm text-brand-300 hover:text-brand-200">All {name} projects</Link>
    </Section>
  );
}

function BuildersSection({ name }: { name: string }) {
  const { filters } = useChart('tool-builders', TOOL_IGNORE);
  const [metric, setMetric] = useState<Metric>('prs');
  const builders = useMemo(() => contributorsInWindow([name], windowMonths(filters.period), CONTRIBUTORS, metric), [name, filters.period, metric]);
  return (
    <section id="builders" className="scroll-mt-20">
      <ChartCard id="tool-builders" className="h-full" title={`Who builds ${name}`} fields={['period']} years undatedNote={false} ignore={TOOL_IGNORE}
        description="Organizations whose people contribute most to the tool’s code in the chosen period, by the “Company” on their GitHub profile."
        actions={<MetricSwitch value={metric} onChange={setMetric} />}>
        <ContributorBars orgs={builders} metric={metric} />
        <ContributionSource tools={[name]} />
        <ContributionCaveat />
      </ChartCard>
    </section>
  );
}

function ProvidersSection({ name, wide }: { name: string; wide: boolean }) {
  const info = toolInfo(name)!;
  const { records } = useToolRecords('tool-providers', name);
  const providers = useMemo(() => serviceProviders(records), [records]);
  return (
    <Section name={name} id="tool-providers" className={wide ? 'lg:col-span-2' : ''} title={`Companies offering ${name} services`}
      note={`Consultancies with documented ${name} projects${isOpenSource(name) ? '' : `; ${info.vendor} itself is not listed`}.`}
      fields={['country', 'period']}>
      <ProviderList list={providers} />
    </Section>
  );
}

/** Everything known about one tool: who uses it for what and where, who builds it, who offers services. Each section has its own filters. */
function ToolProfile({ name }: { name: string }) {
  const info = toolInfo(name)!;
  const open = isOpenSource(name);
  const color = open ? OPEN_SOURCE : PROPRIETARY;
  const { catalogue } = useChart('tool', TOOL_IGNORE);
  const all = useMemo(() => catalogue.filter((r) => r.tool_name === name), [catalogue, name]);
  const gh = CONTRIBUTORS.tools[name];
  const categories = [...new Set(all.flatMap((r) => splitCategories(r.tool_category)))].filter((c) => c !== 'unspecified' && c !== 'other');

  return (
    <div>
      <header className="relative pb-10 pt-12 md:pt-16">
        <div className="pointer-events-none absolute -inset-x-40 -top-14 bottom-0 -z-10" aria-hidden="true"
          style={{ background: `radial-gradient(50rem 20rem at 30% 0%, ${color}33, transparent 70%)` }} />
        <div className="flex flex-col gap-6 md:flex-row md:items-end">
          <ToolLogo name={name} size={88} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <LicenseBadge tool={name} />
              {info.licenseName && <span className="text-xs text-ink-500">{info.licenseName}</span>}
              <Link href="/about#sources" className="text-xs text-ink-400 hover:text-ink-200" title="When GridLens last searched the web and publications for projects using this tool.">
                {info.last_searched ? <>Last searched <span className="text-ink-200">{formatDate(info.last_searched)}</span></> : 'No dedicated search yet'}
              </Link>
            </div>
            <h1 className="font-display mt-2 text-5xl text-ink-50 sm:text-7xl">{name}</h1>
            <p className="mt-2 max-w-2xl text-ink-300">
              {open ? 'Open-source' : 'Commercial'} tool by {info.vendor}
              {categories.length > 0 && <>, used for {categories.map(categoryLabel).join(', ').toLowerCase()}</>}.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <a href={info.url} target="_blank" rel="noreferrer" className="inline-flex h-10 items-center gap-1.5 rounded-full bg-ink-50 px-4 text-sm font-medium text-ink-950 hover:bg-white">
              Website <ArrowUpRight size={15} />
            </a>
            {gh && (
              <a href={`https://github.com/${gh.githubOrgs[0]}`} target="_blank" rel="noreferrer" className="inline-flex h-10 items-center gap-1.5 rounded-full border border-ink-700 px-4 text-sm text-ink-200 hover:border-ink-500">
                Code <ArrowUpRight size={15} />
              </a>
            )}
          </div>
        </div>
      </header>

      <Headline name={name} />
      {/* Two columns on wide screens; cards in a row share one height. */}
      <div className="mt-8 grid grid-cols-1 items-stretch gap-6 lg:grid-cols-2">
        <WhereSection name={name} />
        <UsedForSection name={name} color={color} />
        <PerYearSection name={name} color={color} />
        <UsersSection name={name} />
        <DecisionsSection name={name} />
        {gh ? <BuildersSection name={name} /> : null}
        <ProvidersSection name={name} wide={!gh} />
      </div>
    </div>
  );
}

export default function Tool({ tool }: { tool?: string }) {
  const name = TOOLS.find((t) => slug(t.name) === tool)?.name;
  if (!name) {
    return (
      <div className="pt-16">
        <p className="text-ink-300">No tool called “{tool}” is tracked.</p>
        <Link href="/" className="mt-4 inline-block text-brand-300">Back to the overview</Link>
      </div>
    );
  }
  return <ToolProfile key={name} name={name} />;
}
