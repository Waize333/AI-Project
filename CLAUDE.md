# AI Travel Planner — Claude Code Instructions

## Architecture (Do Not Deviate)

This is a university AI course project. The architecture is fixed:

1. **K-Means Clustering** → geographic day partitioning (`src/clustering.py`)
2. **CSP + Backtracking** → constraint enforcement (`src/csp_solver.py`)
3. **A\*** → intra-day routing (`src/astar_router.py`)
4. **Genetic Algorithm** → comparison baseline (`src/ga_solver.py`)

**Never add neural networks or deep learning.** The entire point is classical AI.

## Development Rules

- All POI data lives in `data/cities/*.json`. Never hardcode POI data in Python.
- The UI (`app.py`) never calls solvers directly — it uses `src/planner.py`.
- Tests must pass before any PR. Run `pytest tests/ -v`.
- All random seeds must be fixed (see `src/config.py`: `RANDOM_SEED = 42`).
- Type hints on every public function. Docstrings on every public function.
- No magic numbers outside `src/config.py`.

## Running

```bash
pip install -r requirements.txt
streamlit run app.py
pytest tests/ -v
python -m experiments.benchmark
```

## Adding a New City

1. Create `data/cities/{cityname}.json` following the schema in `data/schema.md`.
2. Minimum 40 POIs with **real lat/lon** from OpenStreetMap or Wikipedia.
3. Balance categories — no single category > 30% of total.
4. Verify with: `python -c "from src.data_loader import load_city; load_city('{cityname}')"`.

## CSP Solver Notes

The CSP implementation uses:
- **AC-3** in `_ac3()` for pre-processing domain pruning
- **MRV** in `_select_mrv()` for variable ordering  
- **LCV** in `_order_days_lcv()` for value ordering  
- **Forward checking** in `_forward_check()` after each assignment

Do not replace these with library calls — they must be custom implementations.

## A* Heuristic

The MST heuristic in `_mst_cost()` is admissible. Proof is documented in `src/astar_router.py` and `report/report.md` Section 5.2. Do not change the heuristic without verifying admissibility.
