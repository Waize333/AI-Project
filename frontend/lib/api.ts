import axios from "axios";
import type { PlanRequest, PlanResponse } from "./types";

const client = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  timeout: 120_000,
});

export async function fetchCities(): Promise<string[]> {
  const res = await client.get<{ cities: string[] }>("/cities");
  return res.data.cities;
}

export async function planTrip(req: PlanRequest): Promise<PlanResponse> {
  const res = await client.post<PlanResponse>("/plan", req);
  return res.data;
}

export async function checkHealth(): Promise<boolean> {
  try {
    await client.get("/health");
    return true;
  } catch {
    return false;
  }
}