import pytest
from baggage_router import Flight, Network
from helpers import make_net


def test_mct_boundary_is_inclusive():
    g = make_net().graph
    assert "F2" in g["F1"]  # exactly MCT
    assert "F3" not in g["F1"]  # MCT - 1


def test_max_layover_prunes_long_connections():
    g = make_net(max_layover=100).graph  # F4 is 200 min after F1 lands
    assert g["F1"] == ("F2",) or set(g["F1"]) == {"F2"}


def test_no_immediate_u_turn():
    net = Network.from_flights(
        [Flight("X", "A", "H", 0, 60, 1), Flight("Y", "H", "A", 200, 260, 1)], {"H": 30}
    )
    assert net.graph["X"] == ()


def test_duplicate_ids_rejected():
    f = Flight("X", "A", "B", 0, 60, 1)
    with pytest.raises(ValueError):
        Network.from_flights([f, f])


def test_invalid_flight_rejected():
    with pytest.raises(ValueError):
        Flight("bad", "A", "B", 100, 100, 1)
