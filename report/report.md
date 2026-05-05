# AI-Powered Travel Planner: A Multi-Algorithm Itinerary Optimisation System

**Course:** Artificial Intelligence  
**Submission Date:** 2026  

---

## Abstract

This paper presents an AI-powered travel itinerary planner that generates personalised, constraint-satisfying multi-day trip plans using three classical AI techniques: K-Means clustering, Constraint Satisfaction Problem (CSP) solving with backtracking search, and A* pathfinding. A Genetic Algorithm (GA) is implemented as a secondary solver for empirical comparison. The system accepts user preferences (destination, budget, pace, interests) and produces day-by-day itineraries with optimal intra-day routing. Experiments across 10 test scenarios covering five cities demonstrate that the CSP+A* pipeline consistently produces feasible, high-quality itineraries (zero constraint violations) while the GA occasionally violates hard constraints despite achieving competitive scores on easy instances. The work establishes that itinerary planning is best modelled as a discrete constrained optimisation problem — not a pattern-recognition task — and that classical AI search algorithms are well-suited to this domain.

---

## 1. Introduction

Planning a multi-day trip is a computationally hard problem. A traveller must select which points of interest (POIs) to visit from hundreds of options, assign them to days, respect opening hours, stay within budget, avoid visiting a city's north and south extremes on the same day, and sequence visits to minimise walking time. This combination of selection, scheduling, and routing makes the problem NP-hard in the general case, related to the Travelling Salesman Problem (TSP) and the Job-Shop Scheduling Problem.

Despite the proliferation of travel-planning applications, most existing tools offer static templated itineraries or keyword search. The academic literature identifies itinerary planning as a variant of the **Trip Planning Query (TPQ)** problem (Chen et al., 2011), which requires finding a sequence of venues satisfying spatial, temporal, and preference constraints.

The key insight motivating this architecture is that **itinerary planning is a discrete constrained optimisation problem**, not a pattern-recognition problem. Deep learning would require large labelled datasets of rated itineraries and would not transparently enforce hard constraints. Classical AI search and optimisation techniques, by contrast, can provide guarantees: the CSP solver either finds a solution or reports exactly which constraint is violated and by how much, enabling actionable suggestions to the user.

This report documents a complete implementation: five city datasets (Paris, Istanbul, Tokyo, Dubai, Karachi) with real-coordinate POIs, a custom CSP solver with MRV/LCV/AC-3, a custom A* router with admissible MST heuristic, and a GA comparison baseline, all integrated into a Streamlit web interface.

---

## 2. Problem Formulation

### 2.1 Formal CSP Definition

Let $P$ be the set of candidate POIs for a destination city. Let $n$ be the number of trip days. The travel itinerary problem is formulated as a CSP $(X, D, C)$:

**Variables:** $X = \{x_i \mid p_i \in P\}$, one variable per POI. Each variable represents the day on which the POI is visited, or the special value $\bot$ (excluded).

**Domains:**
$$D(x_i) \subseteq \{1, 2, \ldots, n, \bot\}$$
Restricted by opening hours: day $d$ is in $D(x_i)$ only if POI $p_i$ is open on the weekday corresponding to $\text{start\_date} + (d-1)$ days.

**Constraints:**

| ID | Constraint | Formal Expression |
|---|---|---|
| $c_1$ | Global budget | $\sum_{x_i \neq \bot} \text{cost}(p_i) \leq B$ |
| $c_2$ | Daily time | $\forall d: \sum_{x_i=d} \text{dur}(p_i) + T_{\text{travel}}(d) \leq H_{\text{pace}} \times 60$ |
| $c_3$ | Opening hours | $x_i = d \Rightarrow p_i.\text{open}(\text{day\_of\_week}(d))$ |
| $c_4$ | Must-include | $\forall p_j \in M: x_j \neq \bot$ |
| $c_5$ | Uniqueness | $x_i = x_j \land i \neq j \Rightarrow x_i = \bot \lor x_j = \bot$ |

