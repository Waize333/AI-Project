"""
AI Travel Planner — Streamlit application entry point.

Run with:
    streamlit run app.py

Pages:
  1. Input Form      — all UserPreferences fields
  2. Solver Selection — CSP+A* / GA / Both
  3. Itinerary View  — day-by-day cards with POI details
  4. Map View        — folium map with routes
  5. Comparison View — side-by-side scores and runtimes (Both mode)
  6. Export          — PDF and JSON download
"""

from __future__ import annotations

import json
import io
import math
import time
from datetime import date, timedelta

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src.data_loader import available_cities, load_city
from src.preferences import UserPreferences
from src.planner import plan_csp_astar, plan_ga, plan_both
from src.config import ALLOWED_CATEGORIES, PACE_HOURS
from src.scorer import Itinerary, DayRoute
from src.utils import minutes_to_hhmm

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DAY_COLORS = [
    "#E63946", "#457B9D", "#2A9D8F", "#E9C46A",
    "#F4A261", "#264653", "#A8DADC", "#6D6875",
]

CATEGORY_ICONS = {
    "landmark": "🏛", "museum": "🏛", "food": "🍽", "nature": "🌿",
    "shopping": "🛍", "religious": "🕌", "nightlife": "🎭",
    "adventure": "🏄", "beach": "🏖", "cultural": "🎨",
}


def _category_icon(category: str) -> str:
    return CATEGORY_ICONS.get(category, "📍")


def _itinerary_to_json(itinerary: Itinerary) -> str:
    """Serialise itinerary to a clean JSON string."""
    data = {
        "destination": itinerary.destination,
        "solver": itinerary.solver,
        "score": round(itinerary.score, 3),
        "total_cost_usd": round(itinerary.total_cost_usd, 2),
        "total_travel_minutes": round(itinerary.total_travel_minutes, 1),
        "days": {},
    }
    for d, route in sorted(itinerary.days.items()):
        data["days"][str(d)] = {
            "pois": [
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "cost_usd": p.avg_cost_usd,
                    "duration_minutes": p.avg_duration_minutes,
                    "rating": p.rating,
                    "lat": p.lat,
                    "lon": p.lon,
                }
                for p in route.pois
            ],
            "total_cost_usd": round(route.total_cost_usd, 2),
            "activity_minutes": round(route.total_activity_minutes, 1),
            "travel_minutes": round(route.total_travel_minutes, 1),
        }
    return json.dumps(data, indent=2)


