import { useEffect, useMemo, useRef, useState } from "react";
import { useVizStore } from "@/store";

const PALETTE = [
  "oklch(0.7 0.15 250 / 0.5)",
  "oklch(0.7 0.15 150 / 0.5)",
  "oklch(0.75 0.15 80 / 0.5)",
  "oklch(0.7 0.18 25 / 0.5)",
  "oklch(0.7 0.15 320 / 0.5)",
];

type Ring = [number, number][];

function polygonRings(geometry: { type: string; coordinates: unknown }): Ring[] {
  if (geometry.type === "Polygon") {
    const rings = geometry.coordinates as number[][][];
    return rings.length > 0 ? [rings[0] as Ring] : [];
  }
  if (geometry.type === "MultiPolygon") {
    const polys = geometry.coordinates as number[][][][];
    return polys.map((p) => p[0] as Ring);
  }
  return [];
}

function ringToPath(ring: Ring): string {
  return ring.map(([x, y]) => `${x},${-y}`).join(" ");
}

interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export function MapView() {
  const envelopes = useVizStore((s) => s.envelopes);
  const setSelected = useVizStore((s) => s.setSelected);
  const containerRef = useRef<HTMLDivElement>(null);

  const componentOrder = useMemo(
    () => Array.from(new Set(envelopes.map((e) => e.properties.component))),
    [envelopes],
  );

  const initialViewBox = useMemo<ViewBox>(() => {
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const feature of envelopes) {
      for (const ring of polygonRings(feature.geometry)) {
        for (const [x, y] of ring) {
          minX = Math.min(minX, x);
          maxX = Math.max(maxX, x);
          minY = Math.min(minY, -y);
          maxY = Math.max(maxY, -y);
        }
      }
    }
    if (!Number.isFinite(minX)) return { x: -10, y: -10, w: 20, h: 20 };
    const pad = Math.max(maxX - minX, maxY - minY) * 0.1 || 1;
    return { x: minX - pad, y: minY - pad, w: maxX - minX + 2 * pad, h: maxY - minY + 2 * pad };
  }, [envelopes]);

  const [viewBox, setViewBox] = useState<ViewBox>(initialViewBox);
  const framedOnce = useRef(false);
  useEffect(() => {
    if (envelopes.length > 0 && !framedOnce.current) {
      framedOnce.current = true;
      setViewBox(initialViewBox);
    }
  }, [envelopes.length, initialViewBox]);

  const drag = useRef<{ x: number; y: number; captured: boolean } | null>(null);
  const DRAG_THRESHOLD_PX = 4;

  function onWheel(e: React.WheelEvent<SVGSVGElement>) {
    e.preventDefault();
    const rect = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    const factor = e.deltaY > 0 ? 1.1 : 1 / 1.1;
    setViewBox((vb) => {
      const cx = vb.x + px * vb.w;
      const cy = vb.y + py * vb.h;
      const w = vb.w * factor;
      const h = vb.h * factor;
      return { x: cx - px * w, y: cy - py * h, w, h };
    });
  }

  function onPointerDown(e: React.PointerEvent<SVGSVGElement>) {
    // Capture is deliberately not set here -- see TimelineView's
    // onPointerDown for why that would break plain clicks on envelopes.
    drag.current = { x: e.clientX, y: e.clientY, captured: false };
  }

  function onPointerMove(e: React.PointerEvent<SVGSVGElement>) {
    if (!drag.current) return;
    const dxPx = e.clientX - drag.current.x;
    const dyPx = e.clientY - drag.current.y;
    if (!drag.current.captured && Math.hypot(dxPx, dyPx) < DRAG_THRESHOLD_PX) return;
    if (!drag.current.captured) {
      e.currentTarget.setPointerCapture(e.pointerId);
      drag.current.captured = true;
    }
    const rect = e.currentTarget.getBoundingClientRect();
    const dx = (dxPx / rect.width) * viewBox.w;
    const dy = (dyPx / rect.height) * viewBox.h;
    drag.current.x = e.clientX;
    drag.current.y = e.clientY;
    setViewBox((vb) => ({ ...vb, x: vb.x - dx, y: vb.y - dy }));
  }

  function onPointerUp(e: React.PointerEvent<SVGSVGElement>) {
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
    drag.current = null;
  }

  if (envelopes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        No trajectory envelopes.
      </div>
    );
  }

  return (
    <div ref={containerRef} className="h-full w-full">
      <svg
        width="100%"
        height="100%"
        viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        className="cursor-grab touch-none active:cursor-grabbing"
      >
        {envelopes.map((feature) => (
          <g
            key={feature.properties.id}
            onClick={() =>
              setSelected({
                kind: "variable",
                id: String(feature.properties.id),
                data: {
                  id: feature.properties.id,
                  class: "TrajectoryEnvelope",
                  domain: `[${feature.properties.est}, ${feature.properties.eet}]`,
                  component: feature.properties.component,
                },
              })
            }
          >
            {polygonRings(feature.geometry).map((ring, i) => (
              <polygon
                key={i}
                points={ringToPath(ring)}
                fill={PALETTE[componentOrder.indexOf(feature.properties.component) % PALETTE.length]}
                stroke="currentColor"
                strokeWidth={viewBox.w / 400}
              />
            ))}
          </g>
        ))}
      </svg>
    </div>
  );
}
