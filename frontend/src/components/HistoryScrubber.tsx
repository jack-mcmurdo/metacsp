import { useEffect } from "react";
import { useVizStore } from "@/store";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { Play, Pause, Radio } from "lucide-react";

const SPEEDS: Array<1 | 4 | 16> = [1, 4, 16];
const BASE_INTERVAL_MS = 400;

export function HistoryScrubber() {
  const frames = useVizStore((s) => s.frames);
  const mode = useVizStore((s) => s.mode);
  const scrubIndex = useVizStore((s) => s.scrubIndex);
  const playing = useVizStore((s) => s.playing);
  const speed = useVizStore((s) => s.speed);
  const enterScrub = useVizStore((s) => s.enterScrub);
  const goLive = useVizStore((s) => s.goLive);
  const setPlaying = useVizStore((s) => s.setPlaying);
  const setSpeed = useVizStore((s) => s.setSpeed);
  const stepScrub = useVizStore((s) => s.stepScrub);

  useEffect(() => {
    if (!playing || mode !== "scrub") return;
    const id = setInterval(() => stepScrub(1), BASE_INTERVAL_MS / speed);
    return () => clearInterval(id);
  }, [playing, mode, speed, stepScrub]);

  const maxIndex = Math.max(0, frames.length - 1);
  const current = mode === "scrub" ? scrubIndex : maxIndex;
  const currentFrame = frames[current];

  return (
    <div className="flex items-center gap-2 border-t bg-background px-3 py-2">
      <Button
        size="icon"
        variant="outline"
        className="size-7"
        disabled={frames.length === 0}
        onClick={() => {
          if (mode === "live") enterScrub(maxIndex);
          setPlaying(!playing);
        }}
      >
        {playing ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
      </Button>

      <div className="flex items-center gap-0.5">
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => setSpeed(s)}
            className={`rounded px-1.5 py-0.5 text-xs ${
              speed === s ? "bg-accent font-medium" : "text-muted-foreground"
            }`}
          >
            {s}×
          </button>
        ))}
      </div>

      <Slider
        className="mx-2 flex-1"
        min={0}
        max={maxIndex}
        step={1}
        value={[current]}
        onValueChange={([v]: number[]) => enterScrub(v)}
        disabled={frames.length === 0}
      />

      <span className="w-28 shrink-0 text-right text-xs text-muted-foreground">
        {currentFrame ? `seq ${currentFrame.seq}` : "—"}
      </span>

      <Button
        size="sm"
        variant={mode === "live" ? "default" : "outline"}
        className="h-7 gap-1 text-xs"
        onClick={goLive}
      >
        <Radio className="size-3.5" />
        Live
      </Button>
    </div>
  );
}
