"use client";

interface SliderProps {
  value: number;               // 0.0 – 1.0
  onChange: (v: number) => void;
  color?: string;              // fill + active-notch color
  disabled?: boolean;
}

const STEPS   = 10;
const NOTCHES = Array.from({ length: STEPS + 1 }, (_, i) => i / STEPS);

function snap(v: number) {
  return Math.round(v * STEPS) / STEPS;
}

export default function Slider({ value, onChange, color = "var(--accent)", disabled = false }: SliderProps) {
  const pct        = snap(value) * 100;
  const fillColor  = disabled ? "rgba(255,255,255,0.07)" : color;
  const thumbColor = disabled ? "#2a2a2a" : "white";

  return (
    <div style={{
      position: "relative", flex: 1, height: 24,
      display: "flex", alignItems: "center",
    }}>
      {/* Notch tick marks */}
      {NOTCHES.map((n) => {
        const active = n * 100 <= pct;
        return (
          <div key={n} style={{
            position: "absolute",
            left: `${n * 100}%`,
            transform: "translateX(-50%)",
            width: 1,
            height: active ? 6 : 3,
            background: active ? fillColor : "rgba(255,255,255,0.1)",
            borderRadius: 1,
            transition: "height 0.08s, background 0.08s",
            pointerEvents: "none",
          }} />
        );
      })}

      {/* Track */}
      <div style={{
        position: "absolute", left: 0, right: 0,
        height: 2, borderRadius: 1,
        background: "rgba(255,255,255,0.07)",
      }}>
        <div style={{
          position: "absolute", left: 0, top: 0, bottom: 0,
          width: `${pct}%`,
          background: fillColor,
          borderRadius: 1,
          transition: "width 0.08s ease",
        }} />
      </div>

      {/* Thumb */}
      <div style={{
        position: "absolute",
        left: `calc(${pct / 100} * (100% - 12px))`,
        width: 12, height: 12, borderRadius: "50%",
        background: thumbColor,
        boxShadow: disabled ? "none" : "0 1px 3px rgba(0,0,0,0.45)",
        pointerEvents: "none",
        transition: "left 0.08s ease",
      }} />

      {/* Native input — invisible, handles all interaction */}
      <input
        type="range" min={0} max={1} step={0.1}
        value={snap(value)} disabled={disabled}
        onChange={(e) => onChange(snap(Number(e.target.value)))}
        style={{
          position: "absolute", inset: 0, width: "100%",
          opacity: 0, cursor: disabled ? "not-allowed" : "pointer", zIndex: 1,
        }}
      />
    </div>
  );
}
