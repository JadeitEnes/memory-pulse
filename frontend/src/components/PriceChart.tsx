import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useForecast, usePriceHistory } from "../hooks/useMarketData";
import type { ChartPoint } from "../types/market";

const DAY_OPTIONS = [7, 30, 90] as const;
const HORIZON_OPTIONS = [30, 60, 90] as const;

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

interface CombinedPoint {
  time: string;
  price?: number;
  predicted?: number;
  lower?: number;
  upper?: number;
}

export function PriceChart({ component, days, onDaysChange }: Props) {
  const [horizon, setHorizon] = useState(30);
  const { points, loading, error } = usePriceHistory(component, days);
  const { data: forecast, loading: fLoading } = useForecast(component, horizon);

  const sampled = samplePoints(points, 200);

  const historical: CombinedPoint[] = sampled.map((p) => ({
    time: p.time,
    price: p.price,
  }));

  const forecastPoints: CombinedPoint[] =
    forecast?.forecast.map((fp) => ({
      time: fp.date,
      predicted: parseFloat(fp.predicted),
      lower: parseFloat(fp.lower),
      upper: parseFloat(fp.upper),
    })) ?? [];

  // Stitch last historical point into forecast so lines connect
  if (historical.length > 0 && forecastPoints.length > 0) {
    const last = historical[historical.length - 1];
    forecastPoints.unshift({
      time: last.time,
      price: last.price,
      predicted: last.price,
      lower: last.price,
      upper: last.price,
    });
  }

  const combined: CombinedPoint[] = [...historical, ...forecastPoints];

  const allPrices = [
    ...sampled.map((p) => p.price),
    ...(forecast?.forecast.flatMap((fp) => [parseFloat(fp.lower), parseFloat(fp.upper)]) ?? []),
  ].filter((v): v is number => v !== undefined);

  const minPrice = allPrices.length ? Math.min(...allPrices) * 0.96 : 0;
  const maxPrice = allPrices.length ? Math.max(...allPrices) * 1.04 : 1;

  const prices = sampled.map((p) => p.price);
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
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <span className="font-mono font-bold text-2xl text-white">{formatPrice(latest)}</span>
          <span
            className={`text-sm font-bold px-2 py-0.5 rounded-full ${
              isUp ? "text-up bg-up-bg" : "text-down bg-down-bg"
            }`}
          >
            {isUp ? "▲" : "▼"}{" "}
            {first > 0 ? Math.abs(((latest - first) / first) * 100).toFixed(2) : "0.00"}%
          </span>
          <span className="text-muted text-xs">{days}d change</span>

          <div className="ml-auto flex items-center gap-2">
            <span className="text-muted text-[11px] uppercase tracking-wide">Forecast</span>
            {HORIZON_OPTIONS.map((h) => (
              <button
                key={h}
                onClick={() => setHorizon(h)}
                className={`px-2 py-1 rounded text-xs font-semibold transition-colors ${
                  horizon === h
                    ? "bg-gold/20 text-gold border border-gold/30"
                    : "text-muted hover:text-white hover:bg-subtle"
                }`}
              >
                {h}D
              </button>
            ))}
            {fLoading && (
              <span className="text-muted text-[10px] animate-pulse">fitting…</span>
            )}
          </div>
        </div>
      )}

      {loading && (
        <div className="h-64 flex items-center justify-center text-muted text-sm">
          Loading…
        </div>
      )}
      {error && (
        <div className="h-64 flex items-center justify-center text-down text-sm">{error}</div>
      )}

      {!loading && !error && (
        <>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={combined} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColor} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                </linearGradient>
                <linearGradient id={`${gradientId}-band`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.18} />
                  <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.03} />
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
                formatter={(value: number, name: string) => {
                  const labels: Record<string, string> = {
                    price: "Price",
                    predicted: "Forecast",
                    upper: "Upper 80%",
                    lower: "Lower 80%",
                  };
                  return [formatPrice(value), labels[name] ?? name];
                }}
              />

              {/* Historical price area */}
              <Area
                type="monotone"
                dataKey="price"
                stroke={chartColor}
                strokeWidth={2}
                fill={`url(#${gradientId})`}
                dot={false}
                activeDot={{ r: 4, fill: chartColor, strokeWidth: 0 }}
                connectNulls={false}
              />

              {/* 80% confidence band upper — filled */}
              <Area
                type="monotone"
                dataKey="upper"
                stroke="none"
                fill={`url(#${gradientId}-band)`}
                dot={false}
                activeDot={false}
                connectNulls={false}
              />

              {/* 80% confidence band lower — erase overlap with card bg */}
              <Area
                type="monotone"
                dataKey="lower"
                stroke="none"
                fill="#0e1525"
                dot={false}
                activeDot={false}
                connectNulls={false}
              />

              {/* Forecast center line (dashed gold) */}
              <Area
                type="monotone"
                dataKey="predicted"
                stroke="#f59e0b"
                strokeWidth={2}
                strokeDasharray="5 3"
                fill="none"
                dot={false}
                activeDot={{ r: 4, fill: "#f59e0b", strokeWidth: 0 }}
                connectNulls={false}
              />
            </AreaChart>
          </ResponsiveContainer>

          <div className="flex items-center gap-5 mt-2 px-1">
            <div className="flex items-center gap-1.5">
              <div className="w-4 h-0.5 rounded" style={{ backgroundColor: chartColor }} />
              <span className="text-muted text-[11px]">Historical</span>
            </div>
            <div className="flex items-center gap-1.5">
              <svg width="16" height="6">
                <line
                  x1="0"
                  y1="3"
                  x2="16"
                  y2="3"
                  stroke="#f59e0b"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                />
              </svg>
              <span className="text-muted text-[11px]">Forecast ({horizon}d · Prophet)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-4 h-3 rounded-sm" style={{ backgroundColor: "#f59e0b22" }} />
              <span className="text-muted text-[11px]">80% confidence</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
