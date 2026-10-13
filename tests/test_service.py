import json
import threading
import urllib.error
import urllib.request

import pytest
from baggage_router.server import make_server
from baggage_router.service import network_info, plan


def test_plan_is_consistent_and_violation_free():
    out = plan({"bags": 300, "seed": 2})
    s = out["summary"]
    assert s["violations"] == 0
    assert s["assigned"] + s["unassigned"] == 300 == len(out["bags"])
    assert all(f["load"] <= f["cap"] for f in out["flights"])
    assert sum(s["reasons"].values()) == s["unassigned"]


def test_airports_carry_real_coordinates():
    airports = network_info()["airports"]
    assert len({a["iata"] for a in airports}) == len(airports) == 21
    assert all(6 < a["lat"] < 36 and 68 < a["lon"] < 98 for a in airports)


def test_cancelled_flights_are_removed_and_never_used():
    gone = [f["id"] for f in network_info()["flights"][:40]]
    out = plan({"bags": 300, "cancelled": gone})
    ids = {f["id"] for f in out["flights"]}
    assert not ids & set(gone)
    assert all(not set(b["legs"]) & set(gone) for b in out["bags"])


def test_lower_capacity_never_improves_delivery():
    roomy = plan({"bags": 600, "capacity_scale": 2.0})["summary"]["assigned"]
    tight = plan({"bags": 600, "capacity_scale": 0.4})["summary"]["assigned"]
    assert tight <= roomy


@pytest.mark.parametrize("bad", [{"bags": 0}, {"bags": "x"}, {"hub_mct": -1}, {"cancelled": "F1"}])
def test_invalid_parameters_rejected(bad):
    with pytest.raises(ValueError):
        plan(bad)


def test_http_api_round_trip():
    srv = make_server("127.0.0.1", 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    try:
        assert b"BagRoute" in urllib.request.urlopen(base + "/").read()
        assert json.load(urllib.request.urlopen(base + "/api/health"))["status"] == "ok"
        req = urllib.request.Request(
            base + "/api/plan", data=json.dumps({"bags": 100}).encode(),
            headers={"Content-Type": "application/json"},
        )
        assert json.load(urllib.request.urlopen(req))["summary"]["bags"] == 100
        bad = urllib.request.Request(base + "/api/plan", data=b'{"bags": -5}')
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(bad)
        assert err.value.code == 400
    finally:
        srv.shutdown()
        srv.server_close()
