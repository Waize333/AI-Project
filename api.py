"""
FastAPI backend for the AI Travel Planner.

Endpoints:
  GET  /health          — liveness check
  GET  /cities          — list available city names
  POST /plan            — run CSP+A* and GA solvers, return results
"""

from __future__ import annotations

import os
import traceback
from datetime import date
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.data_loader import available_cities, load_city, POI
from src.planner import plan_both, plan_csp_astar, plan_ga
from src.preferences import UserPreferences
from src.scorer import DayRoute, Itinerary

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Travel Planner API", version="1.0.0")

_origins_env = os.getenv("ALLOWED_ORIGINS", "")
_allowed_origins: list[str] = (
    [o.strip() for o in _origins_env.split(",") if o.strip()]
    if _origins_env
    else ["http://localhost:3000", "http://127.0.0.1:3000"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class PlanRequest(BaseModel):
    destination: str
    num_days: int = Field(ge=1, le=14)
    budget_usd: float = Field(gt=0)
    traveler_type: str = "solo"
    interest_weights: dict[str, float] = Field(default_factory=dict)
    pace: str = "balanced"
    must_include: list[str] = Field(default_factory=list)
    must_avoid_categories: list[str] = Field(default_factory=list)
    start_date: str = "2025-06-01"
    hotel_lat: Optional[float] = None
    hotel_lon: Optional[float] = None
    solver: str = "both"  # "csp", "ga", or "both"


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _poi_to_dict(poi: POI) -> dict[str, Any]:
    return {
        "id": poi.id,
        "name": poi.name,
        "city": poi.city,
        "lat": poi.lat,
        "lon": poi.lon,
        "category": poi.category,
        "tags": poi.tags,
        "avg_cost_usd": poi.avg_cost_usd,
        "avg_duration_minutes": poi.avg_duration_minutes,
        "rating": poi.rating,
        "indoor": poi.indoor,
        "family_friendly": poi.family_friendly,
    }


def _day_route_to_dict(dr: DayRoute) -> dict[str, Any]:
    return {
        "day": dr.day,
        "pois": [_poi_to_dict(p) for p in dr.pois],
        "total_cost_usd": dr.total_cost_usd,
        "total_activity_minutes": dr.total_activity_minutes,
        "total_travel_minutes": dr.total_travel_minutes,
    }


def _itinerary_to_dict(it: Itinerary) -> dict[str, Any]:
    return {
        "destination": it.destination,
        "days": {str(k): _day_route_to_dict(v) for k, v in it.days.items()},
        "total_cost_usd": it.total_cost_usd,
        "total_travel_minutes": it.total_travel_minutes,
        "score": it.score,
        "solver": it.solver,
        "runtime_seconds": getattr(it, "runtime_seconds", None),
    }


def _build_preferences(req: PlanRequest) -> UserPreferences:
    hotel = None
    if req.hotel_lat is not None and req.hotel_lon is not None:
        hotel = (req.hotel_lat, req.hotel_lon)

    prefs = UserPreferences(
        destination=req.destination,
        num_days=req.num_days,
        budget_usd=req.budget_usd,
        traveler_type=req.traveler_type,  # type: ignore[arg-type]
        interest_weights=req.interest_weights,
        pace=req.pace,  # type: ignore[arg-type]
        must_include=req.must_include,
        must_avoid_categories=req.must_avoid_categories,
        start_date=date.fromisoformat(req.start_date),
        hotel_location=hotel,
    )
    prefs.validate()
    return prefs


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/cities")
def cities() -> dict[str, list[str]]:
    return {"cities": available_cities()}


@app.get("/cities/{city_name}/pois")
def get_pois(city_name: str) -> dict[str, Any]:
    try:
        pois = load_city(city_name)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"city": city_name, "pois": [_poi_to_dict(p) for p in pois]}


@app.post("/plan")
def plan(req: PlanRequest) -> dict[str, Any]:
    try:
        prefs = _build_preferences(req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        if req.solver == "csp":
            itinerary, report = plan_csp_astar(prefs)
            if itinerary is None:
                return {
                    "feasible": False,
                    "infeasibility_report": {
                        "constraint_violated": report.constraint_violated,
                        "message": report.message,
                        "suggestion": report.suggestion,
                        "suggested_budget": report.suggested_budget,
                        "suggested_days": report.suggested_days,
                    },
                    "csp_itinerary": None,
                    "ga_itinerary": None,
                }
            return {
                "feasible": True,
                "infeasibility_report": None,
                "csp_itinerary": _itinerary_to_dict(itinerary),
                "ga_itinerary": None,
            }

        elif req.solver == "ga":
            itinerary, runtime = plan_ga(prefs)
            return {
                "feasible": True,
                "infeasibility_report": None,
                "csp_itinerary": None,
                "ga_itinerary": _itinerary_to_dict(itinerary),
            }

        else:  # "both"
            result = plan_both(prefs)
            csp_it = result.get("csp")
            ga_it = result.get("ga")
            report = result.get("csp_error")

            return {
                "feasible": result.get("feasible", csp_it is not None),
                "infeasibility_report": (
                    {
                        "constraint_violated": report.constraint_violated,
                        "message": report.message,
                        "suggestion": report.suggestion,
                        "suggested_budget": report.suggested_budget,
                        "suggested_days": report.suggested_days,
                    }
                    if report else None
                ),
                "csp_itinerary": _itinerary_to_dict(csp_it) if csp_it else None,
                "ga_itinerary": _itinerary_to_dict(ga_it) if ga_it else None,
            }

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Planning failed: {exc}")