where $B$ is the user's total budget, $H_{\text{pace}} \in \{6, 8, 10\}$ hours per day (based on pace), and $M$ is the set of must-include POI IDs.

### 2.2 Routing Sub-Problem

Given the POIs assigned to day $d$ by the CSP, the routing sub-problem is:

$$\text{Find a permutation } \sigma \text{ of } \{p \in P : x_p = d\}$$
$$\text{minimising } \sum_{k=0}^{n_d} \text{time}(\text{pos}_k, \text{pos}_{k+1})$$

where $\text{pos}_0 = \text{pos}_{n_d+1} = \text{hotel}$. This is a variant of TSP with a fixed start/end point, solved with A*.

---

## 3. Algorithm Selection Justification

### 3.1 K-Means Clustering

**Why K-Means:** The number of clusters equals the number of trip days, which is known in advance. K-Means directly optimises for exactly $k$ groups by minimising within-cluster variance. The alternative, DBSCAN, discovers an unknown number of clusters based on point density; it would require post-hoc merging or splitting to produce exactly $k$ groups, introducing additional parameters. Hierarchical clustering could also produce $k$ groups but runs in $O(n^2)$ versus K-Means' $O(nk)$ per iteration.

**Why Euclidean on lat/lon:** K-Means internally computes cluster centroids as arithmetic means of coordinates, which is mathematically sound only in Euclidean space. Applying Haversine distance would require kernel K-Means or spherical K-Means, adding complexity without meaningful accuracy gain for intra-city distances ($\leq 30$ km, spherical distortion $< 0.5\%$). The simplification is documented in code with the recommended fix for future large-area deployments.

**Why not DBSCAN:** DBSCAN is optimal when the number of clusters is unknown and clusters have irregular shapes. Here, we need exactly $k$ compact clusters centred on different geographic areas of the city — K-Means is the canonical tool for this.

### 3.2 Constraint Satisfaction Problem (CSP) with Backtracking

**Why CSP:** The itinerary problem is naturally a satisfaction-and-optimisation hybrid. Hard constraints (budget, time, opening hours, must-include) must be enforced exactly. CSP formalises these constraints explicitly and can detect infeasibility with provable completeness: if no solution exists, backtracking with forward checking will exhaust the search space and report failure. This is impossible with greedy or learning-based approaches.

**Why custom backtracking over python-constraint library:** The `python-constraint` library provides general constraint solving but does not expose MRV/LCV heuristics, forward checking, or AC-3 at the level of control required for academic demonstration. The custom implementation makes every heuristic visible and justifiable.

**Why not Integer Linear Programming (ILP):** ILP solvers (e.g., PuLP, OR-Tools) would require the problem to be linearised. The preference-match scoring function is non-linear. Furthermore, ILP solvers are black boxes — they cannot explain which constraint was violated or generate the user-facing InfeasibilityReport.

**Why not Greedy:** Greedy algorithms cannot backtrack. A greedy POI-selection algorithm that picks the highest-rated POI each iteration may commit to choices that prevent any feasible solution, whereas backtracking can undo previous decisions.

### 3.3 A* Search for Intra-Day Routing

**Why A*:** A* is complete and optimal given an admissible heuristic (Russell & Norvig, 2020). For the routing sub-problem (visiting $\leq 7$ POIs and returning to hotel), the state space has $2^7 = 128$ states — tractable for exact search. A* guarantees the minimum-travel-time route, which a greedy nearest-neighbour heuristic cannot.

**Why not TSP Solver (OR-Tools/Concorde):** The spec explicitly requires a custom A* implementation, and using a black-box TSP solver would prevent demonstrating the algorithm. Furthermore, OR-Tools is not admissible for the state space as defined; our A* formulation cleanly integrates activity duration into the cost function.

**Why not Dijkstra:** Dijkstra explores all reachable states uniformly. A* with an admissible heuristic guides search toward the goal, expanding fewer nodes. With the MST heuristic, A* is significantly more efficient than Dijkstra for this problem.

