import changelogData from '../data/changelog.json';
import AboutTabs from './AboutTabs';

type Tag = 'added' | 'removed' | 'reclassified' | 'coverage';

interface Entry {
  date: string;
  tag: Tag;
  title: string;
  description: string;
}

const entries = changelogData as Entry[];

const TAGS: Record<Tag, { label: string; dot: string }> = {
  added: { label: 'Added', dot: 'bg-brand-400' },
  coverage: { label: 'Coverage', dot: 'bg-rose-400' },
  reclassified: { label: 'Reclassified', dot: 'bg-[#7fb3d5]' },
  removed: { label: 'Removed', dot: 'bg-ink-500' },
};

/** Extract the "Mon YYYY" key used for grouping entries. */
function groupKey(date: string): string {
  // "Oct–Nov 2026" → "Oct 2026"
  const match = date.match(/([A-Za-z]+)/);
  return match ? `${match[1]} ${date.slice(date.lastIndexOf(' '))}` : 'Unknown';
}

/** Entries grouped by month, newest month first. */
function groupedEntries(entries: Entry[]) {
  const map = new Map<string, Entry[]>();
  for (const e of entries) {
    const key = groupKey(e.date);
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(e);
  }
  // entries are already newest-first; sort months newest-first
  const monthOrder = [...map.keys()];
  const months = monthOrder.sort((a, b) => {
    const am = new Date(a + ' 1');
    const bm = new Date(b + ' 1');
    return bm.getTime() - am.getTime();
  });
  return months.map(m => ({ month: m, entries: map.get(m)! }));
}

/** What changed in the data, newest first. App-only changes are not listed. */
export default function Changelog() {
  const groups = groupedEntries(entries);
  return (
    <div>
      <AboutTabs current="/about/changelog" />
      <h1 className="font-display mt-10 text-5xl text-ink-50">Changelog</h1>
      <p className="mt-4 max-w-2xl text-lg text-ink-300">
        Every change to the data: organizations and projects added or removed, reclassified, or newly covered regions.
      </p>
      {groups.map((group, gi) => (
        <div key={gi} className="mt-10 max-w-3xl">
          <h2 className="font-display text-2xl text-ink-100">{group.month}</h2>
          <ol className="mt-6 border-l border-ink-800">
            {group.entries.map((e, i) => (
              <li key={i} className="relative pb-10 pl-8 last:pb-0">
                <span className={`absolute -left-[5px] top-2 h-2.5 w-2.5 rounded-full ${TAGS[e.tag].dot}`} aria-hidden="true" />
                <p className="flex flex-wrap items-baseline gap-x-3 text-xs text-ink-500">
                  <time>{e.date}</time>
                  <span className="uppercase tracking-[0.14em]">{TAGS[e.tag].label}</span>
                </p>
                <h3 className="font-display mt-1 text-2xl text-ink-50">{e.title}</h3>
                <p className="mt-2 leading-relaxed text-ink-300">{e.description}</p>
              </li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  );
}
