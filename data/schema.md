# POI Data Schema

Each city JSON file is a **JSON array** of POI objects. Every object must conform to the schema below. The `data_loader.py` module validates all fields on load and raises `ValueError` for any violation.

## Required Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | string | Unique within city, prefix `{city_code}_NNN` | Stable identifier |
| `name` | string | Non-empty | Display name |
| `city` | string | Non-empty | City name |
| `lat` | float | [-90, 90] | WGS-84 latitude |
| `lon` | float | [-180, 180] | WGS-84 longitude |
| `category` | string | See allowed list | Broad category |
| `tags` | string[] | Can be empty | Descriptive keywords |
| `avg_cost_usd` | float | ≥ 0 | Typical entry cost in USD |
| `avg_duration_minutes` | int | > 0 | Typical visit time |
| `opening_hours` | object | Keys from `DAY_ABBREVIATIONS` | Operating hours per day |
| `rating` | float | [0.0, 5.0] | Visitor rating |
| `indoor` | bool | — | Whether the attraction is indoors |
| `family_friendly` | bool | — | Suitable for families with children |

## Opening Hours Format

```json
"opening_hours": {
  "mon": [9, 22],
  "tue": [9, 22],
  "wed": [9, 22],
  "thu": [9, 22],
  "fri": [9, 22],
  "sat": [9, 22],
  "sun": [9, 22]
}
```

- Keys must be in `["mon", "tue", "wed", "thu", "fri", "sat", "sun"]`.
- Values are `[open_hour, close_hour]` in 24-hour format (integers).
- **Omitting a day means the venue is closed that day.**

## Allowed Categories

```
landmark | museum | food | nature | shopping | religious | nightlife | adventure | beach | cultural
```

## Dataset Requirements

- Minimum 40 POIs per city; target 60.
- Balanced distribution across categories — no category should exceed 30% of the total.
- All coordinates must be real, publicly verifiable lat/lon (from Wikipedia, OpenStreetMap, or official sources). Fabricated coordinates break clustering and routing.

## Example

```json
{
  "id": "par_001",
  "name": "Eiffel Tower",
  "city": "Paris",
  "lat": 48.8584,
  "lon": 2.2945,
  "category": "landmark",
  "tags": ["iconic", "romantic", "viewpoint"],
  "avg_cost_usd": 30,
  "avg_duration_minutes": 120,
  "opening_hours": {
    "mon": [9, 22], "tue": [9, 22], "wed": [9, 22],
    "thu": [9, 22], "fri": [9, 22], "sat": [9, 22], "sun": [9, 22]
  },
  "rating": 4.6,
  "indoor": false,
  "family_friendly": true
}
```
