import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { ComposableMap, Geographies, Geography, ZoomableGroup, Sphere, Graticule } from 'react-simple-maps';
import { mapColorFor, MAP_HOVER } from '../../lib/colors';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

// Natural Earth via world-atlas (ISC licence), served from this site.
const GEO_URL = '/geo/countries-110m.json';

const MIN_ZOOM = 1;
const MAX_ZOOM = 8;
const DEFAULT_CENTER: [number, number] = [10, 20];
const DEFAULT_ZOOM = 1;

interface GeoProperties {
  name: string;
}

interface WorldMapProps {
  valueByCountry: Map<string, number>;
  maxValue: number;
  onHover?: (name: string | null) => void;
  /** Unit in the tooltip ("projects"). */
  unit?: string;
  /** More lines in the tooltip for a country, e.g. the tools used there. */
  details?: (name: string) => ReactNode;
  /** Click on a country (atlas name). */
  onSelect?: (name: string) => void;
  /** Country shown as selected (atlas name). */
  selected?: string;
}

export default function WorldMap({ valueByCountry, maxValue, onHover, unit = 'projects', details, onSelect, selected }: WorldMapProps) {
  const [loadError, setLoadError] = useState(false);
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const [position, setPosition] = useState<{ coordinates: [number, number]; zoom: number }>({
    coordinates: DEFAULT_CENTER,
    zoom: DEFAULT_ZOOM,
  });
  const [tooltip, setTooltip] = useState<{ x: number; y: number; name: string; value: number } | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(GEO_URL)
      .then((r) => {
        if (!r.ok) throw new Error('bad response');
      })
      .catch(() => {
        if (!cancelled) setLoadError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const zoomBy = useCallback((factor: number) => {
    setPosition((pos) => ({ ...pos, zoom: Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, pos.zoom * factor)) }));
  }, []);

  const resetView = useCallback(() => {
    setPosition({ coordinates: DEFAULT_CENTER, zoom: DEFAULT_ZOOM });
  }, []);

  if (loadError) {
    return (
      <div className="flex aspect-[800/420] items-center justify-center text-sm text-ink-500">
        Unable to load world map data (offline?).
      </div>
    );
  }

  return (
    <div ref={wrapperRef} className="relative overflow-hidden rounded-xl border border-ink-800/80 bg-[radial-gradient(ellipse_at_center,#121633_0%,#080a13_70%)]">
      {/* Zoom controls */}
      <div className="absolute right-3 top-3 z-10 flex flex-col overflow-hidden rounded-lg border border-ink-700 bg-ink-900/90 shadow-lg backdrop-blur-sm">
        <button
          type="button"
          aria-label="Zoom in"
          onClick={() => zoomBy(1.5)}
          className="flex h-8 w-8 items-center justify-center text-ink-300 transition-colors hover:bg-ink-800 hover:text-brand-300"
        >
          <ZoomIn size={16} strokeWidth={1.75} />
        </button>
        <div className="h-px w-full bg-ink-700" />
        <button
          type="button"
          aria-label="Zoom out"
          onClick={() => zoomBy(1 / 1.5)}
          className="flex h-8 w-8 items-center justify-center text-ink-300 transition-colors hover:bg-ink-800 hover:text-brand-300"
        >
          <ZoomOut size={16} strokeWidth={1.75} />
        </button>
        <div className="h-px w-full bg-ink-700" />
        <button
          type="button"
          aria-label="Reset view"
          onClick={resetView}
          className="flex h-8 w-8 items-center justify-center text-ink-300 transition-colors hover:bg-ink-800 hover:text-brand-300"
        >
          <Maximize2 size={14} strokeWidth={1.75} />
        </button>
      </div>

      <p className="pointer-events-none absolute left-3 top-3 z-10 rounded-md bg-ink-900/80 px-2 py-1 text-[10px] uppercase tracking-wide text-ink-500 backdrop-blur-sm">
        Pinch or scroll to zoom
      </p>

      <ComposableMap
        width={800}
        height={420}
        projectionConfig={{ scale: 150, center: [0, 8] }}
        style={{ width: '100%', height: 'auto', cursor: 'grab', display: 'block' }}
        onMouseMove={(e) => {
          if (!tooltip || !wrapperRef.current) return;
          const rect = wrapperRef.current.getBoundingClientRect();
          setTooltip((t) => (t ? { ...t, x: e.clientX - rect.left, y: e.clientY - rect.top } : t));
        }}
      >
        <ZoomableGroup
          center={position.coordinates}
          zoom={position.zoom}
          minZoom={MIN_ZOOM}
          maxZoom={MAX_ZOOM}
          onMoveEnd={(pos) =>
            setPosition({
              coordinates: pos.coordinates ?? DEFAULT_CENTER,
              zoom: pos.zoom ?? DEFAULT_ZOOM,
            })
          }
        >
          {/* Sphere + Graticule must be inside the same ZoomableGroup as the
              country geometry. They were previously siblings of
              ZoomableGroup (outside the pan/zoom transform), so the globe
              outline and grid lines stayed visually fixed while the actual
              country shapes panned/zoomed underneath them -- the graticule
              cells and country borders would drift apart and misalign as
              soon as the user interacted with the map. Rendering them here,
              inside the transformed group, keeps the "raster" (graticule +
              sphere) and the vector country data moving together as one
              consistent coordinate space at every zoom/pan state. */}
          <Sphere id="sphere-outline" fill="transparent" stroke="#2f3245" strokeWidth={0.6 / position.zoom} />
          <Graticule stroke="#151829" strokeWidth={0.4 / position.zoom} />
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const name = (geo.properties as GeoProperties).name;
                const value = valueByCountry.get(name) ?? 0;
                const isHovered = hoveredKey === geo.rsmKey;
                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    onMouseEnter={(e) => {
                      setHoveredKey(geo.rsmKey);
                      onHover?.(name);
                      const rect = wrapperRef.current?.getBoundingClientRect();
                      if (rect) {
                        setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top, name, value });
                      }
                    }}
                    onMouseLeave={() => {
                      setHoveredKey(null);
                      onHover?.(null);
                      setTooltip(null);
                    }}
                    onClick={() => value > 0 && onSelect?.(name)}
                    fill={isHovered ? MAP_HOVER : mapColorFor(value, maxValue)}
                    stroke={selected === name ? '#f4efe6' : '#080a13'}
                    strokeWidth={(selected === name ? 1.6 : 0.5) / position.zoom}
                    style={{ outline: 'none', cursor: 'pointer' }}
                  />
                );
              })
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>

      {tooltip && (
        <div
          className={`pointer-events-none absolute z-20 w-max max-w-64 -translate-x-1/2 rounded-xl ${tooltip.y < 200 ? 'translate-y-4' : '-translate-y-[calc(100%+12px)]'} border border-ink-700 bg-ink-950/95 px-3 py-2 text-xs shadow-2xl backdrop-blur`}
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <p className="font-semibold text-ink-50">{tooltip.name}</p>
          <p className="text-brand-300">{tooltip.value.toLocaleString()} {unit}</p>
          {tooltip.value > 0 && details?.(tooltip.name)}
          {tooltip.value > 0 && onSelect && <p className="mt-1.5 text-[10px] text-ink-500">{selected === tooltip.name ? 'Click to clear the country filter' : 'Click to filter every chart'}</p>}
        </div>
      )}
    </div>
  );
}
