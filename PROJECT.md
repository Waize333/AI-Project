AI Travel Planner — Project Reference

> University AI Course Project
> Classical AI algorithms: K-Means Clustering · CSP + Backtracking · A* Search · Genetic Algorithm

---

## What This Project Does

The SFY AI Travel Planner takes a user's travel preferences and generates a day-by-day itinerary for a chosen city. Given inputs like destination, number of days, budget, traveler type, and interest weights, the system produces an ordered schedule of Points of Interest (POIs) that:

- Stays within the total budget
- Respects each POI's opening hours
- Minimises daily travel time
- Maximises alignment with the user's interests

The system runs two independent solvers (CSP+A* and Genetic Algorithm) and compares their results. The CSP+A* pipeline guarantees constraint satisfaction and route optimality; the GA is a stochastic comparison baseline.

**Cities available:** Paris (50 POIs), Istanbul (40), Tokyo (40), Dubai (40), Karachi (40)

---

## Architecture Overview

```
User Preferences
      │
      ▼
K-Means Clustering   ─── groups POIs into K geographic day-clusters
      │
      ▼
CSP Solver           ─── assigns POIs to days, enforcing all constraints
  (AC-3, MRV, LCV, forward checking, backtracking)
      │
      ▼
A* Router            ─── orders POIs within each day (min travel time)
  (MST admissible heuristic)
      │
      ▼
Scorer               ─── evaluates itinerary quality (linear regression)
      │
      ▼
Itinerary (+ GA comparison baseline)
```

---

## File-by-File Reference

### Backend — Python Core (`src/`)

---

#### `src/config.py`

Global constants. All magic numbers live here.


| Constant             | Value                                | Purpose                                                   |
| -------------------- | ------------------------------------ | --------------------------------------------------------- |
| `RANDOM_SEED`        | 42                                   | Fixed seed for reproducibility across K-Means and GA      |
| `PACE_HOURS`         | `{relaxed:6, balanced:8, packed:10}` | Max activity hours per day by pace type                   |
| `MAX_POIS_PER_DAY`   | 7                                    | Hard cap on POIs per day (A* state space stays tractable) |
| `GA_POPULATION`      | 100                                  | Number of GA chromosomes per generation                   |
| `GA_GENERATIONS`     | 200                                  | Number of evolution steps                                 |
| `GA_CROSSOVER_RATE`  | 0.8                                  | Probability of OX crossover per pair                      |
| `GA_MUTATION_RATE`   | 0.15                                 | Probability of mutation per chromosome                    |
| `GA_TOURNAMENT_SIZE` | 3                                    | Tournament selection pool size                            |
| `CATEGORIES`         | 10 category strings                  | Valid POI categories for preference weighting             |

---

#### `src/utils.py`

Pure utility functions with no side effects.

**`haversine(lat1, lon1, lat2, lon2) → float`**
Computes the great-circle distance in kilometres between two geographic coordinates using the Haversine formula. Used by the A* router and K-Means pre-filtering.

**`travel_time_minutes(lat1, lon1, lat2, lon2, speed_kmh=5.0) → float`**
Converts haversine distance to travel minutes at walking speed. The default 5 km/h is conservative — accounts for navigation, crossings, and urban density. Used as the edge weight in A*.

**`day_of_week(date_str: str, day_offset: int) → str`**
Given a start date string ("2025-06-01") and a day offset, returns the weekday name ("mon", "tue", …). Used by the CSP to check opening hours.

---

#### `src/preferences.py`

Data model for user travel preferences.

**`TravelerType`** — Enum: `solo | couple | family | friends`
Affects family-friendliness filtering: if `family`, only `family_friendly=true` POIs pass the initial filter.

**`PaceType`** — Enum: `relaxed | balanced | packed`
Controls the daily hour budget (6 / 8 / 10 hours) used by the CSP time constraint.

**`UserPreferences`** — DataclassHolds all planner inputs after validation:

- `destination: str`
- `num_days: int` (1–14)
- `budget_usd: float`
- `traveler_type: TravelerType`
- `interest_weights: Dict[str, float]` — per-category weights in [0, 1]
- `pace: PaceType`
- `must_include: List[str]` — POI IDs that must appear in the itinerary
- `must_avoid_categories: List[str]` — categories to exclude entirely
- `start_date: str` — ISO date string, determines opening-hour day offsets

---

#### `src/data_loader.py`

Loads and validates POI datasets from `data/cities/*.json`.

**`POI`** — Frozen dataclass matching the schema in `data/schema.md`:

