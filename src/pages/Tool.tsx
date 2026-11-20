import { useMemo, useState, type ReactNode } from 'react';
import { ArrowUpRight } from 'lucide-react';
import { useChart } from '../lib/chartFilters';
import { decisionOf, DECISION_INFO, OTHER_DECISION, organizationDirectory, projectsPerYear, serviceProviders } from '../lib/insights';
import { CONTRIBUTORS, contributorsInWindow } from '../lib/contributors';
import { TOOLS, toolInfo, isOpenSource } from '../lib/tools';
import { projectImpact } from '../lib/impact';
import { orgGroupLabel } from '../lib/orgTypes';
import { categoryLabel, splitCategories } from '../lib/toolCategories';
import { toAtlasName } from '../lib/countryAliases';
import { OPEN_SOURCE, PROPRIETARY } from '../lib/colors';
import { Link, slug } from '../lib/router';
import HorizontalBarChart from '../components/charts/HorizontalBarChart';
import WorldMap from '../components/charts/WorldMap';
import YearBars from '../components/charts/YearBars';
import ChartCard, { ALL_FIELDS } from '../components/chart/ChartCard';
import LicenseBadge from '../components/common/LicenseBadge';
import ToolLogo from '../components/common/ToolLogo';
import EmptyState from '../components/common/EmptyState';
import { ProjectRow } from '../sections/GridDecisions';
import { ContributionCaveat, ContributionSource, ContributorBars, WindowSlider } from '../sections/Builders';
import { ProviderList } from '../sections/Providers';

const THIS_YEAR = new Date().getFullYear();

function Panel({ id, title, note, children, className = '' }: { id?: string; title: string; note?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section id={id} className={`scroll-mt-20 rounded-2xl border border-ink-800/80 bg-ink-900/40 p-4 sm:p-6 ${className}`}>
      <h2 className="font-display mb-1 text-xl text-ink-50">{title}</h2>
      {note && <p className="mb-4 text-sm text-ink-400">{note}</p>}
      {children}
    </section>
  );
}

