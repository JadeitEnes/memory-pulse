import { useWebSocket } from "../hooks/useWebSocket";

function formatPrice(value: string): string {
  const n = parseFloat(value);
  return n >= 1 ? `$${n.toFixed(2)}` : `$${n.toFixed(4)}`;
}

export function LiveFeed() {
  const { prices, connected } = useWebSocket();

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-card h-full">
      <div className="flex items-center gap-2 mb-5">
        <span
          className={`w-2 h-2 rounded-full ${
            connected ? "bg-up live-dot" : "bg-muted"
          }`}
        />
        <h3 className="text-white font-semibold text-sm tracking-wide uppercase">
          Live Feed
        </h3>
        <span
          className={`text-[11px] ml-auto font-medium ${
            connected ? "text-up" : "text-muted"
          }`}
        >
          {connected ? "● Live" : "Reconnecting…"}
        </span>
      </div>

      {prices.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 gap-2">
          <div className="w-8 h-8 border-2 border-subtle border-t-accent rounded-full animate-spin" />
          <p className="text-muted text-xs">Waiting for broadcast…</p>
        </div>
      ) : (
        <div className="space-y-1">
          {prices.map((p) => {
            const n = parseFloat(p.price_value);
            return (
              <div
                key={p.component}
                className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-subtle/50 transition-colors"
              >
                <div>
                  <p className="text-white text-sm font-semibold leading-tight">
                    {p.component}
                  </p>
                  <p className="text-muted text-[11px]">{p.market_segment}</p>
                </div>
                <p className="font-mono text-accent font-bold text-sm">
                  {formatPrice(p.price_value)}
                </p>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-border">
        <p className="text-muted text-[11px] text-center">
          Updates every 5 seconds via WebSocket
        </p>
      </div>
    </div>
  );
}
