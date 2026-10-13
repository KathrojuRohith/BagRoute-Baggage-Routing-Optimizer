"""Parallel shortest-path computation.

Why processes: tree building is pure-Python CPU work, so threads would serialise on the GIL.
Work unit: one (origin, ready-time) *group* - one tree answers every bag in the group
(amortised cost). The network is shipped once per worker via the pool initializer.
The assignment phase stays sequential: bags compete for shared capacity.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from types import TracebackType

from .graph import Network
from .models import Bag, Route
from .routing import build_tree, extract_legs, make_route
from .utils import timed

Task = tuple[str, int, tuple[tuple[str, str], ...]]  # origin, ready, ((bag_id, dest), ...)
Answer = list[tuple[str, tuple[str, ...] | None]]

_NET: Network | None = None


def _init_worker(net: Network) -> None:
    global _NET
    _NET = net


def solve_group(net: Network, task: Task) -> Answer:
    """Pure function: one tree, many answers."""
    origin, ready, items = task
    tree = build_tree(net, origin, ready)
    return [(bag_id, extract_legs(tree, dest)) for bag_id, dest in items]


def _worker(task: Task) -> Answer:
    assert _NET is not None, "worker not initialised"
    return solve_group(_NET, task)


def group_bags(bags: Iterable[Bag]) -> list[Task]:
    groups: dict[tuple[str, int], list[tuple[str, str]]] = defaultdict(list)
    for b in bags:
        groups[(b.origin, b.ready)].append((b.id, b.dest))
    return [(o, r, tuple(items)) for (o, r), items in sorted(groups.items())]


class ParallelRouter:
    """Context manager owning a process pool. workers <= 1 runs in-process (no pool)."""

    def __init__(self, network: Network, workers: int = 1) -> None:
        self.network = network
        self.workers = workers
        self._pool: ProcessPoolExecutor | None = None

    def __enter__(self) -> ParallelRouter:
        if self.workers > 1:
            self._pool = ProcessPoolExecutor(
                max_workers=self.workers, initializer=_init_worker, initargs=(self.network,)
            )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=True, cancel_futures=exc_type is not None)
            self._pool = None

    @timed
    def route_all(self, bags: Sequence[Bag]) -> dict[str, Route | None]:
        """Unconstrained (capacity-ignoring) earliest-arrival route for every bag."""
        tasks = group_bags(bags)
        if self._pool is None:
            answers = [solve_group(self.network, t) for t in tasks]
        else:
            chunk = max(1, len(tasks) // (self.workers * 4))
            answers = list(self._pool.map(_worker, tasks, chunksize=chunk))
        out: dict[str, Route | None] = {}
        for answer in answers:
            for bag_id, legs in answer:
                out[bag_id] = None if legs is None else make_route(self.network, bag_id, legs)
        return out
