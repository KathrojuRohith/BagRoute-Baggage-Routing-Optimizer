"""Time-expanded connection graph.

Each *flight* is a node. An edge F1 -> F2 exists when a bag can legally transfer:

    F1.dest == F2.origin
    F2.dep - F1.arr >= MCT(F1.dest)          (minimum connection time)
    F2.dep - F1.arr <= max_layover           (keeps the graph small, avoids silly layovers)
    F2.dest != F1.origin                     (no immediate U-turn)

Because the departures at an airport are sorted by time, the valid successors of a
flight are one contiguous slice found with two binary searches, so building the graph
costs O(F log F + E).
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .models import Flight

DEFAULT_MCT = 45
DEFAULT_MAX_LAYOVER = 480


def group_departures(flights: Iterable[Flight]) -> dict[str, tuple[Flight, ...]]:
    """Departures per origin airport, sorted by (departure time, id)."""
    buckets: dict[str, list[Flight]] = defaultdict(list)
    for f in flights:
        buckets[f.origin].append(f)
    return {o: tuple(sorted(fs, key=lambda f: (f.dep, f.id))) for o, fs in buckets.items()}


def build_connection_graph(
    flights: Iterable[Flight],
    mct: Mapping[str, int],
    default_mct: int = DEFAULT_MCT,
    max_layover: int = DEFAULT_MAX_LAYOVER,
) -> dict[str, tuple[str, ...]]:
    """Pure function: flights + MCT table -> adjacency (flight id -> feasible next flight ids)."""
    flight_list = list(flights)
    departures = group_departures(flight_list)
    times = {o: [f.dep for f in fs] for o, fs in departures.items()}
    graph: dict[str, tuple[str, ...]] = {}
    for f in flight_list:
        outs = departures.get(f.dest, ())
        ts = times.get(f.dest, [])
        lo = bisect_left(ts, f.arr + mct.get(f.dest, default_mct))
        hi = bisect_right(ts, f.arr + max_layover)
        graph[f.id] = tuple(g.id for g in outs[lo:hi] if g.dest != f.origin)
    return graph


@dataclass(frozen=True)
class Network:
    """Immutable bundle of everything a router needs (cheap to ship to worker processes)."""

    flights: Mapping[str, Flight]
    graph: Mapping[str, tuple[str, ...]]
    departures: Mapping[str, tuple[Flight, ...]]
    dep_times: Mapping[str, tuple[int, ...]]
    mct: Mapping[str, int]
    default_mct: int = DEFAULT_MCT
    max_layover: int = DEFAULT_MAX_LAYOVER

    @classmethod
    def from_flights(
        cls,
        flights: Iterable[Flight],
        mct: Mapping[str, int] | None = None,
        default_mct: int = DEFAULT_MCT,
        max_layover: int = DEFAULT_MAX_LAYOVER,
    ) -> Network:
        flight_list = list(flights)
        by_id = {f.id: f for f in flight_list}
        if len(by_id) != len(flight_list):
            raise ValueError("duplicate flight ids")
        table = dict(mct or {})
        departures = group_departures(flight_list)
        return cls(
            flights=by_id,
            graph=build_connection_graph(flight_list, table, default_mct, max_layover),
            departures=departures,
            dep_times={o: tuple(f.dep for f in fs) for o, fs in departures.items()},
            mct=table,
            default_mct=default_mct,
            max_layover=max_layover,
        )

    def min_connection(self, airport: str) -> int:
        return self.mct.get(airport, self.default_mct)

    def first_flights(self, origin: str, ready: int) -> tuple[Flight, ...]:
        """Flights leaving `origin` at or after `ready`."""
        i = bisect_left(self.dep_times.get(origin, ()), ready)
        return self.departures.get(origin, ())[i:]

    @property
    def edge_count(self) -> int:
        return sum(len(v) for v in self.graph.values())
