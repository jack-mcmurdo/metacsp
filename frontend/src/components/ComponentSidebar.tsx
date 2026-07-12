import { useState } from "react";
import { useVizStore } from "@/store";
import { Checkbox } from "@/components/ui/checkbox";

export function ComponentSidebar() {
  const componentOrder = useVizStore((s) => s.componentOrder);
  const hiddenComponents = useVizStore((s) => s.hiddenComponents);
  const toggleComponentHidden = useVizStore((s) => s.toggleComponentHidden);
  const setComponentOrder = useVizStore((s) => s.setComponentOrder);

  const [dragging, setDragging] = useState<string | null>(null);

  function onDrop(target: string) {
    if (!dragging || dragging === target) return;
    const order = [...componentOrder];
    const from = order.indexOf(dragging);
    const to = order.indexOf(target);
    order.splice(from, 1);
    order.splice(to, 0, dragging);
    setComponentOrder(order);
    setDragging(null);
  }

  return (
    <div className="flex flex-col gap-1 p-2">
      <div className="px-1 pb-1 text-xs font-medium text-muted-foreground">Components</div>
      {componentOrder.map((component) => (
        <div
          key={component}
          draggable
          onDragStart={() => setDragging(component)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={() => onDrop(component)}
          className="flex cursor-grab items-center gap-2 rounded-md px-1 py-1 text-sm hover:bg-accent"
        >
          <Checkbox
            checked={!hiddenComponents.has(component)}
            onCheckedChange={() => toggleComponentHidden(component)}
          />
          <span className="truncate">{component}</span>
        </div>
      ))}
    </div>
  );
}
