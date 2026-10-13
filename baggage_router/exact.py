"""Exact assignment by branch-and-bound (small instances only) - the greedy benchmark."""

from __future__ import annotations

from collections.abc import Sequence

from .graph import Network
from .models import Bag
from .routing import enumerate_paths


def optimal_assignment(
    net: Network, bags: Sequence[Bag], max_candidates: int | None = None
) -> int:
    """Maximum number of bags that can be delivered on time without exceeding capacity.

    Branch: for each bag choose one of its on-time candidate paths, or skip it.
    Bound: prune when current + remaining bags cannot beat the incumbent.
    """
    cands: list[list[tuple[str, ...]]] = []
    for b in bags:
        paths = [
            p
            for p in enumerate_paths(net, b.origin, b.ready, b.dest)
            if net.flights[p[-1]].arr <= b.deadline
        ]
        paths.sort(key=lambda p: (net.flights[p[-1]].arr, len(p)))
        if paths:
            cands.append(paths if max_candidates is None else paths[:max_candidates])
    cands.sort(key=len)  # most constrained first
    remaining = {fid: f.capacity for fid, f in net.flights.items()}
    best = 0

    def search(i: int, count: int) -> None:
        nonlocal best
        best = max(best, count)
        if i == len(cands) or count + (len(cands) - i) <= best:
            return
        for path in cands[i]:
            if all(remaining[leg] > 0 for leg in path):
                for leg in path:
                    remaining[leg] -= 1
                search(i + 1, count + 1)
                for leg in path:
                    remaining[leg] += 1
        search(i + 1, count)

    search(0, 0)
    return best
