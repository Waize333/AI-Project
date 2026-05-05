"use client";

import { useEffect, useState } from "react";

const STAGES = [
  { name:"K-Means Clustering",  detail:"POIs grouped into K geographic day-clusters", formula:"argmin Σ ||xᵢ−μₖ||²",    color:"#60A5FA" },
  { name:"CSP + Backtracking",  detail:"AC-3 pruning · MRV · LCV · Forward checking",  formula:"AC-3 arc-consistency",   color:"#A78BFA" },
  { name:"A* Search",           detail:"Optimal intra-day routing, admissible heuristic",formula:"f(n)=g(n)+h(n), h=MST",  color:"#34D399" },
  { name:"Genetic Algorithm",   detail:"Comparison — 100 chromosomes, 200 generations", formula:"Tournament·OX·Elitism",  color:"#FB923C" },
];

/* ─── K-Means: centroids translate to converged positions ─ */
function KMeansSVG({ active, frame }: { active:boolean; frame:number }) {
  const dots = [
    {x:18,y:18,c:0},{x:30,y:30,c:0},{x:12,y:40,c:0},{x:28,y:52,c:0},{x:40,y:22,c:0},
    {x:62,y:14,c:1},{x:74,y:26,c:1},{x:58,y:36,c:1},{x:78,y:40,c:1},{x:68,y:52,c:1},
    {x:92,y:22,c:2},{x:100,y:40,c:2},{x:86,y:54,c:2},{x:104,y:56,c:2},
  ];
  const clr = ["#60A5FA","#A78BFA","#34D399"];
  const start = [{x:30,y:60},{x:60,y:10},{x:90,y:60}];
  const end   = [{x:26,y:34},{x:68,y:34},{x:95,y:42}];

  const t    = active ? Math.min(frame/60,1) : 1;
  const ease = t<0.5 ? 2*t*t : -1+(4-2*t)*t;
  const ctrs = start.map((s,i)=>({ x:s.x+(end[i].x-s.x)*ease, y:s.y+(end[i].y-s.y)*ease, c:clr[i] }));
  const colored = !active || frame>70;

  return (
    <svg viewBox="0 0 116 72" width="100%" height="100%">
      {t>0.8 && ctrs.map((c,i)=>(
        <circle key={`r${i}`} cx={c.x} cy={c.y} r={28} fill={c.c} fillOpacity={0.05}
          stroke={c.c} strokeWidth={0.6} strokeOpacity={0.2} strokeDasharray="3 2"/>
      ))}
      {dots.map((d,i)=>(
        <circle key={i} cx={d.x} cy={d.y} r={3} fill={colored?clr[d.c]:"#333"} fillOpacity={0.9}
          style={{transition:"fill 0.6s ease"}}/>
      ))}
      {ctrs.map((c,i)=>(
        <g key={`ctr${i}`}>
          <circle cx={c.x} cy={c.y} r={5.5} fill={c.c} stroke="rgba(255,255,255,0.3)" strokeWidth={1}/>
          {t>0.9&&<text x={c.x} y={c.y+14} textAnchor="middle" fill={c.c} fontSize={6} opacity={0.7}>Day {i+1}</text>}
        </g>
      ))}
      <text x={58} y={70} textAnchor="middle" fill="rgba(255,255,255,0.2)" fontSize={5.5}>
        {active&&frame<60?"Converging centroids…":"Clusters formed"}
      </text>
    </svg>
  );
}

