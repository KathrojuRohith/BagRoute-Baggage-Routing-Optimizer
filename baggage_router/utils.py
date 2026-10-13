"""Small cross-cutting helpers: a timing decorator."""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

log = logging.getLogger("baggage_router")
TIMINGS: dict[str, float] = {}  # function name -> seconds taken by the last call


def timed(fn: Callable[P, R]) -> Callable[P, R]:
    """Record wall-clock time of each call in TIMINGS and log it at DEBUG level."""

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            TIMINGS[fn.__qualname__] = elapsed
            log.debug("%s took %.4fs", fn.__qualname__, elapsed)

    return wrapper
