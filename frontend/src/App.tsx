import { useState } from "react";
import { LiveFeed } from "./components/LiveFeed";
import { MarketCard } from "./components/MarketCard";
import { PriceChart } from "./components/PriceChart";
import { useMarketOverview } from "./hooks/useMarketData";

function Header({ lastUpdate }: { lastUpdate: string }) {
  const time = lastUpdate
    ? new Date(lastUpdate).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10 px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-accent/20 border border-accent/30 flex items-center justify-center">
            <span className="text-accent text-xs font-bold">M</span>
          </div>
          <div>
            <h1 className="text-white font-bold text-base tracking-tight leading-none">
              Memory<span className="text-accent">Pulse</span>
            </h1>
            <p className="text-muted text-[10px] tracking-widest uppercase leading-none mt-0.5">
              Market Intelligence
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-1.5 text-[11px] text-muted bg-subtle/40 px-3 py-1.5 rounded-full border border-border">
            <span className="w-1.5 h-1.5 rounded-full bg-up live-dot" />
            DRAM · NAND · AI Memory
          </div>
          {time && (
            <span className="text-muted text-xs">
              {time}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}

export default function App() {
  const { data, loading, error } = useMarketOverview();
  const [selectedComponent, setSelectedComponent] = useState<string>("HBM3");
  const [chartDays, setChartDays] = useState(30);

  return (
    <div className="min-h-screen bg-surface">
      <Header lastUpdate={data?.generated_at ?? ""} />

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {loading && (
          <div className="flex flex-col items-center justify-center h-64 gap-3">
            <div className="w-10 h-10 border-2 border-subtle border-t-accent rounded-full animate-spin" />
            <p className="text-muted text-sm">Loading market data…</p>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-64 text-down text-sm">
            Failed to connect: {error}
          </div>
        )}

        {data && (
          <>
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-white font-semibold text-sm">Market Overview</h2>
                <span className="text-muted text-xs">{data.total_components} components tracked</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                {data.components.map((summary) => (
                  <MarketCard
                    key={summary.component}
                    summary={summary}
                    selected={selectedComponent === summary.component}
                    onClick={() => setSelectedComponent(summary.component)}
                  />
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div className="lg:col-span-2">
                <PriceChart
                  component={selectedComponent}
                  days={chartDays}
                  onDaysChange={setChartDays}
                />
              </div>
              <div>
                <LiveFeed />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
