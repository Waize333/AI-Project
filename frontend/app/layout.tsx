import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Travel Planner",
  description: "Classical AI — CSP, A*, K-Means, Genetic Algorithm",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ background: "var(--bg)", color: "var(--text)", margin: 0 }}>

        <header style={{
          position: "sticky", top: 0, zIndex: 50,
          background: "var(--bg)",
          borderBottom: "1px solid var(--border)",
          height: 52, display: "flex", alignItems: "center",
        }}>
          <div style={{
            maxWidth: 1100, margin: "0 auto", width: "100%",
            padding: "0 24px",
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 26, height: 26, borderRadius: 6,
                background: "var(--accent)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 13, color: "white",
              }}>✈</div>
              <span style={{ fontSize: 14, fontWeight: 600 }}>AI Travel Planner</span>
            </div>

            <div style={{ display: "flex", gap: 20, fontSize: 12, color: "var(--text-3)" }}>
              <span>K-Means</span>
              <span>CSP + AC-3</span>
              <span>A* Search</span>
              <span>Genetic Algorithm</span>
            </div>
          </div>
        </header>

        <main>{children}</main>

        <footer style={{
          borderTop: "1px solid var(--border)", marginTop: 64,
          padding: "20px 0", textAlign: "center",
          fontSize: 12, color: "var(--text-3)",
        }}>
          AI Travel Planner — University AI Course Project
        </footer>
      </body>
    </html>
  );
}
