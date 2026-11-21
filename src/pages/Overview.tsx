import { useMemo, type ReactNode } from 'react';
import { ArrowRight } from 'lucide-react';
import type { CatalogueRecord } from '../types';
import { Link, slug as toolSlug } from '../lib/router';
import { openShare } from '../lib/insights';
import { catalogueUpdated, isOpenSource, searchFreshness } from '../lib/tools';
import { formatDate } from '../lib/dates';
import AdoptionRanking from '../components/common/AdoptionRanking';
import changelog from '../data/changelog.json';
import PurposeMatrix from '../sections/PurposeMatrix';
import Momentum from '../sections/Momentum';
import Geographic from '../sections/Geographic';
import GridDecisions from '../sections/GridDecisions';
import Builders from '../sections/Builders';

const THIS_YEAR = new Date().getFullYear();

function Section({ id, n, title, children }: { id: string; n: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20" aria-labelledby={`${id}-h`}>
      <h2 id={`${id}-h`} className="mb-4 flex items-baseline gap-3 text-ink-400">
        <span className="font-mono text-xs text-brand-400">{n}</span>
        <span className="text-xs uppercase tracking-[0.14em]">{title}</span>
      </h2>
      {children}
    </section>
  );
}

/** Starting points by reader: each opens a section with filters already set (shareable URLs). */
const PATHS = [
  { who: 'Funders', what: 'Where open tools already shape real grid decisions', href: '/?decisions.license=open_source#decisions' },
  { who: 'Grid operators & utilities', what: 'What your peers use, and for which decisions', href: '/?adoption.sector=industry#adoption' },
  { who: 'Industry', what: 'Organizations that build the open-source tools', href: '/#builders' },
  { who: 'Researchers', what: 'Every project with its sources, as CSV', href: '/projects' },
];

