import { useMemo, useState } from 'react';
import { useChart } from '../lib/chartFilters';
import { DECISION_INFO, purposeMatrix } from '../lib/insights';
import { Link, navigate, slug } from '../lib/router';
import { isOpenSource } from '../lib/tools';
import ChartCard from '../components/chart/ChartCard';
import Segmented from '../components/chart/Segmented';
import EmptyState from '../components/common/EmptyState';
import ToolLogo from '../components/common/ToolLogo';

/** Which tools are used for which grid decision: a heat matrix of projects per tool and purpose. */
export default function PurposeMatrix() {
  const { records } = useChart('purpose');
  const [mode, setMode] = useState('count');
  // Hovered cell: its row and column are highlighted, everything else dims slightly.
  const [at, setAt] = useState<{ r: number; c: number } | null>(null);
  const m = useMemo(() => purposeMatrix(records), [records]);

  return (
    <ChartCard
      id="purpose"
      title="Which tool for which decision"
      description="Projects per tool and kind of grid decision. Hover a column for what it covers."
      fields={['country', 'period', 'sector', 'license', 'orgType', 'evidenceStrength', 'search']}
      actions={<Segmented label="Show" value={mode} onChange={setMode} options={[{ id: 'count', label: 'Projects' }, { id: 'share', label: '% of tool' }]} />}
    >
      {m.rows.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <table className="w-full min-w-[720px] border-separate border-spacing-[3px] text-sm" onMouseLeave={() => setAt(null)}>
            <thead>
              <tr>
                <th className="sticky left-0 z-10 bg-[#0c0f1b] pb-2 text-left align-bottom text-xs font-normal text-ink-500">Tool</th>
                {m.decisions.map((d, ci) => (
                  <th key={d} scope="col" className={`group relative w-[10%] px-1 pb-2 align-bottom text-xs font-medium leading-tight transition-colors ${at?.c === ci ? 'text-ink-50' : 'text-ink-300'}`}>
                    <span tabIndex={0} className="cursor-help underline decoration-ink-600 decoration-dotted underline-offset-4 outline-none group-hover:text-ink-50 focus:text-ink-50">
                      {DECISION_INFO[d]?.short ?? d}
                    </span>
                    <span role="tooltip" className="pointer-events-none absolute left-1/2 top-full z-20 mt-1 w-56 -translate-x-1/2 rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 text-left text-xs font-normal leading-relaxed text-ink-200 opacity-0 shadow-xl transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                      {DECISION_INFO[d]?.description}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {m.rows.map((row, ri) => (
                <tr key={row.tool}>
                  <th scope="row" className="sticky left-0 z-10 whitespace-nowrap bg-[#0c0f1b] pr-3 text-left font-normal">
                    <Link href={`/tools/${slug(row.tool)}`} className={`flex items-center gap-2 transition-colors hover:text-ink-50 ${at?.r === ri ? '!text-ink-50' : ''} ${isOpenSource(row.tool) ? 'text-brand-200' : 'text-ink-200'}`}>
                      <ToolLogo name={row.tool} size={20} />
                      {row.tool}
                    </Link>
                  </th>
                  {row.counts.map((c, j) => {
                    const share = row.total ? c / row.total : 0;
                    const strength = mode === 'share' ? share : Math.sqrt(c / m.max);
                    const label = mode === 'share' ? (c ? `${Math.round(share * 100)}%` : '') : c || '';
                    return (
                      <td key={j} onMouseEnter={() => setAt({ r: ri, c: j })} onClick={() => navigate(`/tools/${slug(row.tool)}${window.location.search}`)}
                        title={`${row.tool} · ${DECISION_INFO[m.decisions[j]]?.short ?? m.decisions[j]}: ${c} projects (${Math.round(share * 100)}% of ${row.tool}’s)`}
                        className={`tabular h-9 cursor-pointer rounded-[3px] text-center text-xs transition-[opacity,box-shadow] duration-150 ${
                          at && at.r !== ri && at.c !== j ? 'opacity-40' : ''} ${at?.r === ri && at?.c === j ? 'shadow-[0_0_0_2px_#f4efe6]' : ''}`}
                        style={{
                          background: c ? `rgba(242, 112, 63, ${0.1 + 0.8 * strength})` : 'rgba(31, 34, 52, 0.5)',
                          color: strength > 0.45 ? '#080a13' : '#cdcad3',
                        }}>
                        {label}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 h-5 text-sm text-ink-200" aria-live="polite">
        {at && (() => {
          const row = m.rows[at.r];
          const c = row.counts[at.c];
          return <><span className="text-ink-50">{row.tool}</span> · {DECISION_INFO[m.decisions[at.c]]?.short}: <span className="tabular text-brand-300">{c}</span> projects, {Math.round((100 * c) / row.total)}% of {row.tool}’s</>;
        })()}
      </p>
      <p className="mt-1 text-xs text-ink-500">
        <span className="sm:hidden">Swipe the table sideways for more decisions. </span>
        {mode === 'share' ? 'Percentages add up to 100% per tool. ' : ''}Projects without a stated decision are left out. Open-source tools are named in ember.
      </p>
    </ChartCard>
  );
}