/** Everything known about one tool: who uses it for what and where, who builds it, who offers services. */
function ToolProfile({ name }: { name: string }) {
  const info = toolInfo(name)!;
  const open = isOpenSource(name);
  const color = open ? OPEN_SOURCE : PROPRIETARY;
  const { records: filtered, catalogue, filters, setFilters } = useChart('tool', ['toolName', 'license']);
  const records = useMemo(() => filtered.filter((r) => r.tool_name === name), [filtered, name]);
  const total = useMemo(() => catalogue.filter((r) => r.tool_name === name).length, [catalogue, name]);

  const orgs = useMemo(() => organizationDirectory(records).filter((o) => o.name !== info.vendor), [records, info.vendor]);
  const gridOperators = orgs.filter((o) => o.group === 'grid_operator').length;
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
  const decisions = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of records) if (decisionOf(r) !== OTHER_DECISION) m.set(decisionOf(r), (m.get(decisionOf(r)) ?? 0) + 1);
    return [...m].map(([d, c]) => ({ name: DECISION_INFO[d]?.short ?? d, count: c })).sort((a, b) => b.count - a.count);
  }, [records]);
  const notable = useMemo(
    () => records
      .filter((r) => projectImpact(r) === 'high')
      .sort((a, b) => Number(decisionOf(a) === OTHER_DECISION) - Number(decisionOf(b) === OTHER_DECISION) || (b.year ?? 0) - (a.year ?? 0))
      .slice(0, 5),
    [records],
  );
  const providers = useMemo(() => serviceProviders(records), [records]);
  const [months, setMonths] = useState(12);
  const builders = useMemo(() => contributorsInWindow([name], months), [name, months]);
  const gh = CONTRIBUTORS.tools[name];
  const categories = [...new Set(records.flatMap((r) => splitCategories(r.tool_category)))].filter((c) => c !== 'unspecified' && c !== 'other');

  return (
    <div>
      <header className="relative pb-10 pt-12 md:pt-16">
        <div className="pointer-events-none absolute -inset-x-40 -top-14 bottom-0 -z-10" aria-hidden="true"
          style={{ background: `radial-gradient(50rem 20rem at 30% 0%, ${color}33, transparent 70%)` }} />
        <div className="flex flex-col gap-6 md:flex-row md:items-end">
          <ToolLogo name={name} size={88} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3"><LicenseBadge tool={name} />{info.licenseName && <span className="text-xs text-ink-500">{info.licenseName}</span>}</div>
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

      <ChartCard id="tool" plain ignore={['toolName', 'license']} fields={ALL_FIELDS.filter((f) => f !== 'toolName' && f !== 'license')}
        description={records.length === total ? `${total === 1 ? 'One documented project' : `All ${total} documented projects`}. Filter by country, period, sector or type of organization.` : `${records.length} of ${total} projects match the filters.`}>
        <dl className="grid grid-cols-2 gap-6 border-y border-ink-800/80 py-6 sm:grid-cols-4">
          {[
            [records.length, 'projects'],
            [orgs.length, 'organizations use it'],
            [gridOperators, 'of them grid or system operators', 'Transmission and distribution system operators, ISOs and RTOs.'],
            [countries.size, 'countries'],
          ].map(([v, l, t]) => (
            <div key={l as string} title={t as string | undefined}>
              <dd className="font-display tabular text-4xl text-ink-50 sm:text-5xl">{v}</dd>
              <dt className="mt-1 text-sm text-ink-400">{l}</dt>
            </div>
          ))}
        </dl>

        {records.length === 0 ? (
          <div className="mt-8"><EmptyState /></div>
        ) : (
          <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel title="Where it is used" note="Projects per country; regional and global studies count in every country they cover." className="lg:col-span-2">
              <WorldMap valueByCountry={atlas} maxValue={Math.max(1, ...atlas.values())}
                selected={filters.country === 'All' ? undefined : toAtlasName(filters.country)}
                onSelect={(n) => { const c = [...countries.keys()].find((k) => toAtlasName(k) === n) ?? n; setFilters({ ...filters, country: filters.country === c ? 'All' : c }); }} />
            </Panel>
            <Panel title="Used for" note="Projects per kind of grid decision, where the source names one.">
              {decisions.length ? <HorizontalBarChart data={decisions} colorOf={() => color} unit="projects" /> : <p className="text-sm text-ink-500">No decision stated in the sources yet.</p>}
            </Panel>
            <Panel title="Projects per year" note={`Projects with a known year, ${THIS_YEAR - 14}–${THIS_YEAR}. ${THIS_YEAR} is still in progress.`}>
              <YearBars years={projectsPerYear(records, THIS_YEAR - 14, THIS_YEAR)} split={false} color={color} />
            </Panel>
            <Panel title="Top users" note="Organizations with the most projects using this tool.">
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
            </Panel>
            <Panel title="Real grid decisions" note="Latest projects in which a grid operator, utility, regulator or ministry used or commissioned the tool.">
              {notable.length ? <ul className="-my-4 divide-y divide-ink-800/80">{notable.map((r) => <ProjectRow key={r.project_id} r={r} />)}</ul> : <p className="text-sm text-ink-500">None documented yet.</p>}
              <Link href={`/projects?projects.tool=${encodeURIComponent(name)}`} className="mt-3 inline-block text-sm text-brand-300 hover:text-brand-200">All {total} projects</Link>
            </Panel>
          </div>
        )}
      </ChartCard>

      {gh && (
        <div className="mt-6">
          <Panel id="builders" title={`Who builds ${name}`}
            note="Organizations whose people had the most pull requests merged into the tool’s code in the chosen period.">
            <div className="mb-4 flex"><WindowSlider months={months} onChange={setMonths} /></div>
            <ContributorBars orgs={builders} />
            <ContributionSource tools={[name]} />
            <ContributionCaveat />
          </Panel>
        </div>
      )}
      <div className="mt-6">
        <Panel title={`Companies offering ${name} services`} note={`Consultancies with documented ${name} projects${open ? '' : `; ${info.vendor} itself is not listed`}.`}>
          <ProviderList list={providers} />
        </Panel>
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
