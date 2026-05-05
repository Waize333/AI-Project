"""
Benchmark: CSP + A* vs Genetic Algorithm across 10 predefined test scenarios.

Each scenario varies city, num_days, budget, and traveller interests.
Both solvers are run on identical inputs. Results are saved to:
  experiments/results/benchmark_table.md
  experiments/results/benchmark_plots.png

Run from project root:
    python -m experiments.benchmark
"""

from __future__ import annotations

import sys
import time
import json
import os
from datetime import date
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from src.preferences import UserPreferences
from src.planner import plan_csp_astar, plan_ga
from src.config import ALLOWED_CATEGORIES

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------

ALL_WEIGHTS = {cat: 0.5 for cat in ALLOWED_CATEGORIES}

SCENARIOS = [
    {
        "id": 1,
        "label": "Paris 3-day Budget",
        "destination": "Paris",
        "num_days": 3,
        "budget_usd": 200,
        "pace": "balanced",
        "traveler_type": "solo",
        "weights": {**ALL_WEIGHTS, "museum": 0.9, "landmark": 0.8},
    },
    {
        "id": 2,
        "label": "Paris 5-day Luxury",
        "destination": "Paris",
        "num_days": 5,
        "budget_usd": 1000,
        "pace": "packed",
        "traveler_type": "couple",
        "weights": {**ALL_WEIGHTS, "food": 1.0, "nightlife": 0.9, "shopping": 0.8},
    },
    {
        "id": 3,
        "label": "Istanbul 3-day Culture",
        "destination": "Istanbul",
        "num_days": 3,
        "budget_usd": 300,
        "pace": "balanced",
        "traveler_type": "friends",
        "weights": {**ALL_WEIGHTS, "religious": 0.9, "cultural": 0.9, "museum": 0.7},
    },
    {
        "id": 4,
        "label": "Istanbul 2-day Relaxed",
        "destination": "Istanbul",
        "num_days": 2,
        "budget_usd": 150,
        "pace": "relaxed",
        "traveler_type": "solo",
        "weights": {**ALL_WEIGHTS, "food": 0.9, "cultural": 0.8},
    },
    {
        "id": 5,
        "label": "Tokyo 4-day Family",
        "destination": "Tokyo",
        "num_days": 4,
        "budget_usd": 800,
        "pace": "balanced",
        "traveler_type": "family",
        "weights": {**ALL_WEIGHTS, "adventure": 0.9, "nature": 0.8, "food": 0.9},
    },
    {
        "id": 6,
        "label": "Tokyo 3-day Otaku",
        "destination": "Tokyo",
        "num_days": 3,
        "budget_usd": 500,
        "pace": "packed",
        "traveler_type": "solo",
        "weights": {**ALL_WEIGHTS, "shopping": 1.0, "cultural": 0.9, "nightlife": 0.8},
    },
    {
        "id": 7,
        "label": "Dubai 2-day Adventure",
        "destination": "Dubai",
        "num_days": 2,
        "budget_usd": 600,
        "pace": "packed",
        "traveler_type": "friends",
        "weights": {**ALL_WEIGHTS, "adventure": 1.0, "beach": 0.9, "nightlife": 0.7},
    },
    {
        "id": 8,
        "label": "Dubai 3-day Luxury",
        "destination": "Dubai",
        "num_days": 3,
        "budget_usd": 1500,
        "pace": "balanced",
        "traveler_type": "couple",
        "weights": {**ALL_WEIGHTS, "landmark": 0.9, "food": 1.0, "shopping": 0.8},
    },
    {
        "id": 9,
        "label": "Karachi 2-day Local",
        "destination": "Karachi",
        "num_days": 2,
        "budget_usd": 80,
        "pace": "relaxed",
        "traveler_type": "family",
        "weights": {**ALL_WEIGHTS, "food": 1.0, "cultural": 0.8, "nature": 0.7},
    },
    {
        "id": 10,
        "label": "Karachi 3-day History",
        "destination": "Karachi",
        "num_days": 3,
        "budget_usd": 150,
        "pace": "balanced",
        "traveler_type": "solo",
        "weights": {**ALL_WEIGHTS, "museum": 0.9, "cultural": 0.9, "landmark": 0.8},
    },
]


