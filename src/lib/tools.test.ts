import { describe, expect, it } from 'vitest';
import { catalogueUpdated, searchFreshness, TOOLS, type ToolInfo } from './tools';

const tool = (name: string, last_searched?: string): ToolInfo => ({ name, vendor: '', license: 'open_source', url: '', categories: [], last_searched });

describe('search dates', () => {
  it('are real, past days in tools.json', () => {
    for (const t of TOOLS.filter((t) => t.last_searched)) {
      expect(t.last_searched).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(new Date(t.last_searched!).toISOString().slice(0, 10)).toBe(t.last_searched);
      expect(t.last_searched! <= new Date().toISOString().slice(0, 10)).toBe(true);
    }
  });

  it('give the catalogue the latest one and list the stalest tools first', () => {
    const tools = [tool('B', '2026-11-18'), tool('A'), tool('C', '2026-11-08')];
    expect(catalogueUpdated(tools)).toBe('2026-11-18');
    expect(searchFreshness(tools).map((t) => t.name)).toEqual(['A', 'C', 'B']);
    expect(catalogueUpdated([tool('A')])).toBeUndefined();
  });
});
