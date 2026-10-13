"""Greedy capacity-aware assignment.

Order: tightest slack first (deadline - earliest possible arrival), then higher priority.
Each bag takes its unconstrained best route if every flight still has room; otherwise it is
re-routed with the full flights blocked. Greedy is NOT optimal in general (see exact.py).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from .graph import Network
from .models import Bag, Flight, Route
from .routing import DijkstraRouter, RoutingStrategy


class CapacityTracker:
    """Remaining hold space per flight; keeps the set of full flights incrementally."""

    def __init__(self, flights: Mapping[str, Flight]) -> None:
        self._remaining = {fid: f.capacity for fid, f in flights.items()}
        self._full = {fid for fid, r in self._remaining.items() if r <= 0}

    def has_room(self, legs: Iterable[str]) -> bool:
        return all(self._remaining[leg] > 0 for leg in legs)

    def take(self, legs: Iterable[str]) -> None:
        for leg in legs:
            self._remaining[leg] -= 1
            if self._remaining[leg] <= 0:
                self._full.add(leg)

    def remaining(self, flight_id: str) -> int:
        return self._remaining[flight_id]

    @property
    def full(self) -> frozenset[str]:
        return frozenset(self._full)


@dataclass
class AssignmentResult:
    assigned: dict[str, Route] = field(default_factory=dict)
    unassigned: dict[str, str] = field(default_factory=dict)  # bag id -> reason
    rerouted: int = 0

    def on_time_rate(self) -> float:
        total = len(self.assigned) + len(self.unassigned)
        return len(self.assigned) / total if total else 1.0


class GreedyAssigner:
    def __init__(self, network: Network, router: RoutingStrategy | None = None) -> None:
        self.network = network
        self.router: RoutingStrategy = router or DijkstraRouter()

    def assign(
        self, bags: Iterable[Bag], initial: Mapping[str, Route | None] | None = None
    ) -> AssignmentResult:
        """`initial` = precomputed unconstrained routes (e.g. from ParallelRouter)."""
        bag_list = list(bags)
        net = self.network
        first = (
            initial
            if initial is not None
            else {b.id: self.router.find_route(net, b) for b in bag_list}
        )
        result = AssignmentResult()
        candidates: list[tuple[int, int, str, Bag, Route]] = []
        for b in bag_list:
            r = first.get(b.id)
            if r is None:
                result.unassigned[b.id] = "no connecting route"
            elif r.arrival > b.deadline:
                result.unassigned[b.id] = "earliest arrival misses deadline"
            else:
                candidates.append((b.deadline - r.arrival, -b.priority, b.id, b, r))
        candidates.sort(key=lambda c: c[:3])  # slack, priority, id (deterministic)

        tracker = CapacityTracker(net.flights)
        for _slack, _prio, _id, bag, route in candidates:
            if not tracker.has_room(route.legs):
                result.rerouted += 1
                alt = self.router.find_route(net, bag, tracker.full)
                if alt is None or alt.arrival > bag.deadline:
                    result.unassigned[bag.id] = "capacity exhausted"
                    continue
                route = alt
            tracker.take(route.legs)
            result.assigned[bag.id] = route
        return result
