from baggage_router.io import chunked, iter_bags, parse_time, read_flights, write_bags, write_flights
from baggage_router.synthetic import generate_bags, generate_flights


def test_parse_time_accepts_clock_and_minutes():
    assert parse_time("08:30") == 510 and parse_time("510") == 510


def test_chunked_is_lazy_and_complete():
    assert list(chunked(range(5), 2)) == [[0, 1], [2, 3], [4]]


def test_csv_round_trip(tmp_path):
    flights = generate_flights(hubs=1, spokes_per_hub=3, waves=2)
    bags = generate_bags(flights, 10)
    write_flights(flights, tmp_path / "f.csv")
    write_bags(bags, tmp_path / "b.csv")
    assert read_flights(tmp_path / "f.csv") == flights
    assert list(iter_bags(tmp_path / "b.csv")) == bags