/* ─── CSP: arc pruning (edges flash red → disappear) ──── */
function CSPSVG({ active, frame }: { active:boolean; frame:number }) {
  const vs = [{x:18,y:18},{x:58,y:12},{x:98,y:18},{x:18,y:52},{x:58,y:58},{x:98,y:52}];
  const edges = [[0,1],[1,2],[0,3],[1,4],[2,5],[3,4],[4,5],[1,3]];
  const pruned = [2,5,7];
  const assign = [0,1,2,0,1,2];
  const clr = ["#60A5FA","#A78BFA","#34D399"];
  const prunedCount = active ? Math.min(Math.floor(frame/25), pruned.length) : pruned.length;
  const assigned    = active ? Math.max(0, Math.floor((frame-30)/12)) : vs.length;

  return (
    <svg viewBox="0 0 116 72" width="100%" height="100%">
      {edges.map(([a,b],i)=>{
        if(pruned.slice(0,prunedCount).includes(i)) return null;
        const flashing = active && pruned[prunedCount]===i && (frame%25)/25 < 0.55;
        return <line key={i} x1={vs[a].x} y1={vs[a].y} x2={vs[b].x} y2={vs[b].y}
          stroke={flashing?"#F87171":"rgba(255,255,255,0.1)"} strokeWidth={flashing?1.5:1}/>;
      })}
      {vs.map((v,i)=>{
        const done = i<Math.min(assigned,vs.length);
        const c = done?clr[assign[i]]:undefined;
        return (
          <g key={i}>
            <rect x={v.x-10} y={v.y-9} width={20} height={18} rx={3}
              fill={done?`${c}20`:"rgba(255,255,255,0.04)"}
              stroke={done?c!:"rgba(255,255,255,0.1)"} strokeWidth={1}/>
            <text x={v.x} y={v.y+4} textAnchor="middle" fill={done?c!:"rgba(255,255,255,0.2)"} fontSize={7} fontWeight={500}>
              {done?`D${assign[i]+1}`:"?"}
            </text>
          </g>
        );
      })}
      <text x={58} y={70} textAnchor="middle" fill="rgba(255,255,255,0.2)" fontSize={5.5}>
        {active?(prunedCount<3?"AC-3 pruning arcs…":"Assigning variables…"):"Constraints satisfied"}
      </text>
    </svg>
  );
}

/* ─── A*: frontier wave then path trace ──────────────── */
function AStarSVG({ active, frame }: { active:boolean; frame:number }) {
  const ns  = [{x:10,y:38},{x:32,y:14},{x:62,y:8},{x:90,y:18},{x:104,y:44},{x:80,y:60},{x:44,y:58}];
  const all = [[0,1],[0,6],[1,2],[1,6],[2,3],[3,4],[4,5],[5,6],[2,6]];
  const path= [[0,1],[1,2],[2,3],[3,4],[4,5],[5,6],[6,0]];
  const dist: Record<number,number> = {0:0,1:1,6:1,2:2,3:3,4:4,5:3};

  const frontierT = active ? Math.min(frame/50,1) : 0;
  const pathT     = active ? Math.max(0,(frame-50)/50) : 1;
  const pathN     = Math.floor(pathT*path.length);

  const inFrontier=(i:number)=>dist[i]!==undefined&&dist[i]<=frontierT*4;
  const isPathEdge=(a:number,b:number)=>path.slice(0,pathN).some(([pa,pb])=>(pa===a&&pb===b)||(pa===b&&pb===a));
  const onPath=(i:number)=>path.slice(0,pathN).some(([a,b])=>a===i||b===i);

  return (
    <svg viewBox="0 0 116 72" width="100%" height="100%">
      {all.map(([a,b],i)=>(
        <line key={i} x1={ns[a].x} y1={ns[a].y} x2={ns[b].x} y2={ns[b].y}
          stroke={isPathEdge(a,b)?"#34D399":"rgba(255,255,255,0.07)"} strokeWidth={isPathEdge(a,b)?2:1}/>
      ))}
      {ns.map((n,i)=>(
        <circle key={i} cx={n.x} cy={n.y} r={i===0?5.5:4.5}
          fill={i===0?"#F87171":onPath(i)?"#34D399":inFrontier(i)?"#374151":"#1a1a1a"}
          stroke={onPath(i)?"#34D399":inFrontier(i)?"rgba(255,255,255,0.2)":"rgba(255,255,255,0.08)"}
          strokeWidth={1.5} style={{transition:"fill 0.3s ease"}}/>
      ))}
      <text x={5} y={10} fill="rgba(255,255,255,0.18)" fontSize={5.5}>f=g+h</text>
      <text x={58} y={70} textAnchor="middle" fill="rgba(255,255,255,0.2)" fontSize={5.5}>
        {active?(frame<50?"Expanding frontier…":"Tracing optimal path…"):"Optimal route"}
      </text>
    </svg>
  );
}

