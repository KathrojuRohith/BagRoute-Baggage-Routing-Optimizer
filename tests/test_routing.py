from baggage_router import BruteForceRouter, DijkstraRouter
from helpers import bag, make_net


def test_earliest_route_respects_mct():
    r = DijkstraRouter().find_route(make_net(), bag())
    assert r is not None and r.legs == ("F1", "F2") and r.arrival == 360 and r.connections == 1


def test_blocked_flight_forces_alternative():
    r = DijkstraRouter().find_route(make_net(), bag(), frozenset({"F2"}))
    assert r is not None and r.legs == ("F1", "F4")


def test_no_route_when_bag_misses_first_flight():
    assert DijkstraRouter().find_route(make_net(), bag(ready=101)) is None


def test_no_route_when_everything_blocked():
    assert DijkstraRouter().find_route(make_net(), bag(), frozenset({"F2", "F4"})) is None


def test_dijkstra_matches_oracle_on_fixture():
    net = make_net()
    for blocked in (frozenset(), frozenset({"F2"}), frozenset({"F1"})):
        a = DijkstraRouter().find_route(net, bag(), blocked)
        b = BruteForceRouter().find_route(net, bag(), blocked)
        assert (a and a.arrival) == (b and b.arrival)