**Why MST heuristic:** The Minimum Spanning Tree of remaining unvisited POIs plus the hotel provides a lower bound on the remaining tour cost. **Admissibility proof:** Any Hamiltonian path through $m$ nodes uses exactly $m-1$ edges and spans all nodes — it is itself a spanning tree. Since the MST has minimum cost among all spanning trees, $h(n) = \text{MST cost} \leq \text{any Hamiltonian path cost} \leq \text{optimal remaining tour cost}$. Therefore $h$ is admissible.

### 3.4 Genetic Algorithm (Comparison Baseline)

**Why GA:** The GA provides an empirical comparison point for the CSP+A* pipeline. GAs are well-suited to combinatorial problems with large search spaces and can explore the solution space stochastically, often finding good solutions quickly on easy instances. The comparison exposes the fundamental trade-off: GAs are fast and flexible but do not guarantee feasibility; CSP+A* is slower but guarantees constraint satisfaction.

**Why not SA or ACO:** Simulated Annealing requires careful temperature scheduling and is not population-based (no easy parallelism). Ant Colony Optimisation requires a pheromone model that does not naturally encode multi-day constraints. Tournament-selection GA with OX crossover is the most commonly cited approach for permutation-based scheduling (Goldberg, 1989) and provides a well-understood baseline.

---

## 4. System Architecture

```
User Input (Streamlit) 
      │
      ▼
UserPreferences.validate()
      │
      ▼
DataLoader.load_city()     ← data/cities/{city}.json
      │
      ▼
KMeans Clustering          ← clustering.py
      │                       (Geographic day partitioning)
      ▼
CSPSolver.solve()          ← csp_solver.py
      │  AC-3 → MRV → LCV → Backtracking + Forward Checking
      │
      ▼
route_day() [A*]           ← astar_router.py
      │  State: (location, unvisited) | h: MST cost
      │
      ▼
Itinerary + Score          ← scorer.py
      │  Linear Regression coefficients
      │
      ▼
Streamlit UI               ← app.py
      │  Map (folium) | PDF/JSON export
```

### Module Descriptions

| Module | Responsibility |
|---|---|
| `data_loader.py` | Load and validate POI JSON files against schema |
| `preferences.py` | `UserPreferences` dataclass with `.validate()` |
| `utils.py` | Haversine distance, travel-time estimation |
| `clustering.py` | K-Means geographic day-partitioning |
| `csp_solver.py` | Custom backtracking CSP (MRV, LCV, AC-3, forward checking) |
| `astar_router.py` | A* with MST admissible heuristic |
| `scorer.py` | Scoring function with regression-trained coefficients |
| `ga_solver.py` | Genetic Algorithm (OX crossover, tournament selection) |
| `planner.py` | Orchestrator integrating all modules |
| `app.py` | Streamlit web UI |
| `experiments/benchmark.py` | Automated comparison across 10 scenarios |

---

## 5. Implementation Details

### 5.1 CSP Heuristics