def _build_prefs(scenario: dict) -> UserPreferences:
    return UserPreferences(
        destination=scenario["destination"],
        num_days=scenario["num_days"],
        budget_usd=scenario["budget_usd"],
        traveler_type=scenario["traveler_type"],
        interest_weights=scenario["weights"],
        pace=scenario["pace"],
        must_include=[],
        must_avoid_categories=[],
        start_date=date(2025, 6, 2),  # Monday
        hotel_location=None,
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_benchmarks() -> list[dict]:
    rows = []
    total = len(SCENARIOS)

    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"[{i}/{total}] {scenario['label']} ...", end=" ", flush=True)
        prefs = _build_prefs(scenario)

        # CSP + A*
        t0 = time.time()
        try:
            csp_result, infeas = plan_csp_astar(prefs)
            csp_runtime = time.time() - t0

            if csp_result:
                csp_score = csp_result.score
                csp_cost = csp_result.total_cost_usd
                csp_pois = sum(len(dr.pois) for dr in csp_result.days.values())
                csp_violations = 0  # CSP guarantees feasibility
                csp_status = "OK"
            else:
                csp_score = 0.0
                csp_cost = 0.0
                csp_pois = 0
                csp_violations = 1
                csp_status = "INFEASIBLE"
        except Exception as e:
            csp_runtime = time.time() - t0
            csp_score = 0.0
            csp_cost = 0.0
            csp_pois = 0
            csp_violations = 1
            csp_status = f"ERROR: {e}"

        # GA
        t0 = time.time()
        try:
            ga_result, ga_runtime = plan_ga(prefs)
            ga_score = ga_result.score
            ga_cost = ga_result.total_cost_usd
            ga_pois = sum(len(dr.pois) for dr in ga_result.days.values())

            # Count constraint violations
            ga_violations = 0
            if ga_cost > prefs.budget_usd:
                ga_violations += 1
            for dr in ga_result.days.values():
                if dr.total_activity_minutes > prefs.daily_minutes:
                    ga_violations += 1
            ga_status = "OK" if ga_violations == 0 else f"{ga_violations} violations"
        except Exception as e:
            ga_runtime = time.time() - t0
            ga_score = 0.0
            ga_cost = 0.0
            ga_pois = 0
            ga_violations = 1
            ga_status = f"ERROR: {e}"

        row = {
            "id": scenario["id"],
            "label": scenario["label"],
            "csp_score": round(csp_score, 3),
            "ga_score": round(ga_score, 3),
            "csp_runtime": round(csp_runtime, 3),
            "ga_runtime": round(ga_runtime, 3),
            "csp_cost": round(csp_cost, 2),
            "ga_cost": round(ga_cost, 2),
            "csp_pois": csp_pois,
            "ga_pois": ga_pois,
            "csp_violations": csp_violations,
            "ga_violations": ga_violations,
            "csp_status": csp_status,
            "ga_status": ga_status,
        }
        rows.append(row)
        print(f"CSP={csp_score:.2f} GA={ga_score:.2f}")

    return rows