```python
@dataclass(frozen=True)
class POI:
    id: str
    name: str
    city: str
    lat: float
    lon: float
    category: str          # one of 10 CATEGORIES
    tags: List[str]
    avg_cost_usd: float
    avg_duration_minutes: float
    opening_hours: Dict[str, List[int]]   # {"mon": [9, 22], ...}
    rating: float          # 1.0 – 5.0
    indoor: bool
    family_friendly: bool
```

**`load_city(city: str) → List[POI]`**
Reads `data/cities/{city}.json`, validates each record against the schema, and returns a list of POI objects. Raises `ValueError` with a clear message if any field is missing or invalid.

**`available_cities() → List[str]`**
Scans `data/cities/` and returns lowercase filenames without extension.

---

#### `src/clustering.py`

K-Means geographic day partitioning.

**Algorithm:** `sklearn.cluster.KMeans` on the (lat, lon) feature matrix of filtered POIs.
**Why K-Means:** The number of clusters K is known in advance (= `num_days`). DBSCAN would produce variable K requiring post-hoc merging. K-Means is O(n·K·i) and fast enough for ≤50 POIs.
**Why Euclidean on lat/lon:** At intra-city scale (<30 km), Euclidean distortion is <0.5% vs haversine — negligible for clustering purposes.

**`cluster_pois_by_day(pois, prefs) → Dict[int, List[POI]]`**

1. Filters POIs by interest weights and family-friendliness.
2. Re-adds any `must_include` POIs that were filtered out.
3. Runs KMeans with `n_clusters=num_days, random_state=RANDOM_SEED`.
4. Handles empty clusters by moving the nearest POI from the largest cluster.
5. Returns a dict mapping day index → list of candidate POIs.

**`get_city_center(pois) → Tuple[float, float]`**
Returns the geographic mean of all POI coordinates, used as the hotel/start location for A* routing.

---

#### `src/csp_solver.py`

The core classical AI engine. A custom CSP solver — no library calls.

##### CSP Formulation


| Element         | Definition                                                               |
| --------------- | ------------------------------------------------------------------------ |
| **Variables**   | One variable Xᵢ per POI candidate                                       |
| **Domain**      | D(Xᵢ) = {1, 2, …, num_days} ∪ {None} (None = exclude this POI)        |
| **Constraints** | Five constraint types (see below)                                        |
| **Solution**    | Assignment of each variable to a day or None, satisfying all constraints |

##### Constraints

1. **Budget** (`c_budget`): Σ cost(POIs assigned) ≤ total_budget_usd
2. **Time** (`c_time`): For each day d, Σ duration(POIs on day d) + travel_time(day d) ≤ pace_hours[d]
3. **Opening hours** (`c_hours`): For each POI on day d, the POI must be open on the corresponding weekday
4. **Must-include** (`c_must`): All `must_include` POI IDs must be assigned a day (not None)
5. **Uniqueness** (`c_unique`): Each POI appears on at most one day

##### Search Techniques

**AC-3 (Arc-Consistency 3)** — `_ac3()`
Pre-processing step before search. Initialises a queue of all constraint arcs (Xᵢ, Xⱼ). For each arc, removes values from D(Xᵢ) that have no support in D(Xⱼ). Continues until no domains change. Returns `False` only if a must-include POI's domain becomes empty — optional POIs are silently excluded.

*Complexity:* O(d²·a) where d = domain size, a = number of arcs.

**MRV (Minimum Remaining Values)** — `_select_mrv()`
Variable ordering heuristic. At each step, selects the unassigned POI whose domain has the fewest remaining feasible values. Breaks ties by highest interest weight. Intuition: tackle the most-constrained POI first to detect infeasibility early.

**LCV (Least Constraining Value)** — `_order_days_lcv()`
Value ordering heuristic. For the selected variable, orders its domain values (days) by how many assignments remain feasible for other unassigned POIs. Prefers the value that eliminates the fewest options for neighbours.

**Forward Checking** — `_forward_check()`
After each assignment, immediately checks all unassigned POIs and prunes any domain values made infeasible by the new assignment. Returns `False` if any must-include POI has its domain emptied (triggering backtracking).

**Backtracking**
Standard depth-first search with the above heuristics. If forward checking fails, undoes the assignment and tries the next value. Returns an `InfeasibilityReport` with actionable suggestions (suggested budget, suggested extra days) if no solution exists.

**Key Design Choice:** Optional POIs are excluded when no feasible day exists; must-include POIs trigger infeasibility. This avoids the solver getting stuck trying to schedule a closed museum on Sunday.

---

#### `src/astar_router.py`

