import { useMemo } from "react";
import { useVizStore, type IntervalSelectionData } from "@/store";
import type { ConstraintDict, VariableDict } from "@/lib/protocol";
import { Separator } from "@/components/ui/separator";

function isInterval(data: unknown): data is IntervalSelectionData {
  return !!data && typeof data === "object" && "start" in data && "end" in data;
}

function isVariable(data: unknown): data is VariableDict {
  return !!data && typeof data === "object" && "domain" in data;
}

function isConstraint(data: unknown): data is ConstraintDict {
  return !!data && typeof data === "object" && "label" in data;
}

export function InspectorPanel() {
  const selected = useVizStore((s) => s.selected);
  const variables = useVizStore((s) => s.variables);
  const constraints = useVizStore((s) => s.constraints);

  const related = useMemo(() => {
    if (!selected || !isInterval(selected.data)) return null;
    const component = selected.data.component;
    const vars = variables.filter((v) => v.component === component);
    const varIds = new Set(vars.map((v) => v.id));
    const cons = constraints.filter(
      (c) => (c.from !== null && varIds.has(c.from)) || (c.to !== null && varIds.has(c.to)),
    );
    return { vars, cons };
  }, [selected, variables, constraints]);

  if (!selected) {
    return (
      <div className="p-3 text-sm text-muted-foreground">
        Click an interval, variable, or constraint to inspect it.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 overflow-y-auto p-3 text-sm">
      {isInterval(selected.data) && (
        <div>
          <div className="font-medium">{selected.data.component}</div>
          <div className="text-muted-foreground">
            [{selected.data.start}, {selected.data.end})
          </div>
          <div className="mt-1">{selected.data.symbols?.join(", ") ?? "(gap)"}</div>
        </div>
      )}

      {isVariable(selected.data) && !isInterval(selected.data) && (
        <div>
          <div className="font-medium">Variable #{selected.data.id}</div>
          <div className="text-muted-foreground">{selected.data.class}</div>
          {selected.data.component && (
            <div className="text-muted-foreground">component: {selected.data.component}</div>
          )}
          <div className="mt-1 break-all font-mono text-xs">{selected.data.domain}</div>
        </div>
      )}

      {isConstraint(selected.data) && (
        <div>
          <div className="font-medium">{selected.data.class}</div>
          <div className="text-muted-foreground">
            {selected.data.from} → {selected.data.to}
          </div>
          <div className="mt-1 break-all font-mono text-xs">{selected.data.label}</div>
        </div>
      )}

      {related && (
        <>
          <Separator />
          <div>
            <div className="mb-1 font-medium">Variables ({related.vars.length})</div>
            <div className="flex flex-col gap-1">
              {related.vars.map((v) => (
                <div key={v.id} className="rounded-md border p-1.5 text-xs">
                  <div className="font-medium">
                    #{v.id} {v.class}
                  </div>
                  <div className="break-all font-mono text-muted-foreground">{v.domain}</div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="mb-1 font-medium">Constraints ({related.cons.length})</div>
            <div className="flex flex-col gap-1">
              {related.cons.map((c, i) => (
                <div key={i} className="rounded-md border p-1.5 text-xs">
                  <div className="font-medium">{c.class}</div>
                  <div className="break-all font-mono text-muted-foreground">{c.label}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
