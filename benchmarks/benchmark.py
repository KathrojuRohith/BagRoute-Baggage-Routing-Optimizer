"""Performance evaluation: runtime vs bag count, parallel speedup, greedy vs exact gap.

    python benchmarks/benchmark.py
    python benchmarks/benchmark.py --bags 1000 5000 20000 --workers 1 2 4
Writes benchmarks/results.csv and prints tables.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from baggage_router import GreedyAssigner, Network, ParallelRouter  # noqa: E402
from baggage_router.exact import optimal_assignment  # noqa: E402
from baggage_router.models import Bag  # noqa: E402
from baggage_router.synthetic import default_mct, generate_bags, generate_flights  # noqa: E402


def run(net: Network, bags: list[Bag], workers: int) -> tuple[float, float, int]:
    t0 = time.perf_counter()
    with ParallelRouter(net, workers) as pr:
        initial = pr.route_all(bags)
    t1 = time.perf_counter()
    result = GreedyAssigner(net).assign(bags, initial)
    t2 = time.perf_counter()
    return t1 - t0, t2 - t1, len(result.assigned)


def greedy_vs_exact(trials: int = 200, n_bags: int = 8) -> tuple[float, int, int]:
    """Tiny tight-capacity instances -> (mean greedy/optimal, worst gap, #suboptimal)."""
    ratios: list[float] = []
    worst = subopt = 0
    for seed in range(trials):
        flights = generate_flights(hubs=1, spokes_per_hub=3, waves=2, capacity=(1, 2), seed=seed)
        net = Network.from_flights(flights, default_mct(flights))
        rng = Random(seed)
        bags = [
            Bag(b.id, b.origin, b.dest, b.ready, b.ready + rng.randrange(240, 900, 30), b.priority)
            for b in generate_bags(flights, n_bags, seed)
        ]
        g = len(GreedyAssigner(net).assign(bags).assigned)
        opt = optimal_assignment(net, bags)
        assert g <= opt
        if opt:
            ratios.append(g / opt)
        worst = max(worst, opt - g)
        subopt += g < opt
    return (sum(ratios) / len(ratios) if ratios else 1.0), worst, subopt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bags", type=int, nargs="+", default=[1000, 4000, 16000])
    ap.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4])
    ap.add_argument("--hubs", type=int, default=5)
    ap.add_argument("--spokes", type=int, default=10)
    ap.add_argument("--waves", type=int, default=8)
    args = ap.parse_args()

    flights = generate_flights(args.hubs, args.spokes, args.waves, capacity=(20, 60))
    net = Network.from_flights(flights, default_mct(flights))
    print(f"network: {len(flights)} flights, {net.edge_count} edges, cpus={os.cpu_count()}\n")

    rows: list[dict[str, float | int]] = []
    print(f"{'bags':>7} {'workers':>7} {'route_s':>8} {'assign_s':>9} {'speedup':>8} {'on-time':>8}")
    for n in args.bags:
        bags = generate_bags(flights, n)
        base = 0.0
        for w in args.workers:
            route_s, assign_s, ok = run(net, bags, w)
            base = base or route_s
            print(f"{n:>7} {w:>7} {route_s:>8.2f} {assign_s:>9.2f} {base / route_s:>7.2f}x {ok / n:>8.1%}")
            rows.append({"bags": n, "workers": w, "route_s": route_s, "assign_s": assign_s,
                         "on_time": ok / n})

    out = Path(__file__).with_name("results.csv")
    with out.open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print(f"\nresults -> {out}")

    mean_ratio, worst, subopt = greedy_vs_exact()
    print(f"\ngreedy vs exact (200 tiny instances): mean greedy/optimal = {mean_ratio:.3f}, "
          f"worst gap = {worst} bag(s), suboptimal in {subopt} instances")


if __name__ == "__main__":
    main()
