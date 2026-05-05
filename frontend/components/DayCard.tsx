"use client";

import { useState } from "react";
import type { DayRoute } from "@/lib/types";
import { DAY_COLORS } from "@/lib/types";

interface Props {
  dayRoute: DayRoute;
  accentColor?: string;
}

function fmt(m: number): string {
  const h = Math.floor(m / 60), min = Math.round(m % 60);
  if (h === 0) return `${min}m`;
  return min === 0 ? `${h}h` : `${h}h ${min}m`;
}

const CAT_ICONS: Record<string, string> = {
  landmark: "🏛", museum: "🎨", food: "🍜", nature: "🌿", shopping: "🛍",
  religious: "🕌", nightlife: "🌃", adventure: "🧗", beach: "🏖", cultural: "🎭",
};
const CAT_COLORS: Record<string, string> = {
  landmark: "#F59E0B", museum: "#A78BFA", food: "#F87171", nature: "#34D399",
  shopping: "#F472B6", religious: "#FB923C", nightlife: "#60A5FA",
  adventure: "#10B981", beach: "#38BDF8", cultural: "#C4B5FD",
};

export default function DayCard({ dayRoute, accentColor = "var(--accent)" }: Props) {
  const [open, setOpen] = useState(false);
  const dot = DAY_COLORS[(dayRoute.day - 1) % DAY_COLORS.length];

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "var(--r)", overflow: "hidden", background: "var(--surface-2)" }}>

      {/* Header */}
      <button onClick={() => setOpen(!open)} style={{
        width: "100%", display: "flex", alignItems: "center", gap: 10,
        padding: "10px 12px", cursor: "pointer", border: "none",
        background: open ? "rgba(255,255,255,0.025)" : "transparent",
        textAlign: "left", transition: "background 0.15s",
      }}>
        {/* Colored day tab */}
        <div style={{
          width: 28, height: 28, borderRadius: 5, flexShrink: 0,
          background: dot, display: "flex", alignItems: "center",
          justifyContent: "center", fontSize: 12, fontWeight: 700, color: "white",
        }}>{dayRoute.day}</div>

        <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text)", flex: 1 }}>
          Day {dayRoute.day}
        </span>

        {/* Category emoji strip */}
        <span style={{ fontSize: 13, letterSpacing: -1, marginRight: 6 }}>
          {dayRoute.pois.slice(0, 5).map((p) => CAT_ICONS[p.category] ?? "📍").join("")}
          {dayRoute.pois.length > 5 && (
            <span style={{ fontSize: 10, color: "var(--text-3)", letterSpacing: 0 }}> +{dayRoute.pois.length - 5}</span>
          )}
        </span>

        <div style={{ display: "flex", gap: 10, marginRight: 8 }}>
          <span style={{ fontSize: 11, color: "var(--text-3)" }}>{dayRoute.pois.length} places</span>
          <span style={{ fontSize: 11, color: "var(--amber)", fontWeight: 500 }}>${dayRoute.total_cost_usd.toFixed(0)}</span>
          <span style={{ fontSize: 11, color: "var(--text-3)" }}>{fmt(dayRoute.total_travel_minutes)} travel</span>
        </div>

        <span style={{ fontSize: 10, color: "var(--text-3)" }}>{open ? "▲" : "▼"}</span>
      </button>

      {/* Expanded timeline */}
      {open && (
        <div style={{ borderTop: "1px solid var(--border)" }}>
          {dayRoute.pois.length === 0 ? (
            <p style={{ padding: "12px", fontSize: 12, color: "var(--text-3)", fontStyle: "italic", margin: 0 }}>
              No places assigned.
            </p>
          ) : (
            <div style={{ padding: "10px 10px 6px", position: "relative" }}>
              {/* Vertical timeline connector */}
              <div style={{
                position: "absolute", left: 20, top: 18, bottom: 18, width: 1,
                background: `${dot}30`,
              }} />

              <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                {dayRoute.pois.map((poi, idx) => {
                  const cc = CAT_COLORS[poi.category] ?? "#888";
                  return (
                    <div key={poi.id} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                      {/* Timeline node */}
                      <div style={{
                        width: 22, height: 22, borderRadius: "50%", flexShrink: 0,
                        background: dot, display: "flex", alignItems: "center",
                        justifyContent: "center", fontSize: 10, fontWeight: 700,
                        color: "white", zIndex: 1, position: "relative",
                      }}>{idx + 1}</div>

                      {/* POI card with category color left border */}
                      <div style={{
                        flex: 1, borderRadius: "var(--r)",
                        border: "1px solid var(--border)",
                        borderLeft: `3px solid ${cc}`,
                        background: "var(--surface)",
                        overflow: "hidden",
                      }}>
                        <div style={{ padding: "7px 10px", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 15 }}>{CAT_ICONS[poi.category] ?? "📍"}</span>
                          <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text)", flex: 1, minWidth: 0 }}>
                            {poi.name}
                          </span>
                          <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 3, background: `${cc}12`, color: cc, whiteSpace: "nowrap" }}>
                            {poi.category}
                          </span>
                        </div>
                        <div style={{
                          padding: "4px 10px 7px",
                          display: "flex", gap: 12, flexWrap: "wrap",
                          borderTop: "1px solid var(--border)",
                        }}>
                          <span style={{ fontSize: 10, color: "var(--text-3)" }}>⭐ {poi.rating.toFixed(1)}</span>
                          <span style={{ fontSize: 10, color: "var(--text-3)" }}>⏱ {fmt(poi.avg_duration_minutes)}</span>
                          <span style={{ fontSize: 10, color: "var(--amber)", fontWeight: 500 }}>${poi.avg_cost_usd}</span>
                          {poi.indoor && (
                            <span style={{ fontSize: 10, color: "var(--accent)" }}>indoor</span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Footer summary */}
          <div style={{
            padding: "7px 12px", borderTop: "1px solid var(--border)",
            display: "flex", gap: 16, fontSize: 11, color: "var(--text-3)",
          }}>
            <span>Activity: <span style={{ color: "var(--text-2)" }}>{fmt(dayRoute.total_activity_minutes)}</span></span>
            <span>Transit: <span style={{ color: "var(--text-2)" }}>{fmt(dayRoute.total_travel_minutes)}</span></span>
            <span>Cost: <span style={{ color: "var(--amber)" }}>${dayRoute.total_cost_usd.toFixed(2)}</span></span>
          </div>
        </div>
      )}
    </div>
  );
}
