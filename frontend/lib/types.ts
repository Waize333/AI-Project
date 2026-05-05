export interface POI {
  id: string;
  name: string;
  city: string;
  lat: number;
  lon: number;
  category: string;
  tags: string[];
  avg_cost_usd: number;
  avg_duration_minutes: number;
  rating: number;
  indoor: boolean;
  family_friendly: boolean;
}

export interface DayRoute {
  day: number;
  pois: POI[];
  total_cost_usd: number;
  total_activity_minutes: number;
  total_travel_minutes: number;
}

export interface Itinerary {
  destination: string;
  days: Record<string, DayRoute>;
  total_cost_usd: number;
  total_travel_minutes: number;
  score: number;
  solver: string;
  runtime_seconds: number | null;
}

export interface InfeasibilityReport {
  constraint_violated: string;
  message: string;
  suggestion: string;
  suggested_budget: number | null;
  suggested_days: number | null;
}

export interface PlanRequest {
  destination: string;
  num_days: number;
  budget_usd: number;
  traveler_type: string;
  interest_weights: Record<string, number>;
  pace: string;
  must_include: string[];
  must_avoid_categories: string[];
  start_date: string;
  hotel_lat?: number;
  hotel_lon?: number;
  solver: string;
}

export interface PlanResponse {
  feasible: boolean;
  infeasibility_report: InfeasibilityReport | null;
  csp_itinerary: Itinerary | null;
  ga_itinerary: Itinerary | null;
}

export const DAY_COLORS = [
  "#3b82f6",
  "#ef4444",
  "#22c55e",
  "#f97316",
  "#a855f7",
  "#06b6d4",
  "#eab308",
  "#ec4899",
  "#14b8a6",
  "#f43f5e",
  "#8b5cf6",
  "#10b981",
  "#f59e0b",
  "#6366f1",
];

export const CATEGORIES = [
  "landmark",
  "museum",
  "food",
  "nature",
  "shopping",
  "religious",
  "nightlife",
  "adventure",
  "beach",
  "cultural",
];