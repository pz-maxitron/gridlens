import { useMemo, useState } from 'react';
import { safe } from '../lib/filters';
import { toAtlasName } from '../lib/countryAliases';
import WorldMap from '../components/charts/WorldMap';
import MapLegend from '../components/charts/MapLegend';
import Segmented from '../components/chart/Segmented';
import ChartCard from '../components/chart/ChartCard';
import { useChart } from '../lib/chartFilters';
import { isOpenSource } from '../lib/tools';
import ToolLogo from '../components/common/ToolLogo';

type Metric = 'records' | 'tools';

/** Tools used in a country, most projects first: the map tooltip (as on EarthPV). */
export function ToolList({ tools }: { tools?: Map<string, number> }) {
  if (!tools?.size) return null;
  const list = [...tools].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  return (
    <ul className="mt-2 space-y-1 border-t border-ink-800 pt-2">
      {list.slice(0, 8).map(([t, n]) => (
        <li key={t} className="flex items-center gap-2 text-ink-200">
          <ToolLogo name={t} size={16} />
          <span className={`min-w-0 flex-1 truncate ${isOpenSource(t) ? 'text-brand-200' : ''}`}>{t}</span>
          <span className="tabular text-ink-500">{n}</span>
        </li>
      ))}
      {list.length > 8 && <li className="text-ink-500">+{list.length - 8} more</li>}
    </ul>
  );
}

/** Where the tools are used. Hover a country for its tools; click it to filter every chart to it. */
export default function Geographic() {
  // The map keeps every country visible so another one can be picked; the country filter only marks it.
  const { records, filters, setFilters } = useChart('map', ['country']);
  const [metric, setMetric] = useState<Metric>('tools');

  const { mapValueByAtlasName, maxValue, rows, multiCountryCount, globalCount, atlasTools, atlasLabel } = useMemo(() => {
    const recordCounts = new Map<string, number>();
    const toolSets = new Map<string, Set<string>>();
    const atlasRecordCounts = new Map<string, number>();
    const atlasToolSets = new Map<string, Set<string>>();
    const atlasTools = new Map<string, Map<string, number>>();
    const atlasLabel = new Map<string, string>();
    let mcCount = 0;
    let gCount = 0;
    for (const r of records) {
      const country = safe(r.country_label);
      if (!country || r.geo_scope !== 'national') continue;
      recordCounts.set(country, (recordCounts.get(country) ?? 0) + 1);
      const tool = safe(r.tool_name);
      if (tool) {
        if (!toolSets.has(country)) toolSets.set(country, new Set());
        toolSets.get(country)!.add(tool);
      }

      const atlasName = toAtlasName(country);
      atlasLabel.set(atlasName, country);
      if (tool) {
        if (!atlasTools.has(atlasName)) atlasTools.set(atlasName, new Map());
        const m = atlasTools.get(atlasName)!;
        m.set(tool, (m.get(tool) ?? 0) + 1);
      }
      atlasRecordCounts.set(atlasName, (atlasRecordCounts.get(atlasName) ?? 0) + 1);
      if (tool) {
        if (!atlasToolSets.has(atlasName)) atlasToolSets.set(atlasName, new Set());
        atlasToolSets.get(atlasName)!.add(tool);
      }
    }
    const source = metric === 'records' ? recordCounts : new Map(Array.from(toolSets, ([k, v]) => [k, v.size]));
    const atlasSource =
      metric === 'records' ? atlasRecordCounts : new Map(Array.from(atlasToolSets, ([k, v]) => [k, v.size]));
    let max = 0;
    for (const v of atlasSource.values()) max = Math.max(max, v);
    const rowList = Array.from(source.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 15);

    for (const r of records) {
      if (r.geo_scope === 'multi_country') mcCount += 1;
      else if (r.geo_scope === 'global') gCount += 1;
    }

    return { valueByCountry: source, mapValueByAtlasName: atlasSource, maxValue: max, rows: rowList, multiCountryCount: mcCount, globalCount: gCount, atlasTools, atlasLabel };
  }, [records, metric]);

  const pick = (country: string) => setFilters({ ...filters, country: filters.country === country ? 'All' : country });

  return (
    <ChartCard
      id="map"
      title="Where the tools are used"
      description="Hover a country for the tools used there; click it to filter every chart to that country. Regional and global studies are counted below the map."
      actions={
        <Segmented
          label="Metric"
          value={metric}
          onChange={(v) => setMetric(v as Metric)}
          options={[{ id: 'tools', label: 'Distinct tools' }, { id: 'records', label: 'Projects' }]}
        />
      }
    >
      <div className="flex flex-col lg:flex-row lg:gap-4">
        <div className="min-w-0 flex-1">
          <WorldMap valueByCountry={mapValueByAtlasName} maxValue={maxValue} unit={metric === 'records' ? 'projects' : 'tools'}
            details={(n) => <ToolList tools={atlasTools.get(n)} />} selected={filters.country === 'All' ? undefined : toAtlasName(filters.country)}
            onSelect={(n) => pick(atlasLabel.get(n) ?? n)} />
        </div>
        <MapLegend maxValue={maxValue} unitLabel={metric === 'records' ? 'Projects' : 'Tools'} />
      </div>
      {multiCountryCount + globalCount > 0 && (
        <p className="mt-3 text-xs text-ink-500">Plus {multiCountryCount} multi-country and {globalCount} global projects.</p>
      )}
      <h3 className="mb-3 mt-6 text-xs uppercase tracking-[0.14em] text-ink-500">Top countries</h3>
      <ol className="grid grid-cols-1 gap-x-8 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map((row, i) => (
          <li key={row.name} className="border-b border-ink-800/70">
            <button type="button" onClick={() => pick(row.name)} title={`Filter every chart to ${row.name}`}
              className={`-mx-2 flex w-[calc(100%+1rem)] items-baseline justify-between gap-3 rounded-md px-2 py-2 text-left text-sm transition-colors hover:bg-ink-800/50 ${filters.country === row.name ? 'text-ink-50' : ''}`}>
              <span className="flex min-w-0 gap-3"><span className="tabular w-5 shrink-0 text-xs text-ink-600">{i + 1}</span><span className="truncate text-ink-200">{row.name}</span></span>
              <span className="tabular text-ink-300">{row.count}</span>
            </button>
          </li>
        ))}
      </ol>
    </ChartCard>
  );
}
