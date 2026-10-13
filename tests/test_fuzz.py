"""Dependency-free randomized checks of the same invariants as test_properties.py."""

from random import Random

from baggage_router import Bag, BruteForceRouter, DijkstraRouter, Flight, GreedyAssigner, Network
from baggage_router.exact import optimal_assignment
from baggage_router.validation import validate_assignment, validate_route

AIRPORTS = ["A", "B", "C", "H"]


def random_case(seed: int, max_bags: int = 6) -> tuple[Network, list[Bag]]:
    rng = Random(seed)
    flights = []
    for i in range(rng.randint(1, 12)):
        o = rng.choice(AIRPORTS)
        d = rng.choice([a for a in AIRPORTS if a != o])
        dep = rng.randint(0, 600)
        flights.append(Flight(f"F{i}", o, d, dep, dep + rng.randint(30, 200), rng.randint(1, 3)))
    net = Network.from_flights(flights, {"H": 60}, default_mct=30, max_layover=240)
    bags = []
    for i in range(rng.randint(1, max_bags)):
        o = rng.choice(AIRPORTS)
        d = rng.choice([a for a in AIRPORTS if a != o])
        ready = rng.randint(0, 400)
        bags.append(Bag(f"B{i}", o, d, ready, ready + rng.randint(0, 1000), rng.randint(0, 2)))
    return net, bags


def test_dijkstra_matches_brute_force_and_routes_are_valid():
    for seed in range(400):
        net, bags = random_case(seed)
        for b in bags:
            a = DijkstraRouter().find_route(net, b)
            o = BruteForceRouter().find_route(net, b)
            assert (a is None) == (o is None), seed
            if a and o:
                assert a.arrival == o.arrival, seed
                relaxed = Bag(b.id, b.origin, b.dest, b.ready, 10**6)
                assert validate_route(net, relaxed, a) == [], seed


def test_assignment_invariants_and_greedy_bounded_by_exact():
    for seed in range(400):
        net, bags = random_case(seed, max_bags=5)
        res = GreedyAssigner(net).assign(bags)
        assert validate_assignment(net, bags, res) == [], seed
        assert len(res.assigned) <= optimal_assignment(net, bags), seed
