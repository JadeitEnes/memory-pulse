import { Line, LineChart, ResponsiveContainer } from "recharts";
import { usePriceHistory } from "../hooks/useMarketData";
import type { PriceSummary } from "../types/market";

const SEGMENT_LABELS: Record<string, string> = {
  SERVER: "Server",
  CONSUMER: "Consumer",
  MOBILE: "Mobile",
  AI_ACCELERATOR: "AI / HPC",
  ENTERPRISE_SSD: "Ent. SSD",
  CONSUMER_SSD: "Cons. SSD",
};

interface Props {
  summary: PriceSummary;
  selected: boolean;
  onClick: () => void;
}

export function MarketCard({ summary, selected, onClick }: Props) {
  const { points } = usePriceHistory(summary.component, 30);

  const latest = parseFloat(summary.latest_price);
  const change = summary.price_change_pct ? parseFloat(summary.price_change_pct) : 0;
  const isUp = change >= 0;
  const absChange = Math.abs(change).toFixed(2);

  const priceDisplay = latest >= 1 ? `$${latest.toFixed(2)}` : `$${latest.toFixed(4)}`;
  const precision = latest >= 1 ? 2 : 4;

  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-xl p-4 border transition-all duration-200 ${
        selected
          ? "bg-card border-accent shadow-card-active"
          : "bg-card border-border hover:border-accent/30 hover:bg-card-hover shadow-card"
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] text-muted font-semibold tracking-widest uppercase truncate">
            {SEGMENT_LABELS[summary.market_segment] ?? summary.market_segment}
          </p>
          <h3 className="text-white font-bold text-base leading-tight mt-0.5">
            {summary.component}
          </h3>
        </div>
        <span
          className={`text-[11px] font-bold px-2 py-0.5 rounded-full shrink-0 ml-2 ${
            isUp
              ? "text-up bg-up-bg"
              : "text-down bg-down-bg"
          }`}
        >
          {isUp ? "▲" : "▼"} {absChange}%
        </span>
      </div>

      <p className="text-xl font-mono font-bold text-white tracking-tight">{priceDisplay}</p>
      <p className="text-[11px] text-muted mb-2">USD / GB</p>

      <div className="h-10">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points}>
            <Line
              type="monotone"
              dataKey="price"
              stroke={isUp ? "#00c896" : "#f43f5e"}
              strokeWidth={1.5}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-1.5 flex justify-between text-[10px] text-muted">
        <span>Lo ${parseFloat(summary.min_price).toFixed(precision)}</span>
        <span>Hi ${parseFloat(summary.max_price).toFixed(precision)}</span>
        <span className="text-subtle">{summary.data_points}pts</span>
      </div>
    </button>
  );
}
