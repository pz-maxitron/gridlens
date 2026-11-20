import { describe, expect, it } from 'vitest';
import { filtersToSearch, mergeFilterSearch, searchToFilters } from './filterParams';
import { EMPTY_FILTERS } from '../types';

describe('filter query string', () => {
  it('is empty without filters', () => {
    expect(filtersToSearch(EMPTY_FILTERS)).toBe('');
    expect(searchToFilters('')).toEqual(EMPTY_FILTERS);
  });

  it('round-trips active filters, including spaces and special characters', () => {
    const f = { ...EMPTY_FILTERS, country: 'Bosnia and Herzegovina', toolName: 'PSS/E', orgType: 'grid_operator', sector: 'industry', period: '5', search: 'TYNDP & flex' };
    const s = filtersToSearch(f);
    expect(s).toBe('?country=Bosnia+and+Herzegovina&tool=PSS%2FE&org=grid_operator&sector=industry&years=5&q=TYNDP+%26+flex');
    expect(searchToFilters(s)).toEqual(f);
  });

  it('ignores unknown keys', () => {
    expect(searchToFilters('?country=Spain&utm_source=x')).toEqual({ ...EMPTY_FILTERS, country: 'Spain' });
  });
});

describe('shared filters in the URL', () => {
  it('replaces the filter keys and leaves other parameters of the page alone', () => {
    expect(mergeFilterSearch('?type=consultancy&tool=PyPSA&country=Chile', { ...EMPTY_FILTERS, country: 'Spain' })).toBe('?type=consultancy&country=Spain');
    expect(mergeFilterSearch('?country=Chile', EMPTY_FILTERS)).toBe('');
  });
});