/* ─── GA: bars evolve + trend line rises ─────────────── */
function GASvg({ active, frame }: { active:boolean; frame:number }) {
  const gens = [[28,40,22,52,36,30],[42,52,36,60,46,42],[55,62,48,67,56,52]];
  const gen  = active ? Math.min(Math.floor(frame/33),2) : 2;
  const fit  = [...gens[gen]].sort((a,b)=>b-a);
  const best = gens.map(g=>Math.max(...g));
  const trendN = active ? Math.min(gen+1,3) : 3;
  const pts  = best.slice(0,trendN).map((f,i)=>({x:12+i*46, y:62-(f/70)*52}));
  const tp   = pts.map((p,i)=>`${i===0?"M":"L"}${p.x},${p.y}`).join(" ");

  return (
    <svg viewBox="0 0 116 72" width="100%" height="100%">
      <line x1={10} y1={8} x2={10} y2={62} stroke="rgba(255,255,255,0.08)" strokeWidth={0.5}/>
      <line x1={10} y1={62} x2={112} y2={62} stroke="rgba(255,255,255,0.08)" strokeWidth={0.5}/>
      {fit.map((f,i)=>{
        const x=14+i*16, h=(f/70)*52;
        return (
          <g key={i}>
            <rect x={x} y={62-h} width={13} height={h} fill={i===0?"#34D399":"rgba(255,255,255,0.1)"} rx={2}/>
            {i===0&&<text x={x+6.5} y={62-h-3} textAnchor="middle" fill="#34D399" fontSize={7}>★</text>}
          </g>
        );
      })}
      {pts.length>=2&&<path d={tp} fill="none" stroke="#34D399" strokeWidth={1.5} strokeOpacity={0.7} strokeLinejoin="round"/>}
      {pts.map((p,i)=><circle key={i} cx={p.x} cy={p.y} r={2.5} fill="#34D399" fillOpacity={0.8}/>)}
      <text x={10} y={70} fill="rgba(255,255,255,0.22)" fontSize={5.5}>Gen {gen+1} · Best:{Math.max(...gens[gen])}</text>
    </svg>
  );
}

/* ─── Main ───────────────────────────────────────────── */
interface Props { loading: boolean; hasResults?: boolean; }