/** When the catalogue was last searched; hover or tap for each tool's last search, stalest first. */
function CatalogueUpdated() {
  const updated = catalogueUpdated();
  if (!updated) return null;
  return (
    <div className="group relative mt-6 w-fit text-sm text-ink-400">
      <button type="button" className="underline decoration-ink-700 decoration-dotted underline-offset-4 hover:text-ink-200">
        Catalogue updated <span className="text-ink-200">{formatDate(updated)}</span>
      </button>
      <div role="tooltip" className="invisible absolute left-0 top-full z-30 mt-2 w-72 rounded-xl border border-ink-800 bg-ink-950 p-4 opacity-0 shadow-2xl transition-opacity group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100">
        <p className="mb-2 text-xs uppercase tracking-[0.14em] text-ink-500">Last search per tool</p>
        <ul className="space-y-1">
          {searchFreshness().map((t) => (
            <li key={t.name} className="flex justify-between gap-4 text-xs">
              <Link href={`/tools/${toolSlug(t.name)}`} className="text-ink-200 hover:text-brand-200">{t.name}</Link>
              <span className={t.lastSearched ? 'tabular text-ink-400' : 'text-ink-500'}>{t.lastSearched ? formatDate(t.lastSearched) : 'not yet'}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function Overview({ catalogue }: { catalogue: CatalogueRecord[] }) {
  const facts = useMemo(() => {
    const orgs = new Set(catalogue.flatMap((r) => r.organizations.map((o) => o.name)));
    const now = openShare(catalogue, THIS_YEAR - 1, THIS_YEAR - 1);
    const then = openShare(catalogue, THIS_YEAR - 6, THIS_YEAR - 6);
    return {
      projects: catalogue.length,
      countries: new Set(catalogue.flatMap((r) => r.countries)).size,
      organizations: orgs.size,
      tools: new Set(catalogue.map((r) => r.tool_name)).size,
      openTools: new Set(catalogue.filter((r) => isOpenSource(r.tool_name)).map((r) => r.tool_name)).size,
      openNow: now === null ? null : Math.round(now * 100),
      openThen: then === null ? null : Math.round(then * 100),
    };
  }, [catalogue]);

  return (
    <div className="space-y-16 pt-10 md:space-y-20 md:pt-16">
      <div className="grid grid-cols-1 gap-12 xl:grid-cols-[1fr_20rem]">
      <header className="max-w-4xl">
        <p className="mb-5 text-xs uppercase tracking-[0.18em] text-ink-400">An open record of energy-model use</p>
        <h1 className="font-display text-[2.6rem] leading-[1.05] text-ink-50 sm:text-6xl">
          Who models the grid, <span className="text-glow italic">with which tools</span>, for which decisions.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ink-300">
          GridLens collects public evidence of how grid operators, utilities, regulators, consultancies and
          researchers use energy system models, from PLEXOS to PyPSA, so you can see what is trusted where.
        </p>
        <dl className="mt-10 grid grid-cols-2 gap-x-8 gap-y-6 sm:flex sm:flex-wrap sm:gap-x-12">
          {[
            [facts.projects.toLocaleString('en'), 'projects'],
            [facts.organizations.toLocaleString('en'), 'organizations'],
            [facts.countries, 'countries'],
            [`${facts.tools}`, `tools, ${facts.openTools} open source`],
          ].map(([v, l]) => (
            <div key={l}>
              <dd className="font-display text-4xl text-ink-50 sm:text-5xl">{v}</dd>
              <dt className="mt-1 text-sm text-ink-400">{l}</dt>
            </div>
          ))}
        </dl>
        <CatalogueUpdated />
        {facts.openNow !== null && (
          <p className="mt-8 text-sm text-ink-400">
            <span className="text-brand-300">{facts.openNow}%</span> of {THIS_YEAR - 1}’s projects used an open-source tool
            {facts.openThen !== null && <>, {facts.openNow >= facts.openThen ? 'up' : 'down'} from {facts.openThen}% in {THIS_YEAR - 6}</>}.{' '}
            <a href="#momentum" className="text-ink-200 underline decoration-ink-600 underline-offset-4 hover:decoration-brand-500">See the trend</a>
          </p>
        )}
      </header>
      <aside aria-label="Latest changes" className="self-start rounded-2xl border border-ink-800/80 bg-ink-900/40 p-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xs uppercase tracking-[0.14em] text-ink-400">Latest in the data</h2>
          <Link href="/about/changelog" className="text-xs text-ink-400 hover:text-ink-100">All changes</Link>
        </div>
        <ol className="mt-4 space-y-4 border-l border-ink-800 pl-4">
          {(changelog as { date: string; title: string }[]).slice(0, 4).map((e) => (
            <li key={e.title} className="relative">
              <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-brand-500/80" aria-hidden="true" />
              <p className="text-xs text-ink-500">{e.date}</p>
              <p className="mt-0.5 text-sm leading-snug text-ink-200">{e.title}</p>
            </li>
          ))}
        </ol>
      </aside>
      </div>

      <nav aria-label="Start here" className="grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-ink-800/80 bg-ink-800/80 sm:grid-cols-2 xl:grid-cols-4">
        {PATHS.map((p) => (
          <Link key={p.who} href={p.href} className="group flex flex-col gap-2 bg-ink-950/85 p-5 transition-colors hover:bg-ink-900">
            <span className="text-xs uppercase tracking-[0.14em] text-ink-500">{p.who}</span>
            <span className="text-ink-100">{p.what}</span>
            <ArrowRight size={16} className="mt-auto text-ink-600 transition-transform group-hover:translate-x-1 group-hover:text-brand-400" />
          </Link>
        ))}
      </nav>

      <Section id="adoption" n="01" title="Adoption"><AdoptionRanking /></Section>
      <Section id="purpose" n="02" title="Tools by purpose"><PurposeMatrix /></Section>
      <Section id="momentum" n="03" title="Momentum"><Momentum /></Section>
      <Section id="map" n="04" title="Where"><Geographic /></Section>
      <Section id="decisions" n="05" title="Grid decisions"><GridDecisions /></Section>
      <Section id="builders" n="06" title="Who builds open source"><Builders /></Section>

      <section className="grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-ink-800/80 bg-ink-800/80 md:grid-cols-3">
        {[
          { href: '/tools/pypsa', title: 'Tool profiles', text: 'Each tool’s users, decisions, countries, builders and service providers in one place.' },
          { href: '/organizations', title: 'Organizations', text: 'All organizations with the tools they use, filterable by type.' },
          { href: '/about', title: 'Methodology', text: 'Where the evidence comes from, how it is checked, and its limits.' },
        ].map((c) => (
          <Link key={c.href} href={c.href} className="group bg-ink-950/85 p-6 transition-colors hover:bg-ink-900">
            <p className="font-display text-2xl text-ink-50">{c.title}</p>
            <p className="mt-2 text-sm text-ink-400">{c.text}</p>
            <ArrowRight size={16} className="mt-4 text-ink-600 transition-transform group-hover:translate-x-1 group-hover:text-brand-400" />
          </Link>
        ))}
      </section>
    </div>
  );
}
