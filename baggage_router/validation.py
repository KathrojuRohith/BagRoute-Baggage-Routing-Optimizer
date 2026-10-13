"""Independent checker for the hard constraints. Used by the CLI (--verify) and the tests."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .assignment import AssignmentResult
from .graph import Network
from .models import Bag, Route


def validate_route(net: Network, bag: Bag, route: Route) -> list[str]:
    errs: list[str] = []
    if not route.legs:
        return [f"{bag.id}: empty route"]
    if any(leg not in net.flights for leg in route.legs):
        return [f"{bag.id}: unknown flight in route"]
    legs = [net.flights[leg] for leg in route.legs]
    if legs[0].origin != bag.origin:
        errs.append(f"{bag.id}: first leg does not leave the bag's origin")
    if legs[0].dep < bag.ready:
        errs.append(f"{bag.id}: first leg departs before the bag is ready")
    if legs[-1].dest != bag.dest:
        errs.append(f"{bag.id}: last leg does not reach the destination")
    if legs[-1].arr > bag.deadline:
        errs.append(f"{bag.id}: arrives after deadline")
    if route.arrival != legs[-1].arr:
        errs.append(f"{bag.id}: route.arrival inconsistent with last leg")
    for a, b in zip(legs, legs[1:]):
        if a.dest != b.origin:
            errs.append(f"{bag.id}: legs {a.id}->{b.id} are not contiguous")
            continue
        layover = b.dep - a.arr
        if layover < net.min_connection(a.dest):
            errs.append(f"{bag.id}: layover {layover} at {a.dest} below MCT")
        if layover > net.max_layover:
            errs.append(f"{bag.id}: layover {layover} above maximum")
    return errs


def validate_assignment(
    net: Network, bags: Iterable[Bag], result: AssignmentResult
) -> list[str]:
    by_id = {b.id: b for b in bags}
    errs: list[str] = []
    load: Counter[str] = Counter()
    for bag_id, route in result.assigned.items():
        errs.extend(validate_route(net, by_id[bag_id], route))
        load.update(route.legs)
    for fid, n in load.items():
        if n > net.flights[fid].capacity:
            errs.append(f"flight {fid}: {n} bags exceed capacity {net.flights[fid].capacity}")
    missing = set(by_id) - set(result.assigned) - set(result.unassigned)
    if missing:
        errs.append(f"{len(missing)} bags neither assigned nor reported unassigned")
    return errs
