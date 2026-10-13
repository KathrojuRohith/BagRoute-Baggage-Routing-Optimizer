# Specification (written before the code)

**Input.** `flights.csv` (id, origin, dest, dep, arr, capacity), `bags.csv` (id, origin, dest,
ready, deadline, priority). Times are integer minutes or `HH:MM`. MCT per airport with a default.

**Output.** For each bag either an itinerary (ordered flight ids + arrival time) or an
UNASSIGNED reason: `no connecting route`, `earliest arrival misses deadline`, `capacity exhausted`.

**Hard invariants** (checked independently by `validation.py`, asserted by the tests):
1. Legs are contiguous: `legs[i].dest == legs[i+1].origin`; first leg leaves the bag's origin, last reaches its destination.
2. For every connection: `MCT(airport) <= next.dep - prev.arr <= max_layover`.
3. First departure >= bag ready time; final arrival <= bag deadline.
4. Bags assigned to a flight <= its capacity.
5. Every bag is either assigned or reported unassigned (nothing silently dropped).

**Non-goals.** Real-time disruptions, interline/terminal-level MCT, bag weight/volume.
