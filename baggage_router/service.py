"""Planning service layer: pure functions that turn UI parameters into a full plan.

Kept free of HTTP so it can be unit-tested and reused (CLI, API, notebooks).
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import replace
from functools import lru_cache
from typing import Any

from .assignment import GreedyAssigner
from .graph import Network
from .models import Flight
from .parallel import ParallelRouter
from .synthetic import generate_bags, generate_flights
from .validation import validate_assignment


# Display metadata: internal synthetic codes -> real Indian airports (schedule itself is illustrative).
_HUBS = {"H0": ("DEL", "Delhi", 28.56, 77.10), "H1": ("BOM", "Mumbai", 19.09, 72.87),
         "H2": ("BLR", "Bengaluru", 13.20, 77.71)}
_SPOKES = {
    "H0": [("JAI", "Jaipur", 26.82, 75.81), ("LKO", "Lucknow", 26.76, 80.88),
           ("ATQ", "Amritsar", 31.71, 74.80), ("IXC", "Chandigarh", 30.67, 76.79),
           ("VNS", "Varanasi", 25.45, 82.86), ("SXR", "Srinagar", 33.99, 74.77)],
    "H1": [("PNQ", "Pune", 18.58, 73.92), ("AMD", "Ahmedabad", 23.07, 72.63),
           ("GOI", "Goa", 15.38, 73.83), ("NAG", "Nagpur", 21.09, 79.05),
           ("IDR", "Indore", 22.72, 75.80), ("STV", "Surat", 21.11, 72.74)],
    "H2": [("MAA", "Chennai", 12.99, 80.17), ("HYD", "Hyderabad", 17.24, 78.43),
           ("VGA", "Vijayawada", 16.53, 80.80), ("COK", "Kochi", 10.15, 76.40),
           ("TRV", "Thiruvananthapuram", 8.48, 76.92), ("IXM", "Madurai", 9.83, 78.09)],
}


def _meta(code: str) -> tuple[str, str, float, float]:
    if code in _HUBS:
        return _HUBS[code]
    hub, idx = "H" + code[1], int(code.split("_")[1])
    return _SPOKES[hub][idx]


@lru_cache(maxsize=1)
def base_flights() -> tuple[Flight, ...]:
    return tuple(generate_flights(hubs=3, spokes_per_hub=6, waves=10, capacity=(10, 26), seed=0))


def network_info() -> dict[str, Any]:
    flights = base_flights()
    codes = sorted({a for f in flights for a in (f.origin, f.dest)})
    airports = [
        {"code": c, "hub": c.startswith("H"), "parent": None if c.startswith("H") else "H" + c[1],
         "iata": _meta(c)[0], "name": _meta(c)[1], "lat": _meta(c)[2], "lon": _meta(c)[3]}
        for c in codes
    ]
    return {
        "airports": airports,
        "flights": [
            {"id": f.id, "o": f.origin, "d": f.dest, "dep": f.dep, "arr": f.arr, "cap": f.capacity}
            for f in flights
        ],
    }


def _number(params: dict[str, Any], key: str, default: float, lo: float, hi: float) -> float:
    value = params.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    if not lo <= value <= hi:
        raise ValueError(f"{key} must be between {lo} and {hi}")
    return float(value)


def plan(params: dict[str, Any]) -> dict[str, Any]:
    n_bags = int(_number(params, "bags", 1500, 1, 20000))
    seed = int(_number(params, "seed", 1, 0, 10**6))
    hub_mct = int(_number(params, "hub_mct", 60, 0, 240))
    scale = _number(params, "capacity_scale", 1.0, 0.1, 3.0)
    workers = int(_number(params, "workers", 1, 1, 8))
    cancelled = params.get("cancelled", [])
    if not isinstance(cancelled, list) or not all(isinstance(c, str) for c in cancelled):
        raise ValueError("cancelled must be a list of flight ids")

    full_schedule = base_flights()
    gone = set(cancelled)
    live = [
        replace(f, capacity=max(0, round(f.capacity * scale)))
        for f in full_schedule
        if f.id not in gone
    ]
    mct = {a: hub_mct for f in live for a in (f.origin, f.dest) if a.startswith("H")}
    net = Network.from_flights(live, mct)
    bags = generate_bags(list(full_schedule), n_bags, seed, deadline_range=(600, 1500))

    t0 = time.perf_counter()
    with ParallelRouter(net, workers) as pr:
        initial = pr.route_all(bags)
    result = GreedyAssigner(net).assign(bags, initial)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    violations = validate_assignment(net, bags, result)

    load: Counter[str] = Counter()
    for route in result.assigned.values():
        load.update(route.legs)

    rows = []
    for b in bags:
        route = result.assigned.get(b.id)
        rows.append(
            {
                "id": b.id, "o": b.origin, "d": b.dest, "ready": b.ready, "deadline": b.deadline,
                "pri": b.priority, "ok": route is not None,
                "legs": list(route.legs) if route else [],
                "arrival": route.arrival if route else None,
                "reason": None if route else result.unassigned[b.id],
            }
        )
    return {
        "summary": {
            "bags": n_bags, "assigned": len(result.assigned),
            "unassigned": len(result.unassigned), "rerouted": result.rerouted,
            "on_time_rate": result.on_time_rate(), "ms": round(elapsed_ms, 1),
            "violations": len(violations), "flights": len(live), "edges": net.edge_count,
            "reasons": dict(Counter(result.unassigned.values())),
        },
        "flights": [
            {"id": f.id, "o": f.origin, "d": f.dest, "dep": f.dep, "arr": f.arr,
             "cap": f.capacity, "load": load[f.id]}
            for f in live
        ],
        "bags": rows,
    }
