import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { scaleLinear } from "d3-scale";
import { useVizStore } from "@/store";
import { intervalState, STATE_COLOR_VAR } from "@/lib/timeline-colors";
import type { TimelineValue } from "@/lib/protocol";

const ROW_HEIGHT = 40;
const AXIS_HEIGHT = 28;
const MIN_LABEL_WIDTH = 26;
const MIN_SPAN = 1;
const TRANSITION = "150ms ease-out";

interface TooltipState {
  x: number;
  y: number;
  component: string;
  start: number;
  end: number;
  state: string;
  symbols: string[] | null;
}

export function TimelineView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);

  const componentOrder = useVizStore((s) => s.componentOrder);
  const hiddenComponents = useVizStore((s) => s.hiddenComponents);
  const viewportStart = useVizStore((s) => s.viewportStart);
  const viewportEnd = useVizStore((s) => s.viewportEnd);
  const follow = useVizStore((s) => s.follow);
  const selected = useVizStore((s) => s.selected);
  const setViewport = useVizStore((s) => s.setViewport);
  const setFollow = useVizStore((s) => s.setFollow);
  const setSelected = useVizStore((s) => s.setSelected);
  const displayedTimelines = useVizStore((s) => s.displayedTimelines);

  const timelines = displayedTimelines();
  const visibleComponents = componentOrder.filter((c) => !hiddenComponents.has(c));
  const timelineByComponent = useMemo(() => {
    const map = new Map<string, (typeof timelines)[number]>();
    for (const tl of timelines) map.set(tl.component, tl);
    return map;
  }, [timelines]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) setWidth(entry.contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const hasDomain = viewportStart !== null && viewportEnd !== null;
  const xScale = useMemo(() => {
    const start = viewportStart ?? 0;
    const end = viewportEnd ?? 100;
    return scaleLinear()
      .domain([start, end])
      .range([0, Math.max(width, 1)]);
  }, [viewportStart, viewportEnd, width]);

  const zoomAt = useCallback(
    (cursorPx: number, factor: number) => {
      if (!hasDomain) return;
      const cursorValue = xScale.invert(cursorPx);
      const start = viewportStart!;
      const end = viewportEnd!;
      let newStart = cursorValue - (cursorValue - start) * factor;
      let newEnd = cursorValue + (end - cursorValue) * factor;
      if (newEnd - newStart < MIN_SPAN) {
        const mid = (newStart + newEnd) / 2;
        newStart = mid - MIN_SPAN / 2;
        newEnd = mid + MIN_SPAN / 2;
      }
      setViewport(newStart, newEnd);
      setFollow(false);
    },
    [hasDomain, xScale, viewportStart, viewportEnd, setViewport, setFollow],
  );

  const onWheel = useCallback(
    (e: React.WheelEvent<SVGSVGElement>) => {
      e.preventDefault();
      const rect = e.currentTarget.getBoundingClientRect();
      const cursorPx = e.clientX - rect.left;
      const factor = e.deltaY > 0 ? 1.1 : 1 / 1.1;
      zoomAt(cursorPx, factor);
    },
    [zoomAt],
  );

  const dragState = useRef<{
    pointers: Map<number, { x: number }>;
    startDistance: number | null;
    captured: boolean;
  } | null>(null);

  const DRAG_THRESHOLD_PX = 4;

  const onPointerDown = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    if (!dragState.current) {
      dragState.current = { pointers: new Map(), startDistance: null, captured: false };
    }
    // Deliberately not calling setPointerCapture here: doing so on every
    // pointerdown (even a plain click with no movement) makes Chromium
    // retarget the compat mouseup/click events at the <svg> instead of the
    // <rect> under the cursor, silently breaking interval clicks. Capture
    // is only engaged once real dragging is detected, in onPointerMove.
    dragState.current.pointers.set(e.pointerId, { x: e.clientX });
  }, []);

  const onPointerMove = useCallback(
    (e: React.PointerEvent<SVGSVGElement>) => {
      const drag = dragState.current;
      if (!drag || !drag.pointers.has(e.pointerId) || !hasDomain) return;
      const prev = drag.pointers.get(e.pointerId)!;
      const dxPx = e.clientX - prev.x;

      if (drag.pointers.size === 1) {
        if (Math.abs(dxPx) < DRAG_THRESHOLD_PX && !drag.captured) return;
        if (!drag.captured) {
          e.currentTarget.setPointerCapture(e.pointerId);
          drag.captured = true;
        }
        drag.pointers.set(e.pointerId, { x: e.clientX });
        const span = viewportEnd! - viewportStart!;
        const dxDomain = -(dxPx / Math.max(width, 1)) * span;
        setViewport(viewportStart! + dxDomain, viewportEnd! + dxDomain);
        setFollow(false);
      } else if (drag.pointers.size === 2) {
        if (!drag.captured) {
          e.currentTarget.setPointerCapture(e.pointerId);
          drag.captured = true;
        }
        drag.pointers.set(e.pointerId, { x: e.clientX });
        const [a, b] = [...drag.pointers.values()];
        const distance = Math.abs(a.x - b.x);
        if (drag.startDistance !== null && distance > 0) {
          const factor = drag.startDistance / distance;
          const mid = (a.x + b.x) / 2;
          const rect = (e.target as SVGSVGElement).getBoundingClientRect?.() ??
            e.currentTarget.getBoundingClientRect();
          zoomAt(mid - rect.left, factor);
        }
        drag.startDistance = distance;
      }
    },
    [hasDomain, viewportStart, viewportEnd, width, setViewport, setFollow, zoomAt],
  );

  const onPointerUp = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
    dragState.current?.pointers.delete(e.pointerId);
    if (dragState.current && dragState.current.pointers.size < 2) {
      dragState.current.startDistance = null;
    }
    if (dragState.current && dragState.current.pointers.size === 0) {
      dragState.current.captured = false;
    }
  }, []);

  if (componentOrder.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Waiting for solver…
      </div>
    );
  }

  const height = AXIS_HEIGHT + visibleComponents.length * ROW_HEIGHT;
  const ticks = hasDomain ? xScale.ticks(Math.max(2, Math.floor(width / 90))) : [];

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden select-none">
      <svg
        width="100%"
        height={height}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onClick={(e) => {
          if (e.target === e.currentTarget) setSelected(null);
        }}
        className="cursor-grab active:cursor-grabbing touch-none"
      >
        {/* axis */}
        <g>
          {ticks.map((t) => (
            <g key={t} transform={`translate(${xScale(t)}, 0)`}>
              <line
                y1={AXIS_HEIGHT}
                y2={height}
                stroke="currentColor"
                strokeOpacity={0.08}
                shapeRendering="crispEdges"
              />
              <text y={16} fontSize={11} fill="currentColor" opacity={0.6} textAnchor="middle">
                {t}
              </text>
            </g>
          ))}
        </g>

        {visibleComponents.map((component, row) => {
          const tl = timelineByComponent.get(component);
          const y = AXIS_HEIGHT + row * ROW_HEIGHT;
          return (
            <g key={component}>
              <text x={4} y={y + 14} fontSize={12} fill="currentColor" fontWeight={500}>
                {component}
              </text>
              {tl &&
                tl.pulses.slice(0, -1).map((p, i) => {
                  const next = tl.pulses[i + 1];
                  const x0 = xScale(p);
                  const x1 = xScale(next);
                  const w = x1 - x0;
                  if (x1 < 0 || x0 > width) return null;
                  const value: TimelineValue = tl.values[i];
                  const state = intervalState(value);
                  const label = value ? value.join("/") : "";
                  const clipId = `clip-${component}-${i}`.replace(/[^a-zA-Z0-9-]/g, "_");
                  const isSelected =
                    selected?.kind === "interval" &&
                    selected.id === `${component}-${p}-${next}`;
                  return (
                    <g key={i}>
                      <rect
                        x={x0}
                        y={y + 15}
                        width={Math.max(w, 0)}
                        height={ROW_HEIGHT - 19}
                        fill={STATE_COLOR_VAR[state]}
                        stroke={isSelected ? "currentColor" : "none"}
                        strokeWidth={isSelected ? 2 : 0}
                        style={{ transition: `x ${TRANSITION}, width ${TRANSITION}` }}
                        onMouseEnter={(e) => {
                          const rect = containerRef.current?.getBoundingClientRect();
                          setTooltip({
                            x: e.clientX - (rect?.left ?? 0),
                            y: e.clientY - (rect?.top ?? 0),
                            component,
                            start: p,
                            end: next,
                            state,
                            symbols: value,
                          });
                        }}
                        onMouseMove={(e) => {
                          const rect = containerRef.current?.getBoundingClientRect();
                          setTooltip((t) =>
                            t
                              ? {
                                  ...t,
                                  x: e.clientX - (rect?.left ?? 0),
                                  y: e.clientY - (rect?.top ?? 0),
                                }
                              : t,
                          );
                        }}
                        onMouseLeave={() => setTooltip(null)}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelected({
                            kind: "interval",
                            id: `${component}-${p}-${next}`,
                            data: { component, start: p, end: next, symbols: value },
                          });
                        }}
                      />
                      {label && w >= MIN_LABEL_WIDTH && (
                        <>
                          <clipPath id={clipId}>
                            <rect x={x0} y={y + 15} width={Math.max(w, 0)} height={ROW_HEIGHT - 19} />
                          </clipPath>
                          <text
                            x={x0 + 4}
                            y={y + 15 + (ROW_HEIGHT - 19) / 2 + 4}
                            fontSize={11}
                            fill="white"
                            clipPath={`url(#${clipId})`}
                            style={{ transition: `x ${TRANSITION}` }}
                          >
                            {label}
                          </text>
                        </>
                      )}
                    </g>
                  );
                })}
            </g>
          );
        })}
      </svg>

      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded-md border bg-popover px-2 py-1 text-xs text-popover-foreground shadow-md"
          style={{ left: tooltip.x + 12, top: tooltip.y + 12 }}
        >
          <div className="font-medium">{tooltip.symbols ? tooltip.symbols.join(", ") : "(gap)"}</div>
          <div className="text-muted-foreground">
            [{tooltip.start}, {tooltip.end}) · {tooltip.state}
          </div>
        </div>
      )}

      {!follow && (
        <div className="absolute right-3 top-1 z-10">
          <button
            onClick={() => setFollow(true)}
            className="rounded-md border bg-background px-2 py-1 text-xs shadow-sm hover:bg-accent"
          >
            Resume follow
          </button>
        </div>
      )}
    </div>
  );
}
