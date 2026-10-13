from baggage_router import Network, ParallelRouter
from baggage_router.synthetic import default_mct, generate_bags, generate_flights


def test_parallel_matches_sequential():
    flights = generate_flights(hubs=2, spokes_per_hub=4, waves=4, seed=3)
    net = Network.from_flights(flights, default_mct(flights))
    bags = generate_bags(flights, 150, seed=3)
    with ParallelRouter(net, workers=1) as seq:
        expected = seq.route_all(bags)
    with ParallelRouter(net, workers=2) as par:
        actual = par.route_all(bags)
    assert actual == expected
