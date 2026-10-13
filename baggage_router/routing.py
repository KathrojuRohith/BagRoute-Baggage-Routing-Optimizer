"""Routing strategies.

Node = flight, so a node's arrival time is fixed regardless of how the bag got there.
"Earliest arrival" is therefore decided by *which destination flight* is reachable; Dijkstra
over (layover + per-leg penalty) picks, among all ways to reach that flight, the path with
the fewest/shortest connections (fewer handoffs = fewer mishandled bags).

`DijkstraRouter`    - production algorithm, O((F + E) log F) per shortest-path tree.
`BruteForceRouter`  - exhaustive DFS oracle used only to validate Dijkstra in tests.
"""

from __future__ import annotations

import heapq
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from .graph import Network
from .models import Bag, Route

LEG_PENALTY = 120  # minutes of "cost" added per flight leg


@dataclass(frozen=True)
class PathTree:
    """Shortest-path tree from one (origin, ready-time) over the connection graph."""

    cost: dict[str, int]
    prev: dict[str, str | None]
    best_to: dict[str, str]  # destination airport -> id of earliest-arriving reachable flight


def build_tree(
    net: Network,
    origin: str,
    ready: int,
    blocked: frozenset[str] = frozenset(),
    leg_penalty: int = LEG_PENALTY,
) -> PathTree:
    cost: dict[str, int] = {}
    prev: dict[str, str | None] = {}
    heap: list[tuple[int, str]] = []
    for f in net.first_flights(origin, ready):
        if f.id not in blocked:
            cost[f.id] = 0
            prev[f.id] = None
            heapq.heappush(heap, (0, f.id))
    while heap:
        c, fid = heapq.heappop(heap)
        if c > cost[fid]:
            continue  # stale heap entry
        arr = net.flights[fid].arr
        for gid in net.graph[fid]:
            if gid in blocked:
                continue
            nc = c + (net.flights[gid].dep - arr) + leg_penalty
            if nc < cost.get(gid, nc + 1):
                cost[gid] = nc
                prev[gid] = fid
                heapq.heappush(heap, (nc, gid))
    best_to: dict[str, str] = {}
    for fid, c in cost.items():
        f = net.flights[fid]
        cur = best_to.get(f.dest)
        if cur is None or (f.arr, c, fid) < (net.flights[cur].arr, cost[cur], cur):
            best_to[f.dest] = fid
    return PathTree(cost, prev, best_to)


def extract_legs(tree: PathTree, dest: str) -> tuple[str, ...] | None:
    fid: str | None = tree.best_to.get(dest)
    if fid is None:
        return None
    legs: list[str] = []
    while fid is not None:
        legs.append(fid)
        fid = tree.prev[fid]
    return tuple(reversed(legs))


def make_route(net: Network, bag_id: str, legs: tuple[str, ...]) -> Route:
    return Route(bag_id, legs, net.flights[legs[-1]].arr)


class RoutingStrategy(Protocol):
    """Strategy interface: swap Dijkstra for an exact or heuristic router."""

    def find_route(
        self, network: Network, bag: Bag, blocked: frozenset[str] = frozenset()
    ) -> Route | None:
        """Earliest-arrival route avoiding `blocked` flights (deadline is *not* checked here)."""
        ...


class DijkstraRouter:
    def __init__(self, leg_penalty: int = LEG_PENALTY) -> None:
        self.leg_penalty = leg_penalty

    def find_route(
        self, network: Network, bag: Bag, blocked: frozenset[str] = frozenset()
    ) -> Route | None:
        tree = build_tree(network, bag.origin, bag.ready, blocked, self.leg_penalty)
        legs = extract_legs(tree, bag.dest)
        return None if legs is None else make_route(network, bag.id, legs)


def enumerate_paths(
    net: Network,
    origin: str,
    ready: int,
    dest: str,
    blocked: frozenset[str] = frozenset(),
) -> Iterator[tuple[str, ...]]:
    """Every legal flight sequence from origin to dest (stops at first arrival at dest)."""

    def dfs(path: list[str]) -> Iterator[tuple[str, ...]]:
        if net.flights[path[-1]].dest == dest:
            yield tuple(path)
            return
        for gid in net.graph[path[-1]]:
            if gid not in blocked:
                path.append(gid)
                yield from dfs(path)
                path.pop()

    for f in net.first_flights(origin, ready):
        if f.id not in blocked:
            yield from dfs([f.id])


class BruteForceRouter:
    """Exponential oracle. Same interface as DijkstraRouter; tiny inputs only."""

    def find_route(
        self, network: Network, bag: Bag, blocked: frozenset[str] = frozenset()
    ) -> Route | None:
        best: tuple[str, ...] | None = None
        for p in enumerate_paths(network, bag.origin, bag.ready, bag.dest, blocked):
            if best is None or network.flights[p[-1]].arr < network.flights[best[-1]].arr:
                best = p
        return None if best is None else make_route(network, bag.id, best)
