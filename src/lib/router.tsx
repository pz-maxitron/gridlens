import { useEffect, useState, type AnchorHTMLAttributes, type MouseEvent } from 'react';

/** Pages of the site. The overview is the one-pager; the rest hold detail and reference material. */
export const PAGES = [
  { path: '/', label: 'Overview', title: 'GridLens — who uses which energy models, where, for which grid decisions' },
  { path: '/organizations', label: 'Organizations', title: 'Organizations · GridLens' },
  { path: '/projects', label: 'Projects & data', title: 'Projects & data · GridLens' },
  { path: '/about', label: 'Methodology', title: 'About & methodology · GridLens' },
  { path: '/about/changelog', label: 'Changelog', title: 'Changelog · GridLens' },
  { path: '/about/contact', label: 'Contact', title: 'Contact · GridLens' },
  { path: '/about/legal', label: 'Legal & privacy', title: 'Legal & privacy · GridLens' },
] as const;

export type PagePath = (typeof PAGES)[number]['path'] | '/tools';

/** Sections of the overview, in page order: the left-hand index and the chart ids. */
export const SECTIONS = [
  { id: 'adoption', label: 'Adoption' },
  { id: 'purpose', label: 'Tools by purpose' },
  { id: 'momentum', label: 'Momentum' },
  { id: 'map', label: 'Where' },
  { id: 'decisions', label: 'Grid decisions' },
  { id: 'builders', label: 'Who builds open source' },
] as const;

/** URL-safe tool name: "PSS/E" → "pss-e", "DIgSILENT PowerFactory" → "digsilent-powerfactory". */
export function slug(name: string): string {
  return name.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

export interface Route {
  page: PagePath;
  /** Tool profile: /tools/<slug>. */
  tool?: string;
}

/** Route for a path; unknown paths show the overview. */
export function parsePath(pathname: string): Route {
  const p = pathname.replace(/\/+$/, '') || '/';
  const tool = p.match(/^\/tools\/([^/]+)$/);
  if (tool) return { page: '/tools', tool: decodeURIComponent(tool[1]) };
  return PAGES.some((pg) => pg.path === p) ? { page: p as PagePath } : { page: '/' };
}

const listeners = new Set<() => void>();

/** Go to an internal path (with optional query/hash) without reloading. */
export function navigate(href: string) {
  window.history.pushState(null, '', href);
  listeners.forEach((l) => l());
  const hash = new URL(href, window.location.origin).hash.slice(1);
  if (hash) requestAnimationFrame(() => document.getElementById(hash)?.scrollIntoView({ block: 'start' }));
  else window.scrollTo(0, 0);
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parsePath(window.location.pathname));
  useEffect(() => {
    const update = () => setRoute(parsePath(window.location.pathname));
    listeners.add(update);
    window.addEventListener('popstate', update);
    return () => {
      listeners.delete(update);
      window.removeEventListener('popstate', update);
    };
  }, []);
  return route;
}

/** In-app link: a normal <a href> (so it can be opened in a new tab), navigated without a reload. */
export function Link({ href, onClick, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  function handle(e: MouseEvent<HTMLAnchorElement>) {
    onClick?.(e);
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    navigate(href);
  }
  return <a href={href} onClick={handle} {...rest} />;
}