A* search for optimal intra-day POI visit order.

##### Problem Formulation

- **State:** `(current_location: Tuple[float,float], unvisited: FrozenSet[str])`
- **Start:** `(hotel_location, frozenset of all POI IDs assigned to this day)`
- **Goal:** All POIs visited, return to hotel
- **Cost:** Total travel time in minutes (haversine + walking speed)
- **Action:** Move to any unvisited POI (or hotel if all visited)

This is a variant of the Travelling Salesman Problem with fixed start/end. With ≤7 POIs per day (`MAX_POIS_PER_DAY`), the state space is at most 7! = 5040 orderings — tractable for A*.

##### MST Heuristic

**`_mst_cost(unvisited, current, hotel) → float`**
Computes the Minimum Spanning Tree cost over `{current} ∪ unvisited ∪ {hotel}` using Prim's algorithm with travel time as edge weight.

**Admissibility proof:**
Any path visiting all unvisited POIs and returning to hotel forms a Hamiltonian path. Every Hamiltonian path is a spanning tree (or superset of one). Therefore MST cost ≤ optimal path cost. The heuristic never overestimates. ∎

*Complexity:* O(n²) with Prim's on a complete graph. Acceptable for n ≤ 7.

**`route_day(pois, hotel_lat, hotel_lon) → List[POI]`**
Runs A* search, returns POIs in optimal visit order.

**`compute_day_travel_time(ordered_pois, hotel_lat, hotel_lon) → float`**
Computes total travel minutes along the routed path, including hotel→first and last→hotel legs.

---

#### `src/ga_solver.py`

Genetic Algorithm — comparison baseline only. Demonstrates where stochastic search falls short on constraint-heavy instances.

##### Chromosome Encoding

A chromosome is a permutation of all candidate POI indices `[0, 1, …, n-1]`. The permutation is split into `num_days` segments at fixed split points; each segment = POIs assigned to that day.

##### Fitness Function

```
fitness = score(itinerary)
        − w_budget  × max(0, total_cost − budget)
        − w_time    × Σ max(0, day_time − pace_hours)
        − w_must    × count(missing must-include POIs)
        − w_hours   × count(POIs open-hour violations)
```

Violations are penalised but not forbidden — the GA can produce infeasible solutions.

##### Operators

**Selection:** Tournament (size = `GA_TOURNAMENT_SIZE = 3`). Draw 3 random chromosomes, return the fittest.

**Crossover:** Order Crossover (OX). Copies a random sub-sequence from parent A into the child, then fills remaining positions in parent B's order. OX preserves relative ordering — critical for permutation problems to avoid invalid chromosomes.

**Mutation:** Two operators applied randomly:

1. *Swap mutation:* Swap two random POI positions.
2. *Boundary mutation:* Shift a day split-point by ±1, reallocating one POI between adjacent days. Explores different day groupings.

**Elitism:** The single best chromosome is copied unchanged into the next generation. Prevents regression.

**Parameters:** Population 100, Generations 200, Crossover rate 0.8, Mutation rate 0.15, Tournament 3.

---

#### `src/scorer.py`

Itinerary quality scoring with linear regression.

**`score_itinerary(itinerary, prefs) → float`**

```
score = Σ_poi [ rating(poi) × preference_match(poi, prefs) ]
      − α × total_travel_minutes
      − β × budget_slack_penalty
      − γ × pace_violation_penalty
```

**`preference_match(poi, prefs)`** — Cosine-style weighted similarity:
`interest_weights[poi.category]` (0–1), boosted by tag overlap with traveler type keywords.

**Coefficients (α, β, γ):** Trained via ordinary least squares on ~15 hand-rated sample itineraries. Not arbitrary — data-driven regression that correlates each component with human quality judgements.

**`Itinerary`** and **`DayRoute`** dataclasses are also defined here, representing the final structured output.

---

#### `src/planner.py`

Orchestrator — calls the other modules in sequence.

**`plan_csp_astar(prefs) → Itinerary | InfeasibilityReport`**Full CSP+A* pipeline:

1. Load city POIs (`data_loader`)
2. Cluster by day (`clustering`)
3. Run CSP solver to assign POIs to days (`csp_solver`)
4. Route each day with A* (`astar_router`)
5. Score result (`scorer`)

**`plan_ga(prefs) → Itinerary`**
GA-only pipeline: load POIs → cluster → GA solve → score.

**`plan_both(prefs) → Tuple[Itinerary | None, Itinerary]`**
Runs both pipelines and returns both results for comparison.

---

#### `api.py`

FastAPI REST server exposing the planner to the frontend.


