"use client";

import dynamic from "next/dynamic";
import type { Itinerary } from "@/lib/types";
import DayCard from "./DayCard";

const MapView = dynamic(() => import("./MapView"), { ssr: false });

interface Props {
  itinerary: Itinerary;
  accentColor?: string;
}

const CITY_IMAGES: Record<string, string> = {
  paris:    "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=1200&q=75&auto=format&fit=crop",
  istanbul: "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?w=1200&q=75&auto=format&fit=crop",
  tokyo:    "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1200&q=75&auto=format&fit=crop",
  dubai:    "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1200&q=75&auto=format&fit=crop",
  karachi:  "https://images.unsplash.com/photo-1548013146-72479768bada?w=1200&q=75&auto=format&fit=crop",
};
const CITY_FLAGS: Record<string, string> = {
  paris:"🇫🇷", istanbul:"🇹🇷", tokyo:"🇯🇵", dubai:"🇦🇪", karachi:"🇵🇰",
};

function fmt(m: number): string {
  const h = Math.floor(m / 60), min = Math.round(m % 60);
  if (h === 0) return `${min}m`;
  return min === 0 ? `${h}h` : `${h}h ${min}m`;
}

export default function ItineraryView({ itinerary, accentColor = "var(--accent)" }: Props) {
  const days = Object.values(itinerary.days).sort((a, b) => a.day - b.day);
  const pois = days.reduce((n, d) => n + d.pois.length, 0);
  const dest = itinerary.destination.toLowerCase();
  const img  = CITY_IMAGES[dest];
  const flag = CITY_FLAGS[dest] ?? "🌍";

  const stats = [
    { label:"Score",   value: itinerary.score.toFixed(1),                              unit:"pts"      },
    { label:"Cost",    value: `$${itinerary.total_cost_usd.toFixed(0)}`,               unit:"usd"      },
    { label:"Travel",  value: fmt(itinerary.total_travel_minutes),                     unit:"en route" },
    { label:"Places",  value: String(pois),                                            unit:"visited"  },
    { label:"Runtime", value: itinerary.runtime_seconds != null
        ? `${itinerary.runtime_seconds.toFixed(3)}s` : "—",                            unit:"solve"    },
  ];

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

      {/* ── City photo banner ──────────────────────── */}
      <div style={{ position:"relative", height:120, borderRadius:"var(--r)", overflow:"hidden", background:"#1a1a2e" }}>
        {img && (
          <div style={{
            position:"absolute", inset:0,
            backgroundImage:`url(${img})`,
            backgroundSize:"cover", backgroundPosition:"center 40%",
          }} />
        )}
        <div style={{
          position:"absolute", inset:0,
          background:"linear-gradient(to right, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.3) 70%, transparent 100%)",
        }} />
        <div style={{ position:"absolute", inset:0, padding:"12px 16px", display:"flex", flexDirection:"column", justifyContent:"flex-end" }}>
          <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:4 }}>
            <span style={{ fontSize:10, padding:"2px 8px", borderRadius:3, background:`${accentColor}20`, border:`1px solid ${accentColor}35`, color:accentColor, fontFamily:"monospace" }}>
              {itinerary.solver}
            </span>
            {itinerary.runtime_seconds != null && (
              <span style={{ fontSize:10, color:"rgba(255,255,255,0.35)", fontFamily:"monospace" }}>
                {itinerary.runtime_seconds.toFixed(3)}s
              </span>
            )}
          </div>
          <div style={{ fontSize:18, fontWeight:700, color:"white", textTransform:"capitalize" }}>
            {flag} {itinerary.destination}
          </div>
          <div style={{ fontSize:11, color:"rgba(255,255,255,0.45)", marginTop:2 }}>
            {days.length} day{days.length!==1?"s":""} · {pois} places
          </div>
        </div>
      </div>

      {/* ── Stats row ──────────────────────────────── */}
      <div style={{ display:"flex", border:"1px solid var(--border)", borderRadius:"var(--r)", overflow:"hidden" }}>
        {stats.map((s, i) => (
          <div key={s.label} style={{
            flex:1, padding:"10px 0", textAlign:"center",
            borderRight: i < stats.length-1 ? "1px solid var(--border)" : "none",
          }}>
            <div style={{ fontSize:10, color:"var(--text-3)", marginBottom:2 }}>{s.label}</div>
            <div style={{ fontSize:14, fontWeight:600 }}>{s.value}</div>
            <div style={{ fontSize:9, color:"var(--text-3)", marginTop:1, textTransform:"uppercase", letterSpacing:"0.05em" }}>{s.unit}</div>
          </div>
        ))}
      </div>

      {/* ── Map — always visible, shows every day ──── */}
      <div>
        <div style={{ fontSize:11, fontWeight:600, color:"var(--text-3)", textTransform:"uppercase", letterSpacing:"0.07em", marginBottom:8 }}>
          Route Map · All Days
        </div>
        <div style={{ borderRadius:"var(--r)", overflow:"hidden", height:300, border:"1px solid var(--border)" }}>
          <MapView itinerary={itinerary} />
        </div>
        {/* Day color legend */}
        <div style={{ display:"flex", gap:12, marginTop:8, flexWrap:"wrap" }}>
          {days.map((d, i) => {
            const COLORS = ["#3b82f6","#ef4444","#22c55e","#f97316","#a855f7","#06b6d4","#eab308","#ec4899"];
            const c = COLORS[i % COLORS.length];
            return (
              <span key={d.day} style={{ display:"flex", alignItems:"center", gap:5, fontSize:11, color:"var(--text-3)" }}>
                <span style={{ width:10, height:10, borderRadius:"50%", background:c, flexShrink:0, display:"inline-block" }} />
                Day {d.day} · {d.pois.length} places
              </span>
            );
          })}
        </div>
      </div>

      {/* ── Day cards — always visible ─────────────── */}
      <div>
        <div style={{ fontSize:11, fontWeight:600, color:"var(--text-3)", textTransform:"uppercase", letterSpacing:"0.07em", marginBottom:8 }}>
          Day Plans
        </div>
        <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
          {days.map((d) => <DayCard key={d.day} dayRoute={d} accentColor={accentColor} />)}
        </div>
      </div>
    </div>
  );
}
