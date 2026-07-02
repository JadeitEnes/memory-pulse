export interface PriceSummary {
  component: string;
  market_segment: string;
  period_days: number;
  avg_price: string;
  min_price: string;
  max_price: string;
  latest_price: string;
  price_unit: string;
  currency: string;
  price_change_pct: string | null;
  data_points: number;
  last_updated: string;
}

export interface MarketOverview {
  components: PriceSummary[];
  total_components: number;
  generated_at: string;
}

export interface PriceRecord {
  id: number;
  component: string;
  market_segment: string;
  price_value: string;
  price_unit: string;
  currency: string;
  data_source: string;
  recorded_at: string;
  is_validated: boolean;
}

export interface PriceHistory {
  items: PriceRecord[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface ChartPoint {
  time: string;
  price: number;
}

export type WsMessage =
  | { type: "price_update"; data: PriceRecord[] }
  | { type: "connected" };
