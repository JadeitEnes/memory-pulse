import { useCallback, useEffect, useState } from "react";
import type { ChartPoint, ForecastResponse, MarketOverview, PriceHistory } from "../types/market";

const API = "/api/v1";

export function useMarketOverview() {
  const [data, setData] = useState<MarketOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(`${API}/prices/market/overview`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30_000);
    return () => clearInterval(id);
  }, [refresh]);

  return { data, loading, error, refresh };
}

export function usePriceHistory(component: string, days: number) {
  const [points, setPoints] = useState<ChartPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!component) return;
    setLoading(true);

    const params = new URLSearchParams({
      component,
      days: String(days),
      limit: "1000",
    });

    fetch(`${API}/prices?${params}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<PriceHistory>;
      })
      .then((data) => {
        const mapped: ChartPoint[] = data.items.map((item) => ({
          time: item.recorded_at,
          price: parseFloat(item.price_value),
        }));
        setPoints(mapped);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Unknown error"))
      .finally(() => setLoading(false));
  }, [component, days]);

  return { points, loading, error };
}

export function useForecast(component: string, horizon: number) {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!component) return;
    setLoading(true);
    setData(null);

    fetch(`${API}/forecasts/${encodeURIComponent(component)}?horizon=${horizon}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<ForecastResponse>;
      })
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Unknown error"))
      .finally(() => setLoading(false));
  }, [component, horizon]);

  return { data, loading, error };
}
