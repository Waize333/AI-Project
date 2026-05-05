"""
Global constants for the AI Travel Planner.
All magic numbers live here with explanatory comments.
"""

RANDOM_SEED = 42

# --- Travel speed assumptions ---
WALKING_SPEED_KMH = 4.0    # Average pedestrian walking speed
TRANSIT_SPEED_KMH = 25.0   # Average city transit (bus/metro) including stops

# --- Pace limits (hours of activity per day) ---
PACE_HOURS = {
    "relaxed": 6,
    "balanced": 8,
    "packed": 10,
}

# --- A* / routing ---
MAX_POIS_PER_DAY = 7  # State-space cap; keeps A* tractable (2^7 = 128 states)
HOTEL_CHECKIN_HOUR = 9  # Earliest departure from hotel each day

# --- Genetic Algorithm hyperparameters ---
GA_POPULATION_SIZE = 100
GA_NUM_GENERATIONS = 200
GA_CROSSOVER_RATE = 0.8
GA_MUTATION_RATE = 0.15
GA_TOURNAMENT_SIZE = 3

# --- Scoring regression defaults (overridden after training) ---
ALPHA_DEFAULT = 0.10   # travel-time penalty weight
BETA_DEFAULT = 0.05    # budget-slack penalty weight
GAMMA_DEFAULT = 0.20   # pace-violation penalty weight

# --- Data validation ---
ALLOWED_CATEGORIES = [
    "landmark", "museum", "food", "nature", "shopping",
    "religious", "nightlife", "adventure", "beach", "cultural",
]

ALLOWED_TRAVELER_TYPES = ["solo", "couple", "family", "friends"]
ALLOWED_PACE_VALUES = ["relaxed", "balanced", "packed"]
DAY_ABBREVIATIONS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# --- Paths ---
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "cities"
