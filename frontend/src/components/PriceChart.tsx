import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { usePriceHistory } from "../hooks/useMarketData";
import type { ChartPoint } from "../types/market";

const DAY_OPTIONS = [7, 30, 90] as const;

interface Props {
  component: string;
  days: number;
  onDaysChange: (d: number) => void;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatPrice(value: number): string {
  return value >= 1 ? `$${value.toFixed(2)}` : `$${value.toFixed(4)}`;
}

function samplePoints(points: ChartPoint[], max: number): ChartPoint[] {
  if (points.length <= max) return points;
  const step = Math.ceil(points.length / max);
  return points.filter((_, i) => i % step === 0);
}

export function PriceChart({ component, days, onDaysChange }: Props) {
  const { points, loading, error } = usePriceHistory(component, days);
  const sampled = samplePoints(points, 200);

  const prices = sampled.map((p) => p.price);
  const minPrice = prices.length ? Math.min(...prices) * 0.97 : 0;
  const maxPrice = prices.length ? Math.max(...prices) * 1.03 : 1;

  const latest = prices[prices.length - 1] ?? 0;
  const first = prices[0] ?? 0;
  const isUp = latest >= first;

  const chartColor = isUp ? "#00c896" : "#f43f5e";
  const gradientId = `grad-${component}`;

  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-card">
      <div className="flex items-center justify-between mb-1">
        <div>
          <h2 className="text-white font-bold text-xl tracking-tight">{component}</h2>
          <p className="text-muted text-xs">Price history · USD/GB</p>
        </div>
        <div className="flex gap-1">
          {DAY_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => onDaysChange(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                days === d
                  ? "bg-accent text-white"
                  : "text-muted hover:text-white hover:bg-subtle"
              }`}
            >
              {d}D
            </button>
          ))}
        </div>
      </div>

      {!loading && !error && prices.length > 0 && (
        <div className="flex items-center gap-3 mb-4">
          <span className="font-mono font-bold text-2xl text-white">
            {formatPrice(latest)}
          </span>
          <span
            className={`text-sm font-bold px-2 py-0.5 rounded-full ${
              isUp ? "text-up bg-up-bg" : "text-down bg-down-bg"
            }`}
          >
            {isUp ? "▲" : "▼"}{" "}
            {first > 0 ? Math.abs(((latest - first) / first) * 100).toFixed(2) : "0.00"}%
          </span>
          <span className="text-muted text-xs">{days}d change</span>
        </div>
      )}

      {loading && (
        <div className="h-64 flex items-center justify-center text-muted text-sm">
          Loading…
        </div>
      )}

      {error && (
        <div className="h-64 flex items-center justify-center text-down text-sm">
          {error}
        </div>
      )}

      {!loading && !error && (
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={sampled} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={chartColor} stopOpacity={0.2} />
                <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a2540" vertical={false} />
            <XAxis
              dataKey="time"
              tickFormatter={formatDate}
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[minPrice, maxPrice]}
              tickFormatter={formatPrice}
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={76}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0e1525",
                border: "1px solid #1a2540",
                borderRadius: "10px",
                color: "#e2e8f0",
                fontSize: "13px",
                boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
              }}
              labelFormatter={formatDate}
              formatter={(value: number) => [formatPrice(value), "Price"]}
            />
            <Area
              type="monotone"
              dataKey="price"
              stroke={chartColor}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
              dot={false}
              activeDot={{ r: 4, fill: chartColor, strokeWidth: 0 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
