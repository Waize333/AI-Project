"use client";

import { useState, useEffect, useMemo } from "react";
import { fetchCities } from "@/lib/api";
import type { PlanRequest } from "@/lib/types";
import { CATEGORIES } from "@/lib/types";
import Slider from "@/components/Slider";
import { useIsMobile } from "@/lib/useIsMobile";

interface Props {
  onSubmit: (req: PlanRequest) => void;
  loading: boolean;
}

/* ─── City data ──────────────────────────────────────── */
const CITY_META: Record<string, {
  flag: string; country: string; tagline: string;
  img: string; fallback: string;
}> = {
  paris:    { flag:"🇫🇷", country:"France",   tagline:"City of Light",        img:"https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=1600&q=80&auto=format&fit=crop", fallback:"#1a0533" },
  istanbul: { flag:"🇹🇷", country:"Turkey",   tagline:"Where East Meets West", img:"https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?w=1600&q=80&auto=format&fit=crop", fallback:"#0f2027" },
  tokyo:    { flag:"🇯🇵", country:"Japan",    tagline:"Neon & Tradition",      img:"https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1600&q=80&auto=format&fit=crop", fallback:"#16002e" },
  dubai:    { flag:"🇦🇪", country:"UAE",      tagline:"Desert Skyline",        img:"https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1600&q=80&auto=format&fit=crop", fallback:"#0a0a0a" },
  karachi:  { flag:"🇵🇰", country:"Pakistan", tagline:"City of Lights",        img:"https://images.unsplash.com/photo-1548013146-72479768bada?w=1600&q=80&auto=format&fit=crop", fallback:"#0c1445" },
};

const CAT_ICONS: Record<string,string>  = { landmark:"🏛", museum:"🎨", food:"🍜", nature:"🌿", shopping:"🛍", religious:"🕌", nightlife:"🌃", adventure:"🧗", beach:"🏖", cultural:"🎭" };
const CAT_COLORS: Record<string,string> = { landmark:"#F59E0B", museum:"#A78BFA", food:"#F87171", nature:"#34D399", shopping:"#F472B6", religious:"#FB923C", nightlife:"#60A5FA", adventure:"#10B981", beach:"#38BDF8", cultural:"#C4B5FD" };

/* ─── Sub-components ─────────────────────────────────── */
function SLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-3)", marginBottom: 7 }}>
      {children}
    </div>
  );
}

function Pill({ active, color = "var(--accent)", onClick, children }: {
  active: boolean; color?: string; onClick: () => void; children: React.ReactNode;
}) {
  return (
    <button type="button" onClick={onClick} style={{
      padding: "5px 13px", borderRadius: 99, fontSize: 12, cursor: "pointer",
      border: `1px solid ${active ? `${color}40` : "var(--border)"}`,
      background: active ? `${color}12` : "transparent",
      color: active ? color : "var(--text-2)",
      transition: "all 0.15s", whiteSpace: "nowrap",
    }}>{children}</button>
  );
}

