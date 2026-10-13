"""CSV input/output. Bags are streamed lazily with generators."""

from __future__ import annotations

import csv
import itertools
from collections.abc import Iterable, Iterator
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

from .assignment import AssignmentResult
from .models import Bag, Flight

T = TypeVar("T")


@lru_cache(maxsize=4096)
def parse_time(text: str) -> int:
    """'HH:MM' or integer minutes -> minutes."""
    text = text.strip()
    if ":" in text:
        hours, minutes = text.split(":")
        return int(hours) * 60 + int(minutes)
    return int(text)


def chunked(items: Iterable[T], size: int) -> Iterator[list[T]]:
    it = iter(items)
    while batch := list(itertools.islice(it, size)):
        yield batch


def read_flights(path: Path) -> list[Flight]:
    with path.open(newline="") as fh:
        return [
            Flight(
                r["id"], r["origin"], r["dest"], parse_time(r["dep"]), parse_time(r["arr"]),
                int(r["capacity"]),
            )
            for r in csv.DictReader(fh)
        ]


def iter_bags(path: Path) -> Iterator[Bag]:
    with path.open(newline="") as fh:
        for r in csv.DictReader(fh):
            yield Bag(
                r["id"], r["origin"], r["dest"], parse_time(r["ready"]),
                parse_time(r["deadline"]), int(r.get("priority") or 0),
            )


def write_flights(flights: Iterable[Flight], path: Path) -> None:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "origin", "dest", "dep", "arr", "capacity"])
        w.writerows((f.id, f.origin, f.dest, f.dep, f.arr, f.capacity) for f in flights)


def write_bags(bags: Iterable[Bag], path: Path) -> None:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "origin", "dest", "ready", "deadline", "priority"])
        w.writerows((b.id, b.origin, b.dest, b.ready, b.deadline, b.priority) for b in bags)


def write_report(result: AssignmentResult, path: Path) -> None:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bag_id", "status", "itinerary", "arrival", "detail"])
        for bag_id in sorted(result.assigned):
            r = result.assigned[bag_id]
            w.writerow([bag_id, "ASSIGNED", ">".join(r.legs), r.arrival, f"{r.connections} connection(s)"])
        for bag_id in sorted(result.unassigned):
            w.writerow([bag_id, "UNASSIGNED", "", "", result.unassigned[bag_id]])