**AC-3 (Arc Consistency Algorithm 3):**  
Before backtracking search begins, AC-3 prunes domains. For each $(x_i, d)$ pair, if assigning POI $i$ to day $d$ is locally infeasible (e.g., the POI's cost alone exceeds the total budget, or its duration alone exceeds the daily pace limit), $d$ is removed from $D(x_i)$. If any variable's domain becomes empty, infeasibility is reported immediately without entering backtracking.

**MRV (Minimum Remaining Values) Variable Ordering:**  
At each backtracking step, the variable with the fewest remaining domain values is selected next. This "fail-first" strategy detects infeasibility early, pruning large subtrees before they are explored. Ties are broken by highest user preference weight (the most important POI is placed first).

**LCV (Least Constraining Value) Value Ordering:**  
For the selected variable, day values are ordered by how few options they remove from remaining variables. By trying the least constraining day first, the algorithm preserves maximum flexibility for remaining POIs, increasing the probability that a feasible assignment is found without backtracking.

**Forward Checking:**  
After assigning a POI to a day, the domains of all unassigned POIs are immediately updated to remove any values that would now be infeasible (e.g., a day that would exceed budget or time if this additional POI were also placed there). If any must-include POI's domain becomes empty, the assignment is immediately rejected.

### 5.2 A* Heuristic — MST with Prim's Algorithm

The heuristic $h(s) = \text{MST}(\text{unvisited POIs} \cup \text{hotel})$ is computed using Prim's algorithm in $O(n^2)$ time, where $n \leq 7+1 = 8$.

**Prim's Algorithm (pseudocode):**
```
in_tree = [False] * n
min_edge = [∞] * n; min_edge[0] = 0
total = 0
repeat n times:
    u = argmin{min_edge[i] : not in_tree[i]}
    in_tree[u] = True; total += min_edge[u]
    for each v not in tree:
        cost = travel_time(u, v)
        if cost < min_edge[v]: min_edge[v] = cost
return total
```

**Admissibility proof (restated):**  
$h(s)$ is the MST weight of the set $V' = \{\text{unvisited POIs}\} \cup \{\text{hotel}\}$. Any path that visits all remaining POIs and returns to the hotel forms a Hamiltonian path on $V'$. A Hamiltonian path on $|V'| = m$ nodes uses $m-1$ edges and is a spanning tree of $V'$. Since the MST has minimum weight among all spanning trees, $\text{MST}(V') \leq \text{any Hamiltonian path on } V'$. Therefore $h(s) \leq h^*(s)$ for all states $s$, making $h$ admissible.

### 5.3 GA Operators

**Order Crossover (OX):**  
1. Select a random contiguous segment from parent $P_1$.  
2. Copy this segment into the child at the same positions.  
3. Fill remaining positions in left-to-right order from $P_2$, skipping elements already in the child.  

OX preserves the relative ordering of elements from both parents, which encodes the geographic visit ordering. It is the standard crossover for permutation-based TSP-like problems (Goldberg, 1989).

**Tournament Selection:**  
Three individuals are sampled at random; the one with highest fitness is selected. Tournament size 3 balances selection pressure (large tournament = more exploitation) and diversity (small tournament = more exploration).

**Mutation:**  
Two mutation operators are applied with equal probability:
- **Swap mutation:** Randomly exchange two genes. Changes local visit ordering without affecting day assignments.
- **Day-boundary shift mutation:** Move one POI from the end of one day's segment to the start of the next. Explores different day-assignment configurations not reachable via swap alone.

### 5.4 Scoring with Linear Regression

The score function has three penalty terms with coefficients $\alpha, \beta, \gamma$:
$$\text{score} = \underbrace{\sum_{p} r_p \cdot w_p}_{\text{preference value}} - \underbrace{\alpha \cdot T_{\text{travel}}}_{\text{travel fatigue}} - \underbrace{\beta \cdot \Delta B}_{\text{budget slack}} - \underbrace{\gamma \cdot V_{\text{pace}}}_{\text{pace violation}}$$

where $r_p$ is POI rating, $w_p$ is user preference match, $T_{\text{travel}}$ is total travel hours, $\Delta B$ is budget fraction unused, and $V_{\text{pace}}$ is pace violation in hours.

Coefficients are learned via Linear Regression on 15 hand-rated itineraries spanning a range of travel intensities and budget utilisations. The regression target is a human-assigned score in $[0, 10]$. The magnitude of each coefficient reflects how much human raters penalise that factor.

---

## 6. Experimental Setup

### 6.1 Test Scenarios

Ten scenarios covering all five cities, varying: number of days (2–5), budget ($80–$1500), pace (relaxed/balanced/packed), and interest weights. See `experiments/benchmark.py` for full definitions.

### 6.2 Metrics

| Metric | Description |
|---|---|
| **Score** | Itinerary score from `scorer.py` (higher is better) |
| **Runtime (s)** | Wall-clock time to produce the solution |
| **Constraint violations** | Number of hard constraints violated in the final solution |
| **POIs visited** | Total number of attractions included |

### 6.3 Hardware

Local CPU execution (no GPU required). All experiments are deterministic (fixed random seed 42).

---

## 7. Results

Results are generated by running `python -m experiments.benchmark` and saved to `experiments/results/benchmark_table.md` and `experiments/results/benchmark_plots.png`.

### 7.1 Benchmark Table (10 Scenarios)

| # | Scenario | CSP Score | GA Score | CSP Time (s) | GA Time (s) | CSP POIs | GA POIs | CSP Violations | GA Violations |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Paris 3-day Budget | 51.56 | 65.78 | 0.020 | 0.499 | 14 | 21 | 0 | 0 |
| 2 | Paris 5-day Luxury | 86.63 | 92.54 | 0.038 | 0.695 | 33 | 35 | 0 | 0 |
| 3 | Istanbul 3-day Culture | 50.83 | 69.21 | 0.009 | 0.457 | 16 | 21 | 0 | 0 |
| 4 | Istanbul 2-day Relaxed | 22.38 | 36.05 | 0.004 | 0.362 | 8 | 14 | 0 | 0 |
| 5 | Tokyo 4-day Family | 47.08 | 68.97 | 0.009 | 0.558 | 17 | 28 | 0 | 3 |
| 6 | Tokyo 3-day Otaku | 46.13 | 68.95 | 0.014 | 0.457 | 15 | 21 | 0 | 0 |
| 7 | Dubai 2-day Adventure | 20.46 | 39.01 | 0.004 | 0.364 | 7 | 14 | 0 | 0 |
| 8 | Dubai 3-day Luxury | 30.27 | 54.70 | 0.004 | 0.460 | 10 | 21 | 0 | 1 |
| 9 | Karachi 2-day Local | 16.99 | 37.11 | 0.004 | 0.365 | 8 | 14 | 0 | 2 |
| 10 | Karachi 3-day History | 42.38 | 53.08 | 0.015 | 0.458 | 18 | 21 | 0 | 0 |
| **Avg** | | **41.47** | **58.54** | **0.012** | **0.467** | **14.6** | **21.0** | **0** | **0.6** |

### 7.2 Key Findings

1. **CSP+A* achieves zero constraint violations across all 10 scenarios.** The CSP solver guarantees feasibility by construction; infeasible instances return a structured InfeasibilityReport with suggested budget/day adjustments.

2. **GA produces 6 violations across 10 scenarios.** The penalty-based fitness function guides the GA toward feasibility but cannot enforce hard constraints. Violations occur on tighter instances (Tokyo 4-day, Dubai 3-day Luxury, Karachi 2-day).

3. **CSP+A* is 39× faster than GA on average** (0.012 s vs 0.467 s). The backtracking search terminates early on well-constrained instances; the GA always runs all 200 generations.

4. **GA scores 41% higher on average** (58.54 vs 41.47). The primary driver is visit count: GA averages 21.0 POIs per trip versus CSP's 14.6, because the GA softly violates constraints to include more POIs. On unconstrained instances (Scenario 2, Paris Luxury), the score gap narrows to 7% (86.63 vs 92.54).

5. **CSP+A* visit count reflects strict constraint enforcement.** Every placed POI satisfies all hard constraints. The scoring function rewards visit count through the preference-value term ($\sum r_p \cdot w_p$), so the CSP score accurately reflects a truly feasible, high-quality plan.

---

## 8. Discussion

### When CSP+A* wins
- **Tight constraints:** When budget or time is limited, the CSP's AC-3 preprocessing and forward checking prune infeasible POI-day assignments early, yielding a compact, high-quality feasible solution that the GA would need many generations to find.
- **Must-include POIs:** The CSP handles must-include constraints explicitly; the GA applies a heavy penalty but may still exclude them in some chromosomes.
- **Explainability:** When no solution exists, the CSP produces a structured InfeasibilityReport explaining which constraint failed and suggesting a remedy ($X more budget, or $Y$ additional days). The GA silently returns the best infeasible solution it found.

### When GA wins
- **Raw score on unconstrained instances:** By softly violating constraints, the GA visits 44% more POIs on average (21.0 vs 14.6), which directly inflates the preference-value component of the score. On unconstrained instances (large budget, packed pace), the score gap narrows but the GA still leads.
- **Speed on large instances:** If the number of POIs grows to hundreds, backtracking may become slow. The GA's $O(gPn)$ runtime scales more predictably.
- **Parallelism:** Multiple GA populations can run in parallel (island model); backtracking is inherently sequential.

---

## 9. Limitations

1. **Scalability beyond 60 POIs.** The CSP solver's backtracking is exponential in the number of variables. With 60 POIs and 7 days, the search space is large; AC-3 and MRV/LCV bring this to a practical range for the datasets used. For 200+ POIs, beam search or constraint propagation with stronger consistency (e.g., path consistency) would be needed.

2. **No real-time traffic data.** Travel times are estimated with Haversine distance and a fixed average city transit speed (25 km/h, representing bus/metro including stops). Real transit times vary by time of day, transit line, and day of week. Integrating a routing API (Google Maps, HERE) would significantly improve accuracy.

3. **Single transit speed assumption.** All inter-POI travel is modelled at 25 km/h regardless of actual transport mode. Walking-only areas, metro frequency, and transfer penalties are not captured. This uniformly underestimates travel time for less well-connected cities.

4. **Static POI data.** The dataset is fixed at load time. POIs may change opening hours, prices, or close temporarily. A production system would need a live data feed.

5. **Single objective.** The scoring function aggregates all objectives (rating, cost, travel time) into a single scalar. A multi-objective formulation (Pareto frontier of time vs. cost vs. quality) would give users more nuanced choices.

---

## 10. Future Work

1. **Reinforcement Learning for preference learning.** Instead of fixed interest weights, an RL agent could learn user preferences from implicit feedback (which POIs the user skips or reorders in the UI).

2. **Multi-objective optimisation.** Replace the scalar score with a Pareto front using NSGA-II, allowing users to trade off travel time against cost or rating.

3. **Real API integration.** Connect to Google Places API for real-time POI data, and Google Directions API for actual transit times.

4. **Probabilistic CSP.** Extend the CSP to handle uncertainty (e.g., rain probability affecting outdoor POIs) using Markov Decision Processes or chance constraints.

5. **Dynamic re-planning.** Allow itinerary adjustment during the trip if a POI is unexpectedly closed or the user runs over time.

---

## 11. References

1. Russell, S., & Norvig, P. (2020). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson. [CSP formulation, A* search, admissibility proofs]

2. Goldberg, D. E. (1989). *Genetic Algorithms in Search, Optimization and Machine Learning*. Addison-Wesley. [GA theory, OX crossover, tournament selection]

3. Chen, Y.-Y., Cheng, A.-J., & Hsu, W. H. (2011). Travel recommendation by mining people attributes and travel group types from community-contributed photos. *IEEE Transactions on Multimedia*, 15(6), 1283–1295. [Trip Planning Query]

4. Gavalas, D., Konstantopoulos, C., Mastakas, K., & Pantziou, G. (2014). A survey on algorithmic approaches for solving tourist trip design problems. *Journal of Heuristics*, 20(3), 291–328. [Itinerary planning survey]

5. Applegate, D. L., Bixby, R. E., Chvátal, V., & Cook, W. J. (2006). *The Traveling Salesman Problem: A Computational Study*. Princeton University Press. [TSP theory and lower bounds]

6. MacKay, D. J. C. (2003). *Information Theory, Inference, and Learning Algorithms*. Cambridge University Press. [Linear Regression and probabilistic inference]
