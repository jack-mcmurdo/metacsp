import { create } from "zustand";
import type {
  ConstraintDict,
  DeltaMessage,
  EnvelopeFeature,
  Frame,
  ServerMessage,
  TimelineDict,
  VariableDict,
} from "@/lib/protocol";

const MAX_FRAMES = 2000;

export type ConnectionStatus = "connecting" | "open" | "closed";

export interface IntervalSelectionData {
  component: string;
  start: number;
  end: number;
  symbols: string[] | null;
}

export interface Selection {
  kind: "variable" | "constraint" | "interval";
  id: string;
  data?: VariableDict | ConstraintDict | IntervalSelectionData;
}

interface VizState {
  connectionStatus: ConnectionStatus;

  variables: VariableDict[];
  constraints: ConstraintDict[];
  timelines: TimelineDict[];
  envelopes: EnvelopeFeature[];
  events: DeltaMessage[];
  frames: Frame[];

  componentOrder: string[];
  hiddenComponents: Set<string>;

  viewportStart: number | null;
  viewportEnd: number | null;
  follow: boolean;

  selected: Selection | null;

  mode: "live" | "scrub";
  scrubIndex: number;
  playing: boolean;
  speed: 1 | 4 | 16;

  setConnectionStatus: (status: ConnectionStatus) => void;
  applyMessage: (msg: ServerMessage) => void;
  setViewport: (start: number, end: number) => void;
  setFollow: (follow: boolean) => void;
  toggleComponentHidden: (name: string) => void;
  setComponentOrder: (order: string[]) => void;
  setSelected: (sel: Selection | null) => void;
  enterScrub: (index: number) => void;
  goLive: () => void;
  setPlaying: (playing: boolean) => void;
  setSpeed: (speed: 1 | 4 | 16) => void;
  stepScrub: (delta: number) => void;

  displayedTimelines: () => TimelineDict[];
}

function maxPulse(timelines: TimelineDict[]): number | null {
  let max: number | null = null;
  for (const tl of timelines) {
    for (const p of tl.pulses) {
      if (max === null || p > max) max = p;
    }
  }
  return max;
}

export const useVizStore = create<VizState>((set, get) => ({
  connectionStatus: "connecting",

  variables: [],
  constraints: [],
  timelines: [],
  envelopes: [],
  events: [],
  frames: [],

  componentOrder: [],
  hiddenComponents: new Set(),

  viewportStart: null,
  viewportEnd: null,
  follow: true,

  selected: null,

  mode: "live",
  scrubIndex: 0,
  playing: false,
  speed: 1,

  setConnectionStatus: (status) => set({ connectionStatus: status }),

  applyMessage: (msg) =>
    set((state) => {
      const next: Partial<VizState> = {};

      if (msg.kind === "snapshot") {
        next.variables = msg.variables;
        next.constraints = msg.constraints;
        next.timelines = msg.timelines;
        next.envelopes = msg.envelopes;
      } else if (msg.kind === "delta") {
        next.events = [...state.events, msg].slice(-500);
        if (msg.variable) {
          if (msg.event === "variable_added") {
            next.variables = [...state.variables, msg.variable];
          } else {
            next.variables = state.variables.filter((v) => v.id !== msg.variable!.id);
          }
        }
        if (msg.constraint) {
          // Constraints have no stable id in the wire format; delta events
          // for constraints only feed the event log, not the variables/
          // constraints arrays (the next snapshot reconciles those).
        }
      } else if (msg.kind === "timelines") {
        next.timelines = msg.timelines;
      }

      const timelines = next.timelines ?? state.timelines;
      const newComponents = timelines
        .map((t) => t.component)
        .filter((c) => !state.componentOrder.includes(c));
      if (newComponents.length > 0) {
        next.componentOrder = [...state.componentOrder, ...newComponents];
      }

      if (msg.kind === "snapshot" || msg.kind === "timelines") {
        const frame: Frame = { seq: msg.seq, ts: msg.ts, timelines: msg.timelines };
        const frames = [...state.frames, frame];
        if (frames.length > MAX_FRAMES) frames.splice(0, frames.length - MAX_FRAMES);
        next.frames = frames;
        if (state.mode === "live" && state.follow) {
          const max = maxPulse(msg.timelines);
          if (max !== null) {
            const span =
              state.viewportStart !== null && state.viewportEnd !== null
                ? state.viewportEnd - state.viewportStart
                : Math.max(max, 100);
            next.viewportStart = max - span;
            next.viewportEnd = max;
          }
        }
        if (state.mode === "live") {
          next.scrubIndex = frames.length - 1;
        }
      }

      return next;
    }),

  setViewport: (start, end) => set({ viewportStart: start, viewportEnd: end }),

  setFollow: (follow) => set({ follow }),

  toggleComponentHidden: (name) =>
    set((state) => {
      const hidden = new Set(state.hiddenComponents);
      if (hidden.has(name)) hidden.delete(name);
      else hidden.add(name);
      return { hiddenComponents: hidden };
    }),

  setComponentOrder: (order) => set({ componentOrder: order }),

  setSelected: (sel) => set({ selected: sel }),

  enterScrub: (index) =>
    set((state) => ({
      mode: "scrub",
      follow: false,
      scrubIndex: Math.max(0, Math.min(index, state.frames.length - 1)),
    })),

  goLive: () =>
    set((state) => ({
      mode: "live",
      follow: true,
      playing: false,
      scrubIndex: Math.max(0, state.frames.length - 1),
    })),

  setPlaying: (playing) => set({ playing }),

  setSpeed: (speed) => set({ speed }),

  stepScrub: (delta) =>
    set((state) => {
      const nextIndex = state.scrubIndex + delta;
      if (nextIndex >= state.frames.length - 1) {
        return { mode: "live", follow: state.follow, scrubIndex: state.frames.length - 1 };
      }
      return { scrubIndex: Math.max(0, nextIndex) };
    }),

  displayedTimelines: () => {
    const state = get();
    if (state.mode === "scrub" && state.frames.length > 0) {
      const frame = state.frames[Math.min(state.scrubIndex, state.frames.length - 1)];
      return frame.timelines;
    }
    return state.timelines;
  },
}));