| Method | Endpoint              | Description                     |
| ------ | --------------------- | ------------------------------- |
| GET    | `/health`             | Liveness check                  |
| GET    | `/cities`             | List of available city names    |
| GET    | `/cities/{city}/pois` | All POIs for a city             |
| POST   | `/plan`               | Run solver(s), return itinerary |

**POST /plan request body:**

```json
{
  "destination": "paris",
  "num_days": 3,
  "budget_usd": 500,
  "traveler_type": "solo",
  "interest_weights": { "museum": 0.9, "landmark": 0.7 },
  "pace": "balanced",
  "must_include": [],
  "must_avoid_categories": ["nightlife"],
  "start_date": "2025-06-01",
  "solver": "both"
}
```

**POST /plan response:**

```json
{
  "feasible": true,
  "infeasibility_report": null,
  "csp_itinerary": { ... },
  "ga_itinerary": { ... }
}
```

---

### Frontend — Next.js 14 (`frontend/`)

---

#### `frontend/app/layout.tsx`

Root layout. Provides the dark glass nav bar, sticky header with algorithm tags, and footer. No state — purely structural.

#### `frontend/app/page.tsx`

Main client page. Manages all application state:

- `loading: boolean` — shows `AlgorithmVisualizer` while API call is in-flight
- `response: PlanResponse | null` — raw API result
- `error: string | null` — API error message
- `activeTab: "csp" | "ga" | "compare"` — which result panel to show

Renders: Hero → Algorithm Pipeline cards → TravelForm (left) / Results (right).

#### `frontend/app/globals.css`

Global dark theme variables and CSS animations:

- `--bg-base`, `--bg-surface`, `--bg-card` colour tokens
- Destination card gradients (`.dest-paris`, `.dest-istanbul`, etc.)
- Category colour utilities (`.cat-landmark`, `.cat-bg-museum`, etc.)
- Keyframe animations: `float`, `fade-up`, `bar-grow`, `glow-pulse`, `spin-slow`
- Glass morphism utilities: `.glass`, `.glass-amber`, `.glass-teal`
- Gradient text utilities: `.gradient-text`, `.gradient-text-amber`
- Custom dark scrollbar and range input thumb styling

---

#### `frontend/components/TravelForm.tsx`

User preference input form. Key design choices:

- **Destination selector:** City cards with per-city gradient backgrounds and landmark icons rather than a plain dropdown. Cities come from the `/cities` API endpoint with a fallback list.
- **Duration stepper:** ± buttons instead of a text input for better UX.
- **Traveler type / pace:** Icon pill buttons with amber/teal active states.
- **Interest weights:** Per-category sliders with emoji icons, avoid toggle per category.
- **Solver selector:** Three options — "CSP+A*", "GA only", "Both (compare)".

#### `frontend/components/AlgorithmVisualizer.tsx`

The centrepiece loading animation. Cycles through 4 stages (K-Means → CSP → A* → GA), each showing:

- An animated SVG visualising the algorithm operating on example data
- Algorithm name, tag line, and one-paragraph explanation
- The key formula/notation
- A progress bar within the stage
- A pulsing live-indicator status bar

Each SVG uses React `useState` + `useEffect`/`setInterval` at 55ms intervals (≈18fps) to advance a `frame` counter. SVG elements transition their `fill`, `stroke`, and `opacity` to show algorithmic progression — dot clustering, arc pruning, path exploration, fitness bar growth.

#### `frontend/components/ItineraryView.tsx`

Displays one solver's itinerary. Shows:

- Destination title + solver tag + runtime
- 4 stat cards: Score, Total Cost, Travel Time, POIs Visited
- "Day Plans" tab → list of `DayCard`s
- "Map" tab → `MapView` (Leaflet, SSR-disabled)

Accepts `accentColor` prop so CSP (teal) and GA (green) renders are visually distinct.

#### `frontend/components/DayCard.tsx`

Collapsible card for one day's route. Closed state shows day badge, POI count, cost, and an emoji preview strip. Open state renders a timeline: vertical colour line with numbered nodes, each connected to a POI info card showing category icon, rating, duration, and cost. Category colours pulled from `CAT_COLORS` map.

#### `frontend/components/ComparisonView.tsx`

Side-by-side metric comparison with horizontal bar charts. For each metric (Score, POIs, Cost, Travel, Runtime), renders two proportional bars — one teal (CSP), one green (GA) — with the winner highlighted. Includes a detailed explainer note on why CSP+A* enforces constraints that GA cannot guarantee.

#### `frontend/components/MapView.tsx`