/* ─── Main ───────────────────────────────────────────── */
export default function TravelForm({ onSubmit, loading }: Props) {
  const isMobile = useIsMobile();
  const [cities, setCities]           = useState<string[]>([]);
  const [dest, setDest]               = useState("");
  const [days, setDays]               = useState(3);
  const [budget, setBudget]           = useState(500);
  const [traveler, setTraveler]       = useState("solo");
  const [pace, setPace]               = useState("balanced");
  const [date, setDate]               = useState("2025-06-01");
  const [solver, setSolver]           = useState("both");
  const [weights, setWeights]         = useState<Record<string,number>>({});
  const [mustAvoid, setMustAvoid]     = useState<string[]>([]);
  // interests always visible — no collapse state needed

  useEffect(() => {
    fetchCities()
      .then((c) => { setCities(c); if (c.length) setDest(c[0]); })
      .catch(() => { const fb=["paris","istanbul","tokyo","dubai","karachi"]; setCities(fb); setDest(fb[0]); });
  }, []);

  const activeCats  = useMemo(() => CATEGORIES.filter(c => !mustAvoid.includes(c)), [mustAvoid]);
  const totalWeight = useMemo(() => activeCats.reduce((s,c) => s+(weights[c]??0.5),0)||1, [activeCats,weights]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const w: Record<string,number> = {};
    for (const c of CATEGORIES) if (!mustAvoid.includes(c)) w[c] = weights[c]??0.5;
    onSubmit({ destination:dest, num_days:days, budget_usd:budget, traveler_type:traveler,
      interest_weights:w, pace, must_include:[], must_avoid_categories:mustAvoid, start_date:date, solver });
  }

  const k    = dest.toLowerCase();
  const meta = CITY_META[k] ?? { flag:"🌍", country:"", tagline:"", img:"", fallback:"#111" };

  return (
    <form onSubmit={handleSubmit}>

      {/* ══ CITY HERO ══════════════════════════════════ */}
      <div style={{ position:"relative", height:240, background:meta.fallback, overflow:"hidden" }}>
        {/* Photo layer */}
        {meta.img && (
          <div style={{
            position:"absolute", inset:0,
            backgroundImage:`url(${meta.img})`,
            backgroundSize:"cover", backgroundPosition:"center 35%",
            transition:"background-image 0.4s ease",
          }} />
        )}
        {/* Gradient — stronger at bottom for text legibility */}
        <div style={{
          position:"absolute", inset:0,
          background:"linear-gradient(to bottom, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0.6) 55%, rgba(0,0,0,0.92) 100%)",
        }} />
        {/* Subtle vignette */}
        <div style={{
          position:"absolute", inset:0,
          background:"radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.4) 100%)",
        }} />

        {/* Content */}
        <div style={{
          position:"absolute", bottom:0, left:0, right:0,
          padding: isMobile ? "0 16px 16px" : "0 28px 20px",
          maxWidth:1200, margin:"0 auto",
        }}>
          {/* City name */}
          <div style={{ fontSize: isMobile ? 26 : 34, fontWeight:700, color:"white", textTransform:"capitalize", lineHeight:1.15, letterSpacing:"-0.02em", textShadow:"0 2px 12px rgba(0,0,0,0.5)" }}>
            {dest || "Select a city"}
          </div>
          {meta.country && (
            <div style={{ fontSize:13, color:"rgba(255,255,255,0.55)", marginTop:3 }}>
              {meta.flag} {meta.country} — {meta.tagline}
            </div>
          )}

          {/* City pills */}
          <div style={{ display:"flex", gap:6, marginTop:14, flexWrap:"wrap" }}>
            {(cities.length ? cities : Object.keys(CITY_META)).map((c) => {
              const m = CITY_META[c.toLowerCase()];
              const active = dest === c;
              return (
                <button key={c} type="button" onClick={() => setDest(c)} style={{
                  padding:"4px 12px", borderRadius:99, fontSize:12, cursor:"pointer", border:"none",
                  background: active ? "white" : "rgba(255,255,255,0.14)",
                  color: active ? "#111" : "rgba(255,255,255,0.8)",
                  fontWeight: active ? 600 : 400, transition:"all 0.15s",
                  backdropFilter:"blur(4px)",
                }}>
                  {m?.flag} {c.charAt(0).toUpperCase()+c.slice(1)}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* ══ FORM CONTROLS BAR ═════════════════════════ */}
      <div style={{ background:"var(--surface)", borderBottom:"1px solid var(--border)" }}>
        <div style={{ maxWidth:1200, margin:"0 auto", padding: isMobile ? "12px 16px" : "16px 28px" }}>

          {/* Row 1: Trip params + submit */}
          <div style={{ display:"flex", gap:10, alignItems:"flex-end", flexWrap:"wrap" }}>

            {/* Days */}
            <div style={{ minWidth:88 }}>
              <SLabel>Days</SLabel>
              <div style={{ display:"flex", alignItems:"center", gap:4 }}>
                <button type="button" onClick={() => setDays(Math.max(1,days-1))}
                  style={{ width:26, height:26, borderRadius:4, border:"1px solid var(--border)", background:"transparent", color:"var(--text-2)", cursor:"pointer", fontSize:15 }}>−</button>
                <span style={{ width:28, textAlign:"center", fontSize:16, fontWeight:600, color:"var(--text)" }}>{days}</span>
                <button type="button" onClick={() => setDays(Math.min(14,days+1))}
                  style={{ width:26, height:26, borderRadius:4, border:"1px solid var(--border)", background:"transparent", color:"var(--text-2)", cursor:"pointer", fontSize:15 }}>+</button>
              </div>
            </div>

            {/* Budget */}
            <div>
              <SLabel>Total Budget</SLabel>
              <div style={{ position:"relative" }}>
                <span style={{ position:"absolute", left:9, top:"50%", transform:"translateY(-50%)", fontSize:14, fontWeight:700, color:"var(--amber)", pointerEvents:"none", zIndex:1 }}>$</span>
                <input type="number" min={1} value={budget} onChange={e=>setBudget(Number(e.target.value))}
                  placeholder="500"
                  className="field" style={{ paddingLeft:22, width:108, fontWeight:600, fontSize:14, color:"var(--text)" }} />
              </div>
              {/* Quick presets */}
              <div style={{ display:"flex", gap:4, marginTop:5 }}>
                {[200,500,1000,2000].map(v=>(
                  <button key={v} type="button" onClick={()=>setBudget(v)} style={{
                    fontSize:10, padding:"2px 7px", borderRadius:4, cursor:"pointer",
                    border:`1px solid ${budget===v?"var(--amber)":"var(--border)"}`,
                    background:budget===v?"rgba(245,158,11,0.1)":"transparent",
                    color:budget===v?"var(--amber)":"var(--text-3)", transition:"all 0.12s",
                  }}>${v}</button>
                ))}
              </div>
            </div>

            {/* Date */}
            <div>
              <SLabel>Start Date</SLabel>
              <div style={{ position:"relative" }}>
                <span style={{ position:"absolute", left:9, top:"50%", transform:"translateY(-50%)", fontSize:13, pointerEvents:"none", zIndex:1, lineHeight:1 }}>📅</span>
                <input type="date" value={date} onChange={e=>setDate(e.target.value)}
                  className="field" style={{ paddingLeft:28, width:148, colorScheme:"dark" }} />
              </div>
            </div>

            {/* Divider */}
            {!isMobile && <div style={{ width:1, height:36, background:"var(--border)", alignSelf:"flex-end", marginBottom:1 }} />}

            {/* Traveler */}
            <div>
              <SLabel>Traveler</SLabel>
              <div style={{ display:"flex", gap:5 }}>
                {[{v:"solo",l:"Solo"},{v:"couple",l:"Couple"},{v:"family",l:"Family"},{v:"friends",l:"Friends"}].map(t=>(
                  <Pill key={t.v} active={traveler===t.v} onClick={()=>setTraveler(t.v)}>{t.l}</Pill>
                ))}
              </div>
            </div>

            {/* Divider */}
            {!isMobile && <div style={{ width:1, height:36, background:"var(--border)", alignSelf:"flex-end", marginBottom:1 }} />}

            {/* Pace */}
            <div>
              <SLabel>Pace</SLabel>
              <div style={{ display:"flex", gap:5 }}>
                {[{v:"relaxed",l:"Relaxed",sub:"6h"},{v:"balanced",l:"Balanced",sub:"8h"},{v:"packed",l:"Packed",sub:"10h"}].map(p=>(
                  <button key={p.v} type="button" onClick={()=>setPace(p.v)} style={{
                    padding:"5px 12px", borderRadius:99, fontSize:12, cursor:"pointer",
                    border:`1px solid ${pace===p.v?"var(--accent-br)":"var(--border)"}`,
                    background:pace===p.v?"var(--accent-bg)":"transparent",
                    color:pace===p.v?"var(--accent)":"var(--text-2)", transition:"all 0.15s",
                  }}>
                    {p.l} <span style={{ opacity:0.5, fontSize:10 }}>{p.sub}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Divider */}
            {!isMobile && <div style={{ width:1, height:36, background:"var(--border)", alignSelf:"flex-end", marginBottom:1 }} />}

            {/* Solver */}
            <div>
              <SLabel>Solver</SLabel>
              <div style={{ display:"flex", gap:5 }}>
                {[{v:"both",l:"Both"},{v:"csp",l:"CSP+A*"},{v:"ga",l:"GA"}].map(s=>(
                  <Pill key={s.v} active={solver===s.v} onClick={()=>setSolver(s.v)}>{s.l}</Pill>
                ))}
              </div>
            </div>

            {/* Spacer */}
            <div style={{ flex:1 }} />

            {/* Generate button */}
            <div style={{ alignSelf:"flex-end", width: isMobile ? "100%" : undefined }}>
              <button type="submit" disabled={loading} style={{
                padding:"8px 24px", borderRadius:"var(--r)", border:"none",
                background:loading?"rgba(79,142,247,0.2)":"var(--accent)",
                color:loading?"rgba(255,255,255,0.4)":"white",
                fontSize:13, fontWeight:600, cursor:loading?"not-allowed":"pointer",
                transition:"all 0.15s", whiteSpace:"nowrap", height:36,
                width: isMobile ? "100%" : undefined,
              }}>
                {loading?"Solving…":"Generate →"}
              </button>
            </div>
          </div>

          {/* Row 2: Interests (always visible) */}
          <div style={{ marginTop:12, paddingTop:12, borderTop:"1px solid var(--border)" }}>

            {/* Header: label + distribution strip */}
            <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:12 }}>
              <span style={{ fontSize:10, fontWeight:600, letterSpacing:"0.08em", textTransform:"uppercase", color:"var(--text-3)", whiteSpace:"nowrap" }}>
                Interests
              </span>
              {/* Attention budget strip */}
              <div style={{ flex:1, height:6, borderRadius:3, display:"flex", overflow:"hidden", background:"rgba(255,255,255,0.04)" }}>
                {activeCats.map(cat => {
                  const pct = ((weights[cat]??0.5)/totalWeight)*100;
                  return (
                    <div key={cat} title={`${cat}: ${(weights[cat]??0.5).toFixed(1)}`} style={{
                      width:`${pct}%`, background:CAT_COLORS[cat]??"#666",
                      transition:"width 0.2s ease", minWidth:pct>1?2:0,
                    }} />
                  );
                })}
              </div>
              <span style={{ fontSize:10, color:"var(--text-3)", whiteSpace:"nowrap" }}>
                {activeCats.length}/{CATEGORIES.length} active
              </span>
            </div>

            {/* Sliders — always visible, 5 columns */}
            <div style={{ display:"grid", gridTemplateColumns: isMobile ? "repeat(2,1fr)" : "repeat(5,1fr)", gap:"10px 20px" }}>
              {CATEGORIES.map(cat => {
                const avoided = mustAvoid.includes(cat);
                const w = weights[cat]??0.5;
                return (
                  <div key={cat} style={{ display:"flex", flexDirection:"column", gap:5, opacity:avoided?0.38:1, transition:"opacity 0.15s" }}>
                    <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                      <span style={{ fontSize:12 }}>
                        {CAT_ICONS[cat]}{" "}
                        <span style={{ fontSize:10, color:"var(--text-2)", textTransform:"capitalize" }}>{cat}</span>
                      </span>
                      <div style={{ display:"flex", alignItems:"center", gap:5 }}>
                        <span style={{ fontSize:10, fontFamily:"monospace", color:avoided?"var(--red)":CAT_COLORS[cat] }}>
                          {avoided?"✕":w.toFixed(1)}
                        </span>
                        <button type="button"
                          onClick={()=>setMustAvoid(p=>p.includes(cat)?p.filter(c=>c!==cat):[...p,cat])}
                          style={{
                            padding:"1px 5px", fontSize:9, borderRadius:3, cursor:"pointer",
                            border:`1px solid ${avoided?"rgba(248,113,113,0.3)":"var(--border)"}`,
                            background:avoided?"rgba(248,113,113,0.08)":"transparent",
                            color:avoided?"var(--red)":"var(--text-3)", transition:"all 0.15s",
                          }}>{avoided?"on":"off"}</button>
                      </div>
                    </div>
                    <Slider value={w} onChange={v=>setWeights(p=>({...p,[cat]:v}))}
                      color={avoided?"rgba(255,255,255,0.06)":CAT_COLORS[cat]} disabled={avoided} />
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </form>
  );
}
