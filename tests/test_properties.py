"""Property-based tests (Hypothesis). Each example is a random mini-network."""

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402

from baggage_router import (  # noqa: E402
    Bag, BruteForceRouter, DijkstraRouter, Flight, GreedyAssigner, Network,
)
from baggage_router.exact import optimal_assignment  # noqa: E402
from baggage_router.validation import validate_assignment, validate_route  # noqa: E402

AIRPORTS = ["A", "B", "C", "H"]


@st.composite
def networks(draw):
    flights = []
    for i in range(draw(st.integers(1, 12))):
        o = draw(st.sampled_from(AIRPORTS))
        d = draw(st.sampled_from([a for a in AIRPORTS if a != o]))
        dep = draw(st.integers(0, 600))
        flights.append(
            Flight(f"F{i}", o, d, dep, dep + draw(st.integers(30, 200)), draw(st.integers(1, 3)))
        )
    return Network.from_flights(flights, {"H": 60}, default_mct=30, max_layover=240)


@st.composite
def bags(draw, max_size=6):
    out = []
    for i in range(draw(st.integers(1, max_size))):
        o = draw(st.sampled_from(AIRPORTS))
        d = draw(st.sampled_from([a for a in AIRPORTS if a != o]))
        ready = draw(st.integers(0, 400))
        out.append(Bag(f"B{i}", o, d, ready, ready + draw(st.integers(0, 1000)), draw(st.integers(0, 2))))
    return out


@settings(max_examples=200, deadline=None)
@given(networks(), bags())
def test_routes_are_contiguous_mct_respecting(net, bag_list):
    big = lambda b: Bag(b.id, b.origin, b.dest, b.ready, 10**6)
    for b in map(big, bag_list):
        r = DijkstraRouter().find_route(net, b)
        if r is not None:
            assert validate_route(net, b, r) == []


@settings(max_examples=200, deadline=None)
@given(networks(), bags())
def test_dijkstra_matches_brute_force(net, bag_list):
    for b in bag_list:
        a = DijkstraRouter().find_route(net, b)
        o = BruteForceRouter().find_route(net, b)
        assert (a is None) == (o is None)
        if a and o:
            assert a.arrival == o.arrival


@settings(max_examples=200, deadline=None)
@given(networks(), bags())
def test_assignment_respects_capacity_deadline_and_accounts_for_every_bag(net, bag_list):
    res = GreedyAssigner(net).assign(bag_list)
    assert validate_assignment(net, bag_list, res) == []


@settings(max_examples=100, deadline=None)
@given(networks(), bags(max_size=5))
def test_greedy_never_exceeds_exact_optimum(net, bag_list):
    assert len(GreedyAssigner(net).assign(bag_list).assigned) <= optimal_assignment(net, bag_list)
