"""Airline baggage routing optimiser (hub-and-spoke, MCT-aware)."""

from .assignment import AssignmentResult, CapacityTracker, GreedyAssigner
from .graph import Network, build_connection_graph
from .models import Bag, Flight, Route
from .parallel import ParallelRouter
from .routing import BruteForceRouter, DijkstraRouter, RoutingStrategy

__all__ = [
    "AssignmentResult",
    "Bag",
    "BruteForceRouter",
    "CapacityTracker",
    "DijkstraRouter",
    "Flight",
    "GreedyAssigner",
    "Network",
    "ParallelRouter",
    "Route",
    "RoutingStrategy",
    "build_connection_graph",
]
__version__ = "1.0.0"