def _build_pdf(itinerary: Itinerary, prefs: UserPreferences) -> bytes:
    """Generate a PDF export of the itinerary using reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle("title", parent=styles["Title"],
                                     fontSize=24, spaceAfter=6)
        story.append(Paragraph(f"AI Travel Planner — {itinerary.destination}", title_style))
        story.append(Paragraph(
            f"Solver: {itinerary.solver} | Score: {itinerary.score:.2f} | "
            f"Budget used: ${itinerary.total_cost_usd:.0f} / ${prefs.budget_usd:.0f}",
            styles["Normal"]
        ))
        story.append(Spacer(1, 0.5*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Spacer(1, 0.3*cm))

        for d in sorted(itinerary.days.keys()):
            route = itinerary.days[d]
            trip_date = prefs.start_date + timedelta(days=d - 1)

            # Day header
            day_heading = ParagraphStyle("day_heading", parent=styles["Heading2"],
                                         fontSize=14, textColor=colors.HexColor("#1a1a2e"))
            story.append(Paragraph(
                f"Day {d} — {trip_date.strftime('%A, %d %B %Y')}",
                day_heading
            ))
            story.append(Paragraph(
                f"Activity: {minutes_to_hhmm(route.total_activity_minutes)} | "
                f"Travel: {minutes_to_hhmm(route.total_travel_minutes)} | "
                f"Cost: ${route.total_cost_usd:.0f}",
                styles["Normal"]
            ))
            story.append(Spacer(1, 0.2*cm))

            if route.pois:
                table_data = [["#", "Place", "Category", "Duration", "Cost", "Rating"]]
                for i, poi in enumerate(route.pois, 1):
                    table_data.append([
                        str(i),
                        poi.name,
                        poi.category.capitalize(),
                        f"{poi.avg_duration_minutes} min",
                        f"${poi.avg_cost_usd:.0f}",
                        f"{poi.rating}/5",
                    ])

                tbl = Table(table_data, colWidths=[1*cm, 7*cm, 3*cm, 2.5*cm, 2*cm, 2*cm])
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#457B9D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(tbl)
            else:
                story.append(Paragraph("No POIs assigned to this day.", styles["Normal"]))

            story.append(Spacer(1, 0.5*cm))

        doc.build(story)
        return buffer.getvalue()

    except ImportError:
        return b""


def _build_map(itinerary: Itinerary, hotel: tuple) -> folium.Map:
    """Create a folium map with colour-coded day routes."""
    all_lats = [hotel[0]] + [
        p.lat for route in itinerary.days.values() for p in route.pois
    ]
    all_lons = [hotel[1]] + [
        p.lon for route in itinerary.days.values() for p in route.pois
    ]
    center = (sum(all_lats) / len(all_lats), sum(all_lons) / len(all_lons))
    m = folium.Map(location=center, zoom_start=13, tiles="CartoDB positron")

    # Hotel marker
    folium.Marker(
        location=hotel,
        popup="Hotel",
        icon=folium.Icon(color="black", icon="home", prefix="fa"),
    ).add_to(m)

    for day_num, route in sorted(itinerary.days.items()):
        color = DAY_COLORS[(day_num - 1) % len(DAY_COLORS)]
        coords = [hotel] + [(p.lat, p.lon) for p in route.pois] + [hotel]

        # Route line
        if len(coords) > 2:
            folium.PolyLine(
                locations=coords,
                color=color,
                weight=3,
                opacity=0.7,
                tooltip=f"Day {day_num}",
            ).add_to(m)

        # POI markers
        for i, poi in enumerate(route.pois, 1):
            folium.CircleMarker(
                location=(poi.lat, poi.lon),
                radius=10,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=folium.Popup(
                    f"<b>Day {day_num} — Stop {i}</b><br>"
                    f"{poi.name}<br>"
                    f"Category: {poi.category}<br>"
                    f"Duration: {poi.avg_duration_minutes} min<br>"
                    f"Cost: ${poi.avg_cost_usd}<br>"
                    f"Rating: {poi.rating}/5",
                    max_width=250,
                ),
                tooltip=f"Day {day_num}: {poi.name}",
            ).add_to(m)

    return m


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "itinerary_csp" not in st.session_state:
    st.session_state.itinerary_csp = None
if "itinerary_ga" not in st.session_state:
    st.session_state.itinerary_ga = None
if "infeasibility" not in st.session_state:
    st.session_state.infeasibility = None
if "prefs" not in st.session_state:
    st.session_state.prefs = None

# ---------------------------------------------------------------------------
# Sidebar — Input Form
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("AI Travel Planner")
    st.caption("Powered by K-Means · CSP · A* · GA")
    st.divider()

    cities = available_cities()
    destination = st.selectbox("Destination", cities, index=0)

    col1, col2 = st.columns(2)
    with col1:
        num_days = st.number_input("Days", min_value=1, max_value=14, value=3)
    with col2:
        budget = st.number_input("Budget (USD)", min_value=50, max_value=50000, value=500, step=50)

    traveler_type = st.selectbox("Traveller type", ["solo", "couple", "family", "friends"])
    pace = st.select_slider("Pace", options=["relaxed", "balanced", "packed"], value="balanced")
    start_date = st.date_input("Start date", value=date.today() + timedelta(days=7))

    st.markdown("**Interest weights** (0 = not interested, 1 = love it)")
    weights: dict[str, float] = {}
    for cat in ALLOWED_CATEGORIES:
        icon = _category_icon(cat)
        weights[cat] = st.slider(f"{icon} {cat.capitalize()}", 0.0, 1.0, 0.5, step=0.1, key=f"w_{cat}")

    st.divider()
    st.markdown("**Advanced**")
    must_avoid_input = st.multiselect(
        "Must-avoid categories",
        options=ALLOWED_CATEGORIES,
        default=[],
    )

    solver_mode = st.radio(
        "Solver",
        ["CSP + A* (recommended)", "GA (comparison)", "Both (benchmark)"],
        index=0,
    )

    generate = st.button("Generate Itinerary", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.title(f"AI Travel Planner")

if generate:
    prefs = UserPreferences(
        destination=destination,
        num_days=int(num_days),
        budget_usd=float(budget),
        traveler_type=traveler_type,
        interest_weights=weights,
        pace=pace,
        must_include=[],
        must_avoid_categories=must_avoid_input,
        start_date=start_date,
        hotel_location=None,
    )

    try:
        prefs.validate()
    except ValueError as e:
        st.error(f"Input error: {e}")
        st.stop()

    st.session_state.prefs = prefs
    st.session_state.infeasibility = None
    st.session_state.itinerary_csp = None
    st.session_state.itinerary_ga = None

    with st.spinner("Planning your trip..."):
        if "CSP" in solver_mode:
            csp_result, infeasibility = plan_csp_astar(prefs)
            st.session_state.itinerary_csp = csp_result
            st.session_state.infeasibility = infeasibility

        if "GA" in solver_mode:
            ga_result, _ = plan_ga(prefs)
            st.session_state.itinerary_ga = ga_result

# ------- Display results -------

infeasibility = st.session_state.infeasibility
itinerary_csp = st.session_state.itinerary_csp
itinerary_ga = st.session_state.itinerary_ga
prefs = st.session_state.prefs

if infeasibility and itinerary_csp is None:
    st.error(f"**Infeasible itinerary detected**")
    st.warning(infeasibility.message)
    st.info(f"**Suggestion:** {infeasibility.suggestion}")
    if infeasibility.suggested_budget:
        st.metric("Suggested minimum budget", f"${infeasibility.suggested_budget:.0f}")
    if infeasibility.suggested_days:
        st.metric("Suggested trip length", f"{infeasibility.suggested_days} days")

elif itinerary_csp or itinerary_ga:
    tab_labels = []
    if itinerary_csp:
        tab_labels.append("CSP + A* Itinerary")
        tab_labels.append("Map View")
    if itinerary_ga:
        tab_labels.append("GA Itinerary")
    if itinerary_csp and itinerary_ga:
        tab_labels.append("Comparison")
    tab_labels.append("Export")

    tabs = st.tabs(tab_labels)
    tab_idx = 0

    def render_itinerary(itinerary: Itinerary, prefs: UserPreferences, tab):
        with tab:
            # Summary metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Score", f"{itinerary.score:.2f}")
            c2.metric("Total cost", f"${itinerary.total_cost_usd:.0f} / ${prefs.budget_usd:.0f}")
            c3.metric("Total travel", minutes_to_hhmm(itinerary.total_travel_minutes))
            c4.metric("Solver runtime", f"{itinerary.runtime_seconds:.2f}s")

            st.divider()

            for d in sorted(itinerary.days.keys()):
                route = itinerary.days[d]
                trip_date = prefs.start_date + timedelta(days=d - 1)
                color = DAY_COLORS[(d - 1) % len(DAY_COLORS)]

                with st.expander(
                    f"Day {d} — {trip_date.strftime('%A, %d %b')} "
                    f"| {len(route.pois)} places "
                    f"| ${route.total_cost_usd:.0f} "
                    f"| {minutes_to_hhmm(route.total_activity_minutes + route.total_travel_minutes)}",
                    expanded=(d == 1),
                ):
                    if not route.pois:
                        st.info("No POIs assigned to this day.")
                        continue

                    for i, poi in enumerate(route.pois, 1):
                        icon = _category_icon(poi.category)
                        st.markdown(
                            f"**{i}. {icon} {poi.name}**  \n"
                            f"`{poi.category}` · "
                            f"{poi.avg_duration_minutes} min · "
                            f"${poi.avg_cost_usd:.0f} · "
                            f"⭐ {poi.rating}"
                        )

                    st.caption(
                        f"Activity: {minutes_to_hhmm(route.total_activity_minutes)} | "
                        f"Travel: {minutes_to_hhmm(route.total_travel_minutes)} | "
                        f"Day cost: ${route.total_cost_usd:.0f}"
                    )

    # Render CSP tab
    if itinerary_csp:
        render_itinerary(itinerary_csp, prefs, tabs[tab_idx])
        tab_idx += 1

        # Map tab
        with tabs[tab_idx]:
            hotel = prefs.hotel_location or (0.0, 0.0)
            m = _build_map(itinerary_csp, hotel)
            st_folium(m, use_container_width=True, height=600)
        tab_idx += 1

    # GA tab
    if itinerary_ga:
        render_itinerary(itinerary_ga, prefs, tabs[tab_idx])
        tab_idx += 1

    # Comparison tab
    if itinerary_csp and itinerary_ga:
        with tabs[tab_idx]:
            st.subheader("CSP + A* vs Genetic Algorithm")

            col_a, col_b = st.columns(2)
            metrics = {
                "Score": (itinerary_csp.score, itinerary_ga.score),
                "Cost (USD)": (itinerary_csp.total_cost_usd, itinerary_ga.total_cost_usd),
                "Travel time (min)": (itinerary_csp.total_travel_minutes, itinerary_ga.total_travel_minutes),
                "Runtime (s)": (itinerary_csp.runtime_seconds, itinerary_ga.runtime_seconds),
            }

            with col_a:
                st.markdown("### CSP + A*")
                for label, (csp_val, _) in metrics.items():
                    st.metric(label, f"{csp_val:.2f}")

            with col_b:
                st.markdown("### GA")
                for label, (csp_val, ga_val) in metrics.items():
                    delta = ga_val - csp_val
                    st.metric(label, f"{ga_val:.2f}", delta=f"{delta:+.2f}")

            # Bar chart comparison
            fig = go.Figure()
            labels = list(metrics.keys())
            csp_vals = [metrics[l][0] for l in labels]
            ga_vals = [metrics[l][1] for l in labels]

            fig.add_trace(go.Bar(name="CSP + A*", x=labels, y=csp_vals, marker_color="#457B9D"))
            fig.add_trace(go.Bar(name="GA", x=labels, y=ga_vals, marker_color="#E63946"))
            fig.update_layout(barmode="group", height=400, title="Solver Comparison")
            st.plotly_chart(fig, use_container_width=True)

        tab_idx += 1

    # Export tab
    with tabs[tab_idx]:
        st.subheader("Export Itinerary")
        active = itinerary_csp or itinerary_ga

        if active:
            col1, col2 = st.columns(2)
            with col1:
                json_str = _itinerary_to_json(active)
                st.download_button(
                    "Download JSON",
                    data=json_str,
                    file_name=f"itinerary_{active.destination.lower()}.json",
                    mime="application/json",
                )
            with col2:
                pdf_bytes = _build_pdf(active, prefs)
                if pdf_bytes:
                    st.download_button(
                        "Download PDF",
                        data=pdf_bytes,
                        file_name=f"itinerary_{active.destination.lower()}.pdf",
                        mime="application/pdf",
                    )
                else:
                    st.info("Install reportlab to enable PDF export: `pip install reportlab`")

else:
    # Welcome screen
    st.markdown("""
    ## Welcome to the AI Travel Planner

    This tool generates personalised, optimised travel itineraries using three classical AI techniques:

    | Algorithm | Role |
    |---|---|
    | **K-Means Clustering** | Groups attractions geographically by day |
    | **CSP + Backtracking (MRV, LCV, AC-3)** | Enforces hard constraints (budget, time, opening hours) |
    | **A\\* Search** | Finds the optimal visit order within each day |
    | **Genetic Algorithm** | Comparison baseline solver |

    Configure your trip in the sidebar and click **Generate Itinerary**.
    """)

    st.info("Available cities: " + ", ".join(available_cities()))
