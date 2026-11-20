import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { CatalogueRecord, Filters } from '../types';
import { EMPTY_FILTERS } from '../types';
import { applyFilters, uniqSorted } from './filters';
import { splitCategories, TOOL_CATEGORIES } from './toolCategories';
import { orgGroup, ORG_GROUPS } from './orgTypes';
import { activeCount, mergeFilterSearch, searchToFilters } from './filterParams';
import { useRoute } from './router';

/** Choices offered in every chart's filter panel. */
export interface FilterOptions {
  countries: string[];
  toolNames: string[];
  toolCategories: string[];
  evidenceStrengths: string[];
  orgTypes: string[];
  sourceGroups: string[];
}

interface FilterState {
  catalogue: CatalogueRecord[];
  options: FilterOptions;
  filters: Filters;
  setFilters: (f: Filters) => void;
}

const Ctx = createContext<FilterState | null>(null);

function optionsFor(catalogue: CatalogueRecord[]): FilterOptions {
  const present = new Set(catalogue.flatMap((r) => splitCategories(r.tool_category)));
  const groups = new Set(catalogue.map(orgGroup));
  return {
    countries: [...new Set(catalogue.flatMap((r) => r.countries))].sort((a, b) => a.localeCompare(b)),
    toolNames: uniqSorted(catalogue, 'tool_name'),
    toolCategories: TOOL_CATEGORIES.map((c) => c.id).filter((id) => present.has(id)),
    evidenceStrengths: uniqSorted(catalogue, 'evidence_strength'),
    orgTypes: ORG_GROUPS.map((g) => g.id).filter((id) => groups.has(id)),
    sourceGroups: ['industry', 'academic'].filter((g) => catalogue.some((r) => r.source_group === g)),
  };
}

/**
 * One set of filters shared by every chart: a filter picked in any chart (or a click on a map country)
 * applies to all of them, as on artificialanalysis.ai. The filters are mirrored in the URL (`?country=Spain`)
 * so a copied link restores the view, and they stay set while moving between pages.
 */
export function ChartFiltersProvider({ catalogue, children }: { catalogue: CatalogueRecord[]; children: ReactNode }) {
  const options = useMemo(() => optionsFor(catalogue), [catalogue]);
  const [filters, setFilters] = useState<Filters>(() => searchToFilters(window.location.search));
  const route = useRoute();

  // After a navigation: a link that carries filters sets them; otherwise the current ones are written into the new URL.
  useEffect(() => {
    const fromUrl = searchToFilters(window.location.search);
    if (activeCount(fromUrl) > 0) setFilters((f) => (JSON.stringify(f) === JSON.stringify(fromUrl) ? f : fromUrl));
  }, [route]);

  useEffect(() => {
    const search = mergeFilterSearch(window.location.search, filters);
    if (search !== window.location.search) {
      window.history.replaceState(window.history.state, '', window.location.pathname + search + window.location.hash);
    }
  }, [filters, route]);

  useEffect(() => {
    const onPop = () => setFilters(searchToFilters(window.location.search));
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const value = useMemo(() => ({ catalogue, options, filters, setFilters }), [catalogue, options, filters]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

/**
 * The shared filters and the projects they select. `ignore` lists filters a view sets itself
 * (a tool page is always about its tool), so they are not applied to its records.
 */
export function useChart(id: string, ignore: (keyof Filters)[] = []) {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useChart needs a ChartFiltersProvider');
  const { filters, catalogue } = ctx;
  const key = ignore.join();
  const records = useMemo(() => {
    const f = { ...filters };
    for (const k of ignore) (f[k] as string) = EMPTY_FILTERS[k];
    return applyFilters(catalogue, f);
  }, [catalogue, filters, key]); // eslint-disable-line react-hooks/exhaustive-deps
  const setFilters = useCallback((f: Filters) => ctx.setFilters(f), [ctx]);
  return { id, filters, setFilters, records, catalogue, options: ctx.options };
}