export default function AlgorithmVisualizer({ loading, hasResults=false }: Props) {
  const [active, setActive] = useState<number|null>(null);
  const [done,   setDone]   = useState<Set<number>>(()=>new Set<number>());
  const [frame,  setFrame]  = useState(0);

  useEffect(()=>{
    if(!loading){ setActive(null); setDone(new Set()); setFrame(0); return; }
    let s=0; setActive(0); setDone(new Set());
    const t=setInterval(()=>{
      setDone(p=>{const ns=new Set(Array.from(p)); ns.add(s); return ns;});
      s=(s+1)%STAGES.length; setActive(s); setFrame(0);
    },2800);
    return ()=>clearInterval(t);
  },[loading]);

  useEffect(()=>{
    if(active===null) return;
    const id=setInterval(()=>setFrame(f=>f>=99?0:f+1),55);
    return ()=>clearInterval(id);
  },[active]);

  const vizs=[
    <KMeansSVG key="km"    active={active===0} frame={frame}/>,
    <CSPSVG    key="csp"   active={active===1} frame={frame}/>,
    <AStarSVG  key="astar" active={active===2} frame={frame}/>,
    <GASvg     key="ga"    active={active===3} frame={frame}/>,
  ];

  /* ── Compact receipt ─────────────────────────────── */
  if(hasResults && !loading){
    return (
      <div className="anim-enter" style={{
        background:"var(--surface)", border:"1px solid var(--border)", borderRadius:"var(--r2)",
        padding:"10px 18px", display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:8,
      }}>
        <div style={{ display:"flex", alignItems:"center", gap:10, flexWrap:"wrap" }}>
          {STAGES.map((s,i)=>(
            <span key={i} style={{ display:"flex", alignItems:"center", gap:5, fontSize:12 }}>
              <span style={{ width:17, height:17, borderRadius:"50%", background:"var(--green-bg)", border:"1.5px solid var(--green)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:8, fontWeight:700, color:"var(--green)" }}>✓</span>
              <span style={{ color:"var(--text-2)" }}>{s.name.split(" ")[0]}</span>
              {i<STAGES.length-1&&<span style={{ color:"var(--text-3)",marginLeft:-4 }}>→</span>}
            </span>
          ))}
        </div>
        <span style={{ fontSize:11, color:"var(--text-3)", fontFamily:"monospace" }}>Pipeline complete</span>
      </div>
    );
  }

  /* ── Full horizontal pipeline ────────────────────── */
  return (
    <div style={{ border:"1px solid var(--border)", borderRadius:"var(--r2)", overflow:"hidden", background:"var(--surface)" }}>
      {/* Header */}
      <div style={{ padding:"11px 18px", borderBottom:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
        <span style={{ fontSize:13, fontWeight:600, color:"var(--text)" }}>Algorithm Pipeline</span>
        {loading
          ? <span style={{ display:"flex", alignItems:"center", gap:6, fontSize:12, color:"var(--text-2)" }}>
              <span className="anim-blink" style={{ display:"inline-block", width:6, height:6, borderRadius:"50%", background:"var(--accent)" }}/>Running
            </span>
          : <span style={{ fontSize:11, color:"var(--text-3)" }}>4 stages · always visible</span>
        }
      </div>

      {/* Horizontal stage cards */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)" }}>
        {STAGES.map((s,i)=>{
          const isActive = active===i;
          const isDone   = done.has(i);

          return (
            <div key={i} className={`shimmer-wrap ${isActive?"":""} anim-enter d${i+1}`}
              style={{
                borderRight: i<3?"1px solid var(--border)":"none",
                padding:"16px 16px 14px",
                background: isActive ? `${s.color}07` : "transparent",
                transition:"background 0.3s",
                position:"relative",
              }}>

              {/* Top row: number + status dot */}
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10 }}>
                <span style={{ fontSize:10, fontFamily:"monospace", color:`${s.color}55` }}>0{i+1}</span>
                <div className={isActive?"anim-blink":""} style={{
                  width:18, height:18, borderRadius:"50%",
                  border:`1.5px solid ${isDone?"var(--green)":isActive?s.color:"rgba(255,255,255,0.1)"}`,
                  background:isDone?"var(--green-bg)":isActive?`${s.color}14`:"transparent",
                  display:"flex", alignItems:"center", justifyContent:"center",
                  fontSize:8, fontWeight:700,
                  color:isDone?"var(--green)":isActive?s.color:"rgba(255,255,255,0.18)",
                }}>
                  {isDone?"✓":i+1}
                </div>
              </div>

              {/* Stage name */}
              <div style={{
                fontSize:12, fontWeight:600, marginBottom:3, transition:"color 0.2s",
                color:isActive?s.color:isDone?"var(--text)":"var(--text-2)",
              }}>{s.name}</div>

              {/* Detail */}
              <div style={{ fontSize:10, color:"var(--text-3)", lineHeight:1.4, marginBottom:10 }}>{s.detail}</div>

              {/* SVG visualization */}
              <div style={{ height:80, opacity:!loading&&!isDone&&active===null?0.28:1, transition:"opacity 0.3s" }}>
                {vizs[i]}
              </div>

              {/* Formula */}
              <div style={{
                fontSize:9, fontFamily:"monospace", marginTop:8, transition:"color 0.2s",
                color:isActive?`${s.color}80`:"rgba(255,255,255,0.1)",
              }}>{s.formula}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
