import type { Filters } from '../types';
import { EMPTY_FILTERS } from '../types';

/** URL query keys for each filter, e.g. ?country=Spain&tool=PyPSA. */
const PARAM: Record<keyof Filters, string> = {
  country: 'country',
  toolName: 'tool',
  toolCategory: 'category',
  orgType: 'org',
  sector: 'sector',
  period: 'years',
  license: 'license',
  evidenceStrength: 'evidence',
  sourceGroup: 'source',
  search: 'q',
};

const KEYS = Object.keys(PARAM) as (keyof Filters)[];

/** Number of filters that differ from the default. */
export function activeCount(filters: Filters): number {
  return KEYS.filter((k) => filters[k].trim() !== EMPTY_FILTERS[k]).length;
}

function write(params: URLSearchParams, filters: Filters, prefix = '') {
  for (const key of KEYS) {
    const value = filters[key].trim();
    if (value && value !== EMPTY_FILTERS[key]) params.set(prefix + PARAM[key], value);
  }
}

function read(params: URLSearchParams, prefix = ''): Filters {
  const filters = { ...EMPTY_FILTERS };
  for (const key of KEYS) {
    const value = params.get(prefix + PARAM[key]);
    if (value) filters[key] = value;
  }
  return filters;
}

/** Query string for one filter set ("" when none are set). */
export function filtersToSearch(filters: Filters): string {
  const params = new URLSearchParams();
  write(params, filters);
  const s = params.toString();
  return s ? `?${s}` : '';
}

/** One filter set from a query string; unknown keys are ignored, missing ones keep their default. */
export function searchToFilters(search: string): Filters {
  return read(new URLSearchParams(search));
}

/** The address bar's query string with the filters written in; other parameters (a page's own ?type=) stay. */
export function mergeFilterSearch(current: string, filters: Filters): string {
  const params = new URLSearchParams(current);
  for (const key of KEYS) params.delete(PARAM[key]);
  write(params, filters);
  const s = params.toString();
  return s ? `?${s}` : '';
}