Leaflet interactive map (loaded client-side only via `next/dynamic`). Renders:

- Colour-coded polylines per day (using `DAY_COLORS` from `lib/types`)
- Numbered circle markers at each POI
- Popup with POI name and category on click

#### `frontend/lib/types.ts`

All TypeScript interfaces shared between components: `POI`, `DayRoute`, `Itinerary`, `PlanRequest`, `PlanResponse`, `InfeasibilityReport`. Also exports `DAY_COLORS` (14-colour cycle) and `CATEGORIES` (10 strings).

#### `frontend/lib/api.ts`

Axios client functions:

- `fetchCities()` — GET `/cities`
- `fetchPois(city)` — GET `/cities/{city}/pois`
- `planTrip(req)` — POST `/plan` with 120s timeout (long solver runs)

---

### Data (`data/`)

#### `data/cities/*.json`

Five city POI datasets with real coordinates from OpenStreetMap:


| City     | POIs | Notable included                                           |
| -------- | ---- | ---------------------------------------------------------- |
| Paris    | 50   | Eiffel Tower, Louvre, Sacré-Cœur, Notre-Dame, Versailles |
| Istanbul | 40   | Hagia Sophia, Grand Bazaar, Topkapi Palace, Bosphorus      |
| Tokyo    | 40   | Senso-ji, Shibuya, Shinjuku, Tsukiji, Akihabara            |
| Dubai    | 40   | Burj Khalifa, Dubai Mall, Palm Jumeirah, Gold Souk         |
| Karachi  | 40   | Clifton Beach, Mohatta Palace, Frere Hall, Saddar          |

#### `data/schema.md`

POI JSON schema documentation — required fields, types, constraints, examples.

---

### Experiments (`experiments/`)

#### `experiments/benchmark.py`

Runs 10 pre-defined scenarios (city × constraint-tightness combinations) through both solvers, measures runtime and score, counts constraint violations, and outputs:

- `experiments/results/benchmark_raw.json`
- `experiments/results/benchmark_table.md`
- `experiments/results/benchmark_plots.png`

#### `experiments/results/benchmark_table.md`

10-scenario summary table:


| Solver   | Avg Score | Avg Runtime | Constraint Violations |
| -------- | --------- | ----------- | --------------------- |
| CSP + A* | 41.47     | 0.012s      | **0**                 |
| GA       | 58.54     | 0.467s      | **6**                 |

*CSP never violates constraints. GA scores higher on easy instances (more POIs explored) but fails on tight-budget/short-trip scenarios.*

---

### Tests (`tests/`)

Run with: `pytest tests/ -v`


| File                 | What it tests                                                                                |
| -------------------- | -------------------------------------------------------------------------------------------- |
| `test_clustering.py` | K-Means produces exactly K non-empty clusters; must-include POIs are preserved               |
| `test_csp.py`        | CSP finds feasible solutions; detects infeasibility correctly; AC-3 prunes domains           |
| `test_astar.py`      | A* returns all POIs; MST heuristic is never larger than true path cost (admissibility check) |
| `test_ga.py`         | GA terminates; OX crossover produces valid permutations; fitness improves over generations   |

---

## Running the Project

**Backend:**

```bash
cd AI-Project
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

**Frontend:**

```bash
cd AI-Project/frontend
npm install
npm run dev   # http://localhost:3000
```

**Tests:**

```bash
pytest tests/ -v
```

**Benchmark:**

```bash
python -m experiments.benchmark
```

**Adding a new city:**

1. Create `data/cities/{city}.json` following `data/schema.md`
2. Minimum 40 POIs with real lat/lon
3. Balance categories — no single category > 30%
4. Validate: `python -c "from src.data_loader import load_city; load_city('{city}')"`

---

## Design Philosophy

This is deliberately a **classical AI** project — no neural networks, no embeddings, no LLMs.

The key insight: itinerary planning is a *discrete constrained optimisation problem*, not a pattern-recognition task. Classical search algorithms are ideal because:

1. **Hard constraint enforcement** — CSP can algebraically prove whether a constraint is satisfiable, not just penalise violations.
2. **Provable optimality** — A* with an admissible heuristic guarantees the globally optimal route; no approximation.
3. **Transparent infeasibility** — When no valid itinerary exists, the CSP reports exactly which constraint failed and by how much, enabling actionable suggestions ("increase budget by $120 or add one more day").
4. **No training data** — Classical AI needs no labelled itineraries, unlike ML approaches.
5. **Interpretable** — Every decision traces back to a constraint check or heuristic evaluation. No black-box behaviour.
