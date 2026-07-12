import type { TimelineValue } from "@/lib/protocol";

export type IntervalState = "gap" | "single" | "overlap" | "inconsistent";

// Mirrors SymbolicTimeline.is_undetermined/is_inconsistent/is_critical
// (meta/symbols_and_time/symbolic_timeline.py).
export function intervalState(value: TimelineValue): IntervalState {
  if (value === null) return "gap";
  if (value.length === 0) return "inconsistent";
  if (value.length === 1) return "single";
  return "overlap";
}

export const STATE_COLOR_VAR: Record<IntervalState, string> = {
  gap: "var(--viz-gap)",
  single: "var(--viz-single)",
  overlap: "var(--viz-overlap)",
  inconsistent: "var(--viz-inconsistent)",
};

export const STATE_LABEL: Record<IntervalState, string> = {
  gap: "Gap",
  single: "Single",
  overlap: "Overlap",
  inconsistent: "Inconsistent",
};
