"""Immutable domain model. All times are integer minutes from the start of the schedule day."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Flight:
    id: str
    origin: str
    dest: str
    dep: int
    arr: int
    capacity: int  # number of bags the hold can take

    def __post_init__(self) -> None:
        if self.origin == self.dest:
            raise ValueError(f"flight {self.id}: origin equals destination")
        if self.arr <= self.dep:
            raise ValueError(f"flight {self.id}: arrival must be after departure")
        if self.capacity < 0:
            raise ValueError(f"flight {self.id}: negative capacity")


@dataclass(frozen=True, slots=True)
class Bag:
    id: str
    origin: str
    dest: str
    ready: int  # check-in complete: earliest it can be loaded
    deadline: int  # latest acceptable arrival at destination
    priority: int = 0  # higher wins ties on equal slack

    def __post_init__(self) -> None:
        if self.origin == self.dest:
            raise ValueError(f"bag {self.id}: origin equals destination")
        if self.deadline < self.ready:
            raise ValueError(f"bag {self.id}: deadline before ready time")


@dataclass(frozen=True, slots=True)
class Route:
    bag_id: str
    legs: tuple[str, ...]  # flight ids in order
    arrival: int

    @property
    def connections(self) -> int:
        return len(self.legs) - 1
