"""Command line: serve | generate | route | demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .assignment import GreedyAssigner
from .graph import Network
from .io import iter_bags, read_flights, write_bags, write_flights, write_report
from .parallel import ParallelRouter
from .synthetic import default_mct, generate_bags, generate_flights
from .validation import validate_assignment


def _run(net: Network, bags: list, workers: int, out: Path | None) -> int:
    with ParallelRouter(net, workers) as pr:
        initial = pr.route_all(bags)
    result = GreedyAssigner(net).assign(bags, initial)
    errors = validate_assignment(net, bags, result)
    total = len(bags)
    print(f"flights={len(net.flights)} edges={net.edge_count} bags={total}")
    print(
        f"assigned={len(result.assigned)} unassigned={len(result.unassigned)} "
        f"rerouted={result.rerouted} on-time={result.on_time_rate():.1%}"
    )
    for bag_id in list(result.assigned)[:3]:
        r = result.assigned[bag_id]
        print(f"  {bag_id}: {' > '.join(r.legs)} (arrives {r.arrival})")
    for bag_id in list(result.unassigned)[:3]:
        print(f"  {bag_id}: UNASSIGNED - {result.unassigned[bag_id]}")
    if out is not None:
        write_report(result, out)
        print(f"report written to {out}")
    if errors:
        print("CONSTRAINT VIOLATIONS:", *errors[:10], sep="\n  ")
        return 1
    print("verification: all constraints satisfied")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="baggage-router", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="write synthetic flights.csv and bags.csv")
    g.add_argument("outdir", type=Path)
    g.add_argument("--hubs", type=int, default=3)
    g.add_argument("--spokes", type=int, default=8, help="spokes per hub")
    g.add_argument("--waves", type=int, default=12)
    g.add_argument("--bags", type=int, default=1000)
    g.add_argument("--seed", type=int, default=0)

    r = sub.add_parser("route", help="route bags from CSV files")
    r.add_argument("flights", type=Path)
    r.add_argument("bags", type=Path)
    r.add_argument("--out", type=Path)
    r.add_argument("--workers", type=int, default=1)
    r.add_argument("--default-mct", type=int, default=45)
    r.add_argument("--max-layover", type=int, default=480)
    r.add_argument("--mct", action="append", default=[], metavar="AIRPORT=MIN")

    d = sub.add_parser("demo", help="generate data in memory and route it")
    d.add_argument("--bags", type=int, default=2000)
    d.add_argument("--workers", type=int, default=2)
    d.add_argument("--seed", type=int, default=0)

    v = sub.add_parser("serve", help="start the web console and API")
    v.add_argument("--host", default="127.0.0.1")
    v.add_argument("--port", type=int, default=8000)

    args = p.parse_args(argv)
    if args.cmd == "serve":
        from .server import serve

        serve(args.host, args.port)
        return 0
    if args.cmd == "generate":
        flights = generate_flights(args.hubs, args.spokes, args.waves, seed=args.seed)
        args.outdir.mkdir(parents=True, exist_ok=True)
        write_flights(flights, args.outdir / "flights.csv")
        write_bags(generate_bags(flights, args.bags, args.seed), args.outdir / "bags.csv")
        print(f"wrote {len(flights)} flights and {args.bags} bags to {args.outdir}")
        return 0
    if args.cmd == "route":
        mct = {k: int(v) for k, v in (item.split("=") for item in args.mct)}
        net = Network.from_flights(
            read_flights(args.flights), mct, args.default_mct, args.max_layover
        )
        return _run(net, list(iter_bags(args.bags)), args.workers, args.out)
    flights = generate_flights(seed=args.seed, capacity=(5, 15))
    net = Network.from_flights(flights, default_mct(flights))
    return _run(net, generate_bags(flights, args.bags, args.seed), args.workers, None)


if __name__ == "__main__":
    sys.exit(main())
