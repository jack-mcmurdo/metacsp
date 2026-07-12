import { useVizStore } from "@/store";
import type { DeltaMessage } from "@/lib/protocol";

function label(event: DeltaMessage): string {
  if (event.variable) return `#${event.variable.id} ${event.variable.class}`;
  if (event.constraint) return event.constraint.class;
  return "";
}

export function EventLog() {
  const events = useVizStore((s) => s.events);
  const frames = useVizStore((s) => s.frames);
  const enterScrub = useVizStore((s) => s.enterScrub);

  function jumpTo(seq: number) {
    const index = frames.findIndex((f) => f.seq >= seq);
    if (index >= 0) enterScrub(index);
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto text-xs">
      {events.length === 0 && (
        <div className="p-3 text-muted-foreground">No events yet.</div>
      )}
      {[...events].reverse().map((event) => (
        <button
          key={event.seq}
          onClick={() => jumpTo(event.seq)}
          className="flex items-center gap-2 border-b px-2 py-1 text-left hover:bg-accent"
        >
          <span className="text-muted-foreground">#{event.seq}</span>
          <span className="font-medium">{event.event}</span>
          <span className="truncate text-muted-foreground">{label(event)}</span>
        </button>
      ))}
    </div>
  );
}
