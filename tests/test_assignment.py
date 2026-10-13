from baggage_router import GreedyAssigner
from baggage_router.exact import optimal_assignment
from baggage_router.validation import validate_assignment
from helpers import bag, make_net


def test_tight_slack_bag_gets_scarce_seat_regardless_of_input_order():
    net = make_net(f2_capacity=1)
    bags = [bag("loose", deadline=600), bag("tight", deadline=400)]
    res = GreedyAssigner(net).assign(bags)
    assert res.assigned["tight"].legs == ("F1", "F2")
    assert res.assigned["loose"].legs == ("F1", "F4")
    assert res.rerouted == 1
    assert validate_assignment(net, bags, res) == []


def test_bag_unassigned_when_capacity_exhausted_and_no_slack():
    net = make_net(f2_capacity=1)
    bags = [bag("tight", deadline=400), bag("also_tight", deadline=450)]
    res = GreedyAssigner(net).assign(bags)
    assert len(res.assigned) == 1
    assert res.unassigned["also_tight"] == "capacity exhausted"


def test_infeasible_bag_reported_not_dropped():
    net = make_net()
    res = GreedyAssigner(net).assign([bag("late", deadline=300), bag("missed", ready=150)])
    assert res.unassigned["late"] == "earliest arrival misses deadline"
    assert res.unassigned["missed"] == "no connecting route"


def test_priority_breaks_slack_ties():
    net = make_net(f2_capacity=1)
    bags = [bag("lo", deadline=400, priority=0), bag("hi", deadline=400, priority=2)]
    res = GreedyAssigner(net).assign(bags)
    assert "hi" in res.assigned and "lo" in res.unassigned


def test_greedy_never_beats_exact():
    net = make_net(f2_capacity=1)
    bags = [bag("a", deadline=400), bag("b", deadline=600), bag("c", deadline=450)]
    assert len(GreedyAssigner(net).assign(bags).assigned) <= optimal_assignment(net, bags)


def test_greedy_is_suboptimal_on_known_counterexample():
    """Defence exhibit: the tightest-slack bag hogs two scarce seats and blocks two others.

    Greedy delivers 1 bag; the optimum is 2 (the A->H bag and the H->B bag).
    """
    from baggage_router import Bag, Flight, Network

    net = Network.from_flights(
        [Flight("F1", "A", "H", 100, 200, 1), Flight("F2", "H", "B", 260, 360, 1)], {"H": 60}
    )
    bags = [
        Bag("through", "A", "B", 0, 360),  # slack 0 -> processed first, takes F1 and F2
        Bag("feeder", "A", "H", 0, 1000),
        Bag("onward", "H", "B", 0, 1000),
    ]
    assert len(GreedyAssigner(net).assign(bags).assigned) == 1
    assert optimal_assignment(net, bags) == 2
