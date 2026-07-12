import { STATE_COLOR_VAR, STATE_LABEL, type IntervalState } from "@/lib/timeline-colors";

const STATES: IntervalState[] = ["gap", "single", "overlap", "inconsistent"];

export function Legend() {
  return (
    <div className="flex items-center gap-3 px-2 py-1 text-xs text-muted-foreground">
      {STATES.map((state) => (
        <div key={state} className="flex items-center gap-1.5">
          <span
            className="inline-block size-2.5 rounded-sm"
            style={{ background: STATE_COLOR_VAR[state] }}
          />
          {STATE_LABEL[state]}
        </div>
      ))}
    </div>
  );
}
