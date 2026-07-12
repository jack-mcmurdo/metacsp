import { useState } from "react";
import { Header } from "@/components/Header";
import { ComponentSidebar } from "@/components/ComponentSidebar";
import { InspectorPanel } from "@/components/InspectorPanel";
import { EventLog } from "@/components/EventLog";
import { Legend } from "@/components/Legend";
import { HistoryScrubber } from "@/components/HistoryScrubber";
import { TimelineView } from "@/components/TimelineView";
import { NetworkView } from "@/components/NetworkView";
import { MapView } from "@/components/MapView";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useDarkMode } from "@/lib/dark-mode";
import { useLiveConnection } from "@/lib/ws";
import { useVizStore } from "@/store";

function App() {
  useLiveConnection();
  const [dark, toggleDark] = useDarkMode();
  const [panelOpen, setPanelOpen] = useState(true);
  const [tab, setTab] = useState("timeline");
  const connectionStatus = useVizStore((s) => s.connectionStatus);
  const hasEnvelopes = useVizStore((s) => s.envelopes.length > 0);

  return (
    <TooltipProvider>
      <div className="flex h-screen flex-col bg-background text-foreground">
        <Header
          dark={dark}
          onToggleDark={toggleDark}
          panelOpen={panelOpen}
          onTogglePanel={() => setPanelOpen((v) => !v)}
        />
        <div className="flex flex-1 overflow-hidden">
          <aside className="w-48 shrink-0 overflow-y-auto border-r">
            <ComponentSidebar />
          </aside>

          <main className="flex flex-1 flex-col overflow-hidden">
            <Tabs value={tab} onValueChange={setTab} className="flex flex-1 flex-col overflow-hidden gap-0">
              <TabsList className="mx-2 mt-2 w-fit">
                <TabsTrigger value="timeline">Timeline</TabsTrigger>
                <TabsTrigger value="network">Network</TabsTrigger>
                {hasEnvelopes && <TabsTrigger value="map">Map</TabsTrigger>}
              </TabsList>
              <div className="relative flex-1 overflow-hidden">
                <TabsContent value="timeline" className="h-full overflow-auto">
                  <TimelineView />
                </TabsContent>
                <TabsContent value="network" className="h-full">
                  <NetworkView />
                </TabsContent>
                <TabsContent value="map" className="h-full">
                  <MapView />
                </TabsContent>

                {connectionStatus === "closed" && (
                  <div className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center bg-background/60 backdrop-blur-sm">
                    <div className="rounded-md border bg-popover px-4 py-2 text-sm shadow-md">
                      Connection lost — reconnecting…
                    </div>
                  </div>
                )}
              </div>
            </Tabs>
            {tab === "timeline" && <Legend />}
            <HistoryScrubber />
          </main>

          {panelOpen && (
            <aside className="flex w-80 shrink-0 flex-col overflow-hidden border-l">
              <Tabs defaultValue="inspector" className="flex flex-1 flex-col overflow-hidden gap-0">
                <TabsList className="m-2 w-fit">
                  <TabsTrigger value="inspector">Inspector</TabsTrigger>
                  <TabsTrigger value="events">Events</TabsTrigger>
                </TabsList>
                <TabsContent value="inspector" className="flex-1 overflow-hidden">
                  <InspectorPanel />
                </TabsContent>
                <TabsContent value="events" className="flex-1 overflow-hidden">
                  <EventLog />
                </TabsContent>
              </Tabs>
            </aside>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
}

export default App;
