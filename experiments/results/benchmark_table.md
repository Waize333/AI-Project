# Benchmark Results: CSP+A* vs Genetic Algorithm

10 predefined scenarios, each run once. Hardware: local CPU.

| # | Scenario | CSP Score | GA Score | CSP Time (s) | GA Time (s) | CSP POIs | GA POIs | CSP Violations | GA Violations |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Paris 3-day Budget | 51.557 | 65.782 | 0.02 | 0.499 | 14 | 21 | 0 | 0 |
| 2 | Paris 5-day Luxury | 86.628 | 92.538 | 0.038 | 0.695 | 33 | 35 | 0 | 0 |
| 3 | Istanbul 3-day Culture | 50.825 | 69.21 | 0.009 | 0.457 | 16 | 21 | 0 | 0 |
| 4 | Istanbul 2-day Relaxed | 22.378 | 36.053 | 0.004 | 0.362 | 8 | 14 | 0 | 0 |
| 5 | Tokyo 4-day Family | 47.075 | 68.965 | 0.009 | 0.558 | 17 | 28 | 0 | 3 |
| 6 | Tokyo 3-day Otaku | 46.133 | 68.954 | 0.014 | 0.457 | 15 | 21 | 0 | 0 |
| 7 | Dubai 2-day Adventure | 20.463 | 39.005 | 0.004 | 0.364 | 7 | 14 | 0 | 0 |
| 8 | Dubai 3-day Luxury | 30.273 | 54.699 | 0.004 | 0.46 | 10 | 21 | 0 | 1 |
| 9 | Karachi 2-day Local | 16.985 | 37.108 | 0.004 | 0.365 | 8 | 14 | 0 | 2 |
| 10 | Karachi 3-day History | 42.378 | 53.076 | 0.015 | 0.458 | 18 | 21 | 0 | 0 |

## Summary

- CSP+A* average score: 41.469
- GA average score:      58.539
- CSP+A* average runtime: 0.012s
- GA average runtime:     0.467s
- CSP+A* total violations: 0
- GA total violations:     6