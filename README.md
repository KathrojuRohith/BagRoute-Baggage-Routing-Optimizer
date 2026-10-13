# Airline Baggage Routing Optimizer

Routes checked bags through a hub-and-spoke network respecting **minimum connection times (MCT)**,
**flight hold capacity** and **bag deadlines**.

| Concern | Technique |
|---|---|
| Model | Time-expanded graph, one node per flight, edge iff MCT <= layover <= max layover |
| Routing | Dijkstra (heap), one shortest-path tree per (origin, ready-time) shared by all bags in the group |
| Capacity | Greedy: tightest slack first, re-route around full flights |
| Baseline | Branch-and-bound exact solver (`exact.py`) to measure the greedy gap |
| Scale | `ProcessPoolExecutor` for the CPU-bound tree building; assignment stays sequential |

## Run
```bash
python -m baggage_router serve            # web console + API at http://127.0.0.1:8000
python -m baggage_router demo --bags 2000 --workers 2
python -m baggage_router generate data/ --bags 5000 --hubs 5 --spokes 10
python -m baggage_router route data/flights.csv data/bags.csv --mct H0=60 --workers 4 --out data/report.csv
python benchmarks/benchmark.py --bags 1000 5000 20000 --workers 1 2 4
```
Python >= 3.10, no runtime dependencies.

## Operations control console
`python -m baggage_router serve` opens a full-bleed map interface (screenshots in `docs/screenshots/`).

Design decisions, taken from studying open-source flight trackers (Aeris, AeroScope, TravStats) and
control-tower / baggage-supervision products (BEUMER Flow Twin, exception-first control towers):

- **Exception-first.** The right panel opens on *Needs attention* (at-risk bags grouped by reason, full flights), and only strained lanes are drawn in colour, so the map stays calm.
- **Follow one bag.** Search a bag, flight or airport (press `/`). A bag shows a step-by-step journey that updates live as the day replays, with a "next action" for bags that cannot be placed.
- **Replay the day.** Aircraft move along their lanes; play/pause, three speeds, and a scrubber with a "bags in the air" profile.
- **One-click scenarios.** Normal day, peak day, Delhi closed, tight holds. Cancel any flight or close any airport and the plan recomputes with an impact readout.
- **Quality of life.** Hover cards, deep links (`#bag=B000002`), remembered settings, light/dark, keyboard shortcuts (`/`, space, Esc), CSV export.

| Endpoint | Purpose |
|---|---|
| `GET /api/network` | airports (IATA, name, coordinates) and the full schedule |
| `POST /api/plan` | `{bags, seed, hub_mct, capacity_scale, workers, cancelled[]}` -> summary, flights with load, per-bag results |
| `GET /api/health` | liveness probe |

Binds to 127.0.0.1 by default; inputs are range-checked and request bodies capped at 64 KB.
Docker: `docker build -t baggage-router . && docker run -p 8000:8000 baggage-router`.
The page loads the Barlow font from Google Fonts and falls back to Arial Narrow when offline.
The airports are real; the flight schedule is generated, so results illustrate the method, not real operations.

## Quality gates
```bash
pip install -e ".[dev]"
pytest                 # unit, integration, property-based (Hypothesis), randomized fuzz; coverage report
mypy                   # strict
ruff check . && black --check .
docker build -t baggage-router . && docker run --rm baggage-router
```

## Layout
```
baggage_router/  service (plan), server (HTTP), web/index.html (console), models, graph, routing (Strategy), assignment, exact, parallel, validation, io, synthetic, cli, utils
tests/           graph / routing / assignment / parallel / io / properties (Hypothesis) / fuzz
benchmarks/      runtime, parallel speedup, greedy-vs-exact
docs/            SPEC.md (spec-first), AI_LOG.md (prompt + review log)
```

## Known limits (say these in the defence)
- Greedy is a heuristic; `test_assignment.py` contains a counterexample (greedy 1 vs optimal 2).
- Dijkstra's per-leg penalty (120 min) is a tunable preference for fewer connections, not a physical quantity.
- Capacity is counted in bags (no weight/volume); MCT is per airport, not per terminal/carrier.
- Parallel speedup depends on core count and bag volume; at small sizes pickling overhead dominates.