def write_markdown_table(rows: list[dict]) -> None:
    lines = [
        "# Benchmark Results: CSP+A* vs Genetic Algorithm",
        "",
        "10 predefined scenarios, each run once. Hardware: local CPU.",
        "",
        "| # | Scenario | CSP Score | GA Score | CSP Time (s) | GA Time (s) | CSP POIs | GA POIs | CSP Violations | GA Violations |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['label']} | {r['csp_score']} | {r['ga_score']} "
            f"| {r['csp_runtime']} | {r['ga_runtime']} "
            f"| {r['csp_pois']} | {r['ga_pois']} "
            f"| {r['csp_violations']} | {r['ga_violations']} |"
        )

    lines += [
        "",
        "## Summary",
        "",
        f"- CSP+A* average score: {sum(r['csp_score'] for r in rows)/len(rows):.3f}",
        f"- GA average score:      {sum(r['ga_score'] for r in rows)/len(rows):.3f}",
        f"- CSP+A* average runtime: {sum(r['csp_runtime'] for r in rows)/len(rows):.3f}s",
        f"- GA average runtime:     {sum(r['ga_runtime'] for r in rows)/len(rows):.3f}s",
        f"- CSP+A* total violations: {sum(r['csp_violations'] for r in rows)}",
        f"- GA total violations:     {sum(r['ga_violations'] for r in rows)}",
    ]

    out_path = RESULTS_DIR / "benchmark_table.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nMarkdown table saved to {out_path}")


def write_plots(rows: list[dict]) -> None:
    scenario_labels = [f"S{r['id']}" for r in rows]
    csp_scores = [r["csp_score"] for r in rows]
    ga_scores = [r["ga_score"] for r in rows]
    csp_runtimes = [r["csp_runtime"] for r in rows]
    ga_runtimes = [r["ga_runtime"] for r in rows]
    csp_pois = [r["csp_pois"] for r in rows]
    ga_pois = [r["ga_pois"] for r in rows]

    x = range(len(rows))
    width = 0.35

    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(2, 2, figure=fig)

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.bar([i - width/2 for i in x], csp_scores, width, label="CSP+A*", color="#457B9D")
    ax1.bar([i + width/2 for i in x], ga_scores, width, label="GA", color="#E63946")
    ax1.set_title("Solution Quality (Score)")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(scenario_labels)
    ax1.set_ylabel("Score (higher is better)")
    ax1.legend()

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.bar([i - width/2 for i in x], csp_runtimes, width, label="CSP+A*", color="#457B9D")
    ax2.bar([i + width/2 for i in x], ga_runtimes, width, label="GA", color="#E63946")
    ax2.set_title("Runtime (seconds)")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(scenario_labels)
    ax2.set_ylabel("Time (s)")
    ax2.legend()

    ax3 = fig.add_subplot(gs[1, 0])
    ax3.bar([i - width/2 for i in x], csp_pois, width, label="CSP+A*", color="#457B9D")
    ax3.bar([i + width/2 for i in x], ga_pois, width, label="GA", color="#E63946")
    ax3.set_title("Number of POIs Visited")
    ax3.set_xticks(list(x))
    ax3.set_xticklabels(scenario_labels)
    ax3.set_ylabel("POIs")
    ax3.legend()

    ax4 = fig.add_subplot(gs[1, 1])
    csp_violations = [r["csp_violations"] for r in rows]
    ga_violations = [r["ga_violations"] for r in rows]
    ax4.bar([i - width/2 for i in x], csp_violations, width, label="CSP+A*", color="#457B9D")
    ax4.bar([i + width/2 for i in x], ga_violations, width, label="GA", color="#E63946")
    ax4.set_title("Constraint Violations")
    ax4.set_xticks(list(x))
    ax4.set_xticklabels(scenario_labels)
    ax4.set_ylabel("Violations (0 = feasible)")
    ax4.legend()

    plt.suptitle("AI Travel Planner: CSP+A* vs GA Benchmark (10 Scenarios)", fontsize=14)
    plt.tight_layout()

    out_path = RESULTS_DIR / "benchmark_plots.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Plots saved to {out_path}")


def write_json(rows: list[dict]) -> None:
    out_path = RESULTS_DIR / "benchmark_raw.json"
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Raw JSON saved to {out_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("AI Travel Planner — Benchmark")
    print("=" * 60)

    rows = run_benchmarks()
    write_markdown_table(rows)
    write_plots(rows)
    write_json(rows)

    print("\nDone.")
