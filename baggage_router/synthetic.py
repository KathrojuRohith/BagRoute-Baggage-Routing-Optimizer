"""Synthetic hub-and-spoke data: hubs in a full mesh, spokes attached to one hub each."""

from __future__ import annotations

from random import Random

from .models import Bag, Flight


def default_mct(flights: list[Flight]) -> dict[str, int]:
    """Hubs need longer transfers (60 min) than spokes (default 45)."""
    return {a: 60 for f in flights for a in (f.origin, f.dest) if a.startswith("H")}


def generate_flights(
    hubs: int = 3,
    spokes_per_hub: int = 8,
    waves: int = 12,
    capacity: tuple[int, int] = (10, 30),
    seed: int = 0,
) -> list[Flight]:
    rng = Random(seed)
    flights: list[Flight] = []

    def add(origin: str, dest: str, lo: int, hi: int) -> None:
        for w in range(waves):
            dep = int(w * 1200 / waves) + rng.randrange(0, 60, 5)
            dur = rng.randrange(lo, hi + 1, 5)
            flights.append(
                Flight(
                    f"F{len(flights):05d}", origin, dest, dep, dep + dur, rng.randint(*capacity)
                )
            )

    hub_names = [f"H{h}" for h in range(hubs)]
    for h, hub in enumerate(hub_names):
        for s in range(spokes_per_hub):
            spoke = f"S{h}_{s}"
            add(spoke, hub, 60, 180)
            add(hub, spoke, 60, 180)
        for other in hub_names:
            if other != hub:
                add(hub, other, 90, 240)
    return flights


def generate_bags(
    flights: list[Flight], n: int, seed: int = 0, deadline_range: tuple[int, int] = (300, 1200)
) -> list[Bag]:
    rng = Random(seed)
    spokes = sorted({f.origin for f in flights if f.origin.startswith("S")})
    if len(spokes) < 2:
        raise ValueError("need at least two spoke airports")
    bags: list[Bag] = []
    for i in range(n):
        origin, dest = rng.sample(spokes, 2)
        ready = rng.randrange(0, 720, 30)  # check-in slots of 30 min
        deadline = ready + rng.randrange(deadline_range[0], deadline_range[1], 30)
        bags.append(Bag(f"B{i:06d}", origin, dest, ready, deadline, rng.randint(0, 2)))
    return bags
