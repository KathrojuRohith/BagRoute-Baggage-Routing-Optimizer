from baggage_router import Bag, Flight, Network

# A --F1--> H --F2/F3/F4--> B   (hub MCT = 60)
#   F2 departs exactly 60 after F1 lands (boundary: legal)
#   F3 departs 59 after            (one minute short: illegal)
#   F4 departs much later          (legal fallback)


def make_net(f2_capacity: int = 1, max_layover: int = 480) -> Network:
    flights = [
        Flight("F1", "A", "H", 100, 200, 5),
        Flight("F2", "H", "B", 260, 360, f2_capacity),
        Flight("F3", "H", "B", 259, 359, 5),
        Flight("F4", "H", "B", 400, 500, 5),
    ]
    return Network.from_flights(flights, {"H": 60}, default_mct=45, max_layover=max_layover)


def bag(bag_id: str = "b", deadline: int = 600, ready: int = 0, priority: int = 0) -> Bag:
    return Bag(bag_id, "A", "B", ready, deadline, priority)
