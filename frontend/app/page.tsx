"use client";

import { useState } from "react";
import TravelForm from "@/components/TravelForm";
import ItineraryView from "@/components/ItineraryView";
import ComparisonView from "@/components/ComparisonView";
import AlgorithmVisualizer from "@/components/AlgorithmVisualizer";
import { planTrip } from "@/lib/api";
import type { PlanRequest, PlanResponse } from "@/lib/types";

type ResultTab = "csp" | "ga" | "compare";

export default function Home() {
  const [loading,  setLoading]  = useState(false);
  const [response, setResponse] = useState<PlanResponse | null>(null);
  const [error,    setError]    = useState<string | null>(null);
  const [tab,      setTab]      = useState<ResultTab>("csp");

  async function handlePlan(req: PlanRequest) {
    setLoading(true); setError(null); setResponse(null);
    try {
      const r = await planTrip(req);
      setResponse(r);
      if (r.csp_itinerary) setTab("csp");
      else if (r.ga_itinerary) setTab("ga");
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "API error");
    } finally {
      setLoading(false);
    }
  }

  const hasCsp     = !!response?.csp_itinerary;
  const hasGa      = !!response?.ga_itinerary;
  const hasBoth    = hasCsp && hasGa;
  const hasResults = !loading && (hasCsp || hasGa);

  return (
    <div>
      {/* ── 1. Form (hero + controls) ─────────────── */}
      <TravelForm onSubmit={handlePlan} loading={loading} />

      {/* ── 2. Algorithm Pipeline (always visible) ── */}
      <section style={{ padding: "0 0 2px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "20px 24px 0" }}>
          <AlgorithmVisualizer loading={loading} hasResults={hasResults} />
        </div>
      </section>

      {/* ── 3. Status / Error / Results ─────────────── */}
      <section style={{ maxWidth: 1200, margin: "0 auto", padding: "16px 24px 64px" }}>

        {/* Error */}
        {error && (
          <div className="anim-enter" style={{
            padding: "12px 16px", borderRadius: "var(--r)",
            border: "1px solid rgba(248,113,113,0.2)",
            background: "rgba(248,113,113,0.05)",
            fontSize: 13, color: "var(--red)",
          }}>
            <b>Error:</b> {error}
          </div>
        )}

        {/* Infeasibility */}
        {response && !response.feasible && response.infeasibility_report && (
          <div className="anim-enter" style={{
            padding: "14px 16px", borderRadius: "var(--r)",
            border: "1px solid rgba(245,158,11,0.2)",
            background: "rgba(245,158,11,0.04)",
          }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--amber)", marginBottom: 6 }}>
              No feasible itinerary
            </div>
            <div style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.6 }}>
              {response.infeasibility_report.message}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-3)", fontStyle: "italic", marginTop: 4 }}>
              {response.infeasibility_report.suggestion}
            </div>
            {(response.infeasibility_report.suggested_budget || response.infeasibility_report.suggested_days) && (
              <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: 12, color: "var(--amber)" }}>
                {response.infeasibility_report.suggested_budget && (
                  <span>Budget: <b>${response.infeasibility_report.suggested_budget}</b></span>
                )}
                {response.infeasibility_report.suggested_days && (
                  <span>Days: <b>{response.infeasibility_report.suggested_days}</b></span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Results panel */}
        {hasResults && (
          <div className="anim-enter-s" style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--r2)",
            overflow: "hidden",
          }}>
            {/* Tabs */}
            <div style={{ display: "flex", borderBottom: "1px solid var(--border)" }}>
              {hasCsp && (
                <button onClick={() => setTab("csp")} style={{
                  flex: 1, padding: "12px 0", fontSize: 13, fontWeight: 500,
                  cursor: "pointer", border: "none", background: "transparent",
                  color: tab === "csp" ? "var(--accent)" : "var(--text-3)",
                  borderBottom: `2px solid ${tab === "csp" ? "var(--accent)" : "transparent"}`,
                  marginBottom: -1, transition: "all 0.15s",
                }}>CSP + A*</button>
              )}
              {hasGa && (
                <button onClick={() => setTab("ga")} style={{
                  flex: 1, padding: "12px 0", fontSize: 13, fontWeight: 500,
                  cursor: "pointer", border: "none", background: "transparent",
                  color: tab === "ga" ? "var(--green)" : "var(--text-3)",
                  borderBottom: `2px solid ${tab === "ga" ? "var(--green)" : "transparent"}`,
                  marginBottom: -1, transition: "all 0.15s",
                }}>Genetic Algorithm</button>
              )}
              {hasBoth && (
                <button onClick={() => setTab("compare")} style={{
                  flex: 1, padding: "12px 0", fontSize: 13, fontWeight: 500,
                  cursor: "pointer", border: "none", background: "transparent",
                  color: tab === "compare" ? "var(--amber)" : "var(--text-3)",
                  borderBottom: `2px solid ${tab === "compare" ? "var(--amber)" : "transparent"}`,
                  marginBottom: -1, transition: "all 0.15s",
                }}>Compare</button>
              )}
            </div>

            <div style={{ padding: "20px 24px" }}>
              {tab === "csp"     && hasCsp  && <ItineraryView itinerary={response!.csp_itinerary!} accentColor="var(--accent)" />}
              {tab === "ga"      && hasGa   && <ItineraryView itinerary={response!.ga_itinerary!}  accentColor="var(--green)" />}
              {tab === "compare" && hasBoth  && <ComparisonView csp={response!.csp_itinerary!} ga={response!.ga_itinerary!} />}
            </div>
          </div>
        )}

        {/* Idle state */}
        {!loading && !response && !error && (
          <div style={{
            padding: "40px 24px", textAlign: "center",
            border: "1px dashed rgba(255,255,255,0.06)",
            borderRadius: "var(--r2)",
          }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>🗺️</div>
            <div style={{ fontSize: 13, color: "var(--text-2)", fontWeight: 500 }}>
              Configure above and hit Generate
            </div>
            <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 4 }}>
              The pipeline will solve your trip step by step
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
