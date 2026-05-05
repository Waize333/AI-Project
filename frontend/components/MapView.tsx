"use client";

import { useEffect, useRef } from "react";
import type { Itinerary } from "@/lib/types";
import { DAY_COLORS } from "@/lib/types";

interface Props { itinerary: Itinerary; }

/**
 * Fetches actual walking-road geometry from OSRM for a single segment.
 * Promise-based timeout — avoids AbortSignal.timeout (requires Node 17.3+).
 * Falls back to straight line on any error or timeout.
 */
function routeSegment(
  from: { lat: number; lon: number },
  to:   { lat: number; lon: number }
): Promise<[number, number][]> {
  const straight: [number, number][] = [[from.lat, from.lon], [to.lat, to.lon]];
  const url = `https://router.project-osrm.org/route/v1/walking/${from.lon},${from.lat};${to.lon},${to.lat}?geometries=geojson&overview=full`;

  return new Promise<[number, number][]>((resolve) => {
    const timer = setTimeout(() => resolve(straight), 5000);

    fetch(url)
      .then((r) => { if (!r.ok) throw new Error(`OSRM ${r.status}`); return r.json(); })
      .then((data) => {
        clearTimeout(timer);
        const coords = data?.routes?.[0]?.geometry?.coordinates;
        if (Array.isArray(coords) && coords.length > 0) {
          resolve(coords.map(([lon, lat]: [number, number]) => [lat, lon] as [number, number]));
        } else {
          resolve(straight);
        }
      })
      .catch(() => { clearTimeout(timer); resolve(straight); });
  });
}

export default function MapView({ itinerary }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef       = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    // Flag set by cleanup — gates every .addTo() call so a pending OSRM
    // fetch can't write to a map that was already destroyed.
    let destroyed = false;

    import("leaflet").then(async (L) => {
      // Re-check: StrictMode may have unmounted between the sync guard and here
      if (destroyed || !containerRef.current || mapRef.current) return;

      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl:       "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl:     "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      const allPois = Object.values(itinerary.days).flatMap((d) => d.pois);
      if (allPois.length === 0) return;

      const avgLat = allPois.reduce((s, p) => s + p.lat, 0) / allPois.length;
      const avgLon = allPois.reduce((s, p) => s + p.lon, 0) / allPois.length;

      const container = containerRef.current;
      const map = L.map(container).setView([avgLat, avgLon], 13);
      mapRef.current = map;

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap",
        maxZoom: 19,
      }).addTo(map);

      for (const [dayKey, dayRoute] of Object.entries(itinerary.days)) {
        if (destroyed) break;

        const dayNum = parseInt(dayKey);
        const color  = DAY_COLORS[(dayNum - 1) % DAY_COLORS.length];
        const pois   = dayRoute.pois;

        /* Markers */
        pois.forEach((poi, idx) => {
          if (destroyed) return;
          const icon = L.divIcon({
            className: "",
            html: `<div style="background:${color};color:white;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;border:2.5px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.5)">${idx + 1}</div>`,
            iconSize: [26, 26],
            iconAnchor: [13, 13],
          });
          L.marker([poi.lat, poi.lon], { icon })
            .addTo(map)
            .bindPopup(`
              <b style="font-size:13px">Stop ${idx+1} — Day ${dayNum}</b><br/>
              <span style="font-size:13px">${poi.name}</span><br/>
              <span style="color:#888;font-size:11px">${poi.category}</span><br/>
              <span style="font-size:11px">⭐ ${poi.rating} · $${poi.avg_cost_usd}</span>
            `);
        });

        /* Road route: fetch each consecutive segment in parallel */
        if (pois.length >= 2) {
          const segments = await Promise.all(
            pois.slice(0, -1).map((p, i) => routeSegment(p, pois[i + 1]))
          );

          // Bail out if cleanup ran while we were waiting for OSRM
          if (destroyed) break;

          const fullPath: [number, number][] = [];
          segments.forEach((seg, i) => {
            fullPath.push(...(i === 0 ? seg : seg.slice(1)));
          });

          if (fullPath.length >= 2) {
            L.polyline(fullPath, { color, weight: 4, opacity: 0.82 }).addTo(map);
          }
        }
      }
    });

    return () => {
      destroyed = true;
      if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
    };
  }, [itinerary]);

  return (
    <>
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <div ref={containerRef} style={{
        width: "100%", height: "100%", minHeight: 300,
        borderRadius: "var(--r)", border: "1px solid var(--border)",
      }} />
    </>
  );
}
