// TypeScript mirror of the wire protocol v2 messages documented in
// docs/VIZ.md -- that document is the single source of truth; keep this
// file in sync with it.

export interface VariableDict {
  id: number;
  class: string;
  domain: string;
  // Added by VizServer on top of variable_to_dict's own schema -- see docs/VIZ.md.
  component: string | null;
}

export interface ConstraintDict {
  class: string;
  from: number | null;
  to: number | null;
  label: string;
}

export type TimelineValue = string[] | null;

export interface TimelineDict {
  component: string;
  pulses: number[];
  values: TimelineValue[];
}

export interface EnvelopeFeature {
  type: "Feature";
  geometry: {
    type: string;
    coordinates: unknown;
  };
  properties: {
    id: number;
    component: string;
    robot_id: number;
    symbols: string[];
    est: number;
    eet: number;
  };
}

interface MessageBase {
  seq: number;
  ts: number;
}

export interface SnapshotMessage extends MessageBase {
  kind: "snapshot";
  variables: VariableDict[];
  constraints: ConstraintDict[];
  timelines: TimelineDict[];
  envelopes: EnvelopeFeature[];
}

export interface DeltaMessage extends MessageBase {
  kind: "delta";
  event: "variable_added" | "variable_removed" | "constraint_added" | "constraint_removed";
  variable?: VariableDict;
  constraint?: ConstraintDict;
}

export interface TimelinesMessage extends MessageBase {
  kind: "timelines";
  timelines: TimelineDict[];
}

export type ServerMessage = SnapshotMessage | DeltaMessage | TimelinesMessage;

// A frame recorded in the history ring buffer: whatever we knew about the
// full state at the time a snapshot/timelines message arrived.
export interface Frame {
  seq: number;
  ts: number;
  timelines: TimelineDict[];
}
