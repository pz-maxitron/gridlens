import { useEffect } from 'react';
import catalogueData from './data/catalogue.json';
import type { CatalogueRecord } from './types';
import { PAGES, slug, useRoute } from './lib/router';
import { ChartFiltersProvider } from './lib/chartFilters';
import { TOOLS } from './lib/tools';
import Shell from './components/layout/Shell';
import Overview from './pages/Overview';
import Tool from './pages/Tool';
import Organizations from './pages/Organizations';
import Projects from './pages/Projects';
import Methodology from './pages/Methodology';
import Changelog from './pages/Changelog';
import Contact from './pages/Contact';
import Legal from './pages/Legal';

const catalogue = catalogueData as CatalogueRecord[];

export default function App() {
  const route = useRoute();

  useEffect(() => {
    const tool = TOOLS.find((t) => slug(t.name) === route.tool)?.name;
    document.title = tool ? `${tool} · GridLens` : PAGES.find((p) => p.path === route.page)?.title ?? PAGES[0].title;
  }, [route]);

  useEffect(() => {
    const id = window.location.hash.slice(1);
    if (id) requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ block: 'start' }));
  }, []);

  return (
    <ChartFiltersProvider catalogue={catalogue}>
      <Shell route={route}>
        <div key={route.page + (route.tool ?? '')}>
          {route.page === '/' && <Overview catalogue={catalogue} />}
          {route.page === '/tools' && <Tool tool={route.tool} />}
          {route.page === '/organizations' && <Organizations catalogue={catalogue} />}
          {route.page === '/projects' && <Projects />}
          {route.page === '/about' && <Methodology catalogue={catalogue} />}
          {route.page === '/about/changelog' && <Changelog />}
          {route.page === '/about/contact' && <Contact />}
          {route.page === '/about/legal' && <Legal />}
        </div>
      </Shell>
    </ChartFiltersProvider>
  );
}
