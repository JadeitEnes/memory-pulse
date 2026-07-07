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

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type AnomalyStatus = "NORMAL" | "WARNING" | "ANOMALY" | "EXTREME";

export interface ComponentRiskReport {
  component: string;
  generated_at: string;
  period_days: number;
  latest_price: string;
  mean_price: string;
  std_price: string;
  z_score: number;
  anomaly_status: AnomalyStatus;
  trend_direction: string;
  price_change_pct: number;
  volatility_pct: number;
  risk_score: number;
  risk_level: RiskLevel;
  risk_factors: {
    anomaly_contribution: number;
    volatility_contribution: number;
    trend_contribution: number;
  };
}

export interface AnomalyOverview {
  generated_at: string;
  period_days: number;
  reports: ComponentRiskReport[];
}

export interface ForecastPoint {
  date: string;
  predicted: string;
  lower: string;
  upper: string;
}

export interface ForecastResponse {
  component: string;
  generated_at: string;
  horizon_days: number;
  historical_days: number;
  model: string;
  forecast: ForecastPoint[];
}
