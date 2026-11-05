"""M5b settings: FX rate edits (DL-15/30, EDGE-08) and audited constant-set versions (DL-18, PRD §5.11)
re-normalise stored Phase A inputs and recompute globally (VAL-5), with no re-read and no model call."""
from decimal import Decimal

from app.db.models import LlmCall
from app.normalize.constants import CONSTANT_SET_V1
from app.normalize.engine import QuoteInput, ResponseContext
from app.process.cells_io import ctx_to_json, input_to_json
from app.process.phase_a import cell_from_inputs
from app.process.recompute import store_phase_a
from app.process.run import recompute_rfx
from tests.test_resolutions_m2b import LINE, _grid, _resolve, setup
from tests.test_review_m5b import processed  # noqa: F401

CTX = ctx_to_json(ResponseContext(gst_statement="STATED", gst_stated_exclusive=True))


def _inputs(value, currency="INR"):
    return {"line": {**LINE, "line_no": 3}, "q": input_to_json(QuoteInput(value=Decimal(value), unit_class="PER_BOX", currency=currency)),
            "ctx": CTX, "pre_trace": []}


def test_fx_rate_set_renormalises_and_flags_accepted_value(tmp_path):
    c, sf, st, rid, vid = setup(tmp_path)
    inp = _inputs("0.12", "USD")  # V2 quotes line 3 in USD
    store_phase_a(sf, rid, {str(vid["V2"]): {3: cell_from_inputs(inp, {}, CONSTANT_SET_V1)}},
                  {str(vid["V2"]): {3: inp}})
    recompute_rfx(sf, st, rid)
    cell = _grid(c, rid)[3][str(vid["V2"])]
    assert cell["status"] == "UNRESOLVED" and "FX_RATE_MISSING" in cell["reasons"]   # never a silent conversion
    with sf() as s:
        calls = s.query(LlmCall).count()
    assert c.put("/settings/fx/USD", json={"rate_to_inr": "84.00", "as_of": "2026-11-01", "source": "RBI reference"}).status_code == 200
    cell = _grid(c, rid)[3][str(vid["V2"])]
    assert cell["value"] == "10.0800" and cell["status"] == "ASSUMED" and "FX_RATE" in cell["reasons"] and "FX" in cell["flags"]
    prov = c.get(f"/rfx/{rid}/cells/{vid['V2']}/3").json()
    fx = next(t for t in prov["trace"] if t["step"] == "fx")
    assert fx["original"] == "0.1200" and fx["rate"] == "84.00" and fx["source"] == "RBI reference"  # original kept (EDGE-08)
    assert _resolve(c, rid, vendor_id=vid["V2"], line_no=3, type="ACCEPT").status_code == 200
    c.put("/settings/fx/USD", json={"rate_to_inr": "86.00", "as_of": "2026-11-04", "source": "RBI reference"})
    cell = _grid(c, rid)[3][str(vid["V2"])]
    assert cell["value"] == "10.3200" and cell["status"] == "ASSUMED"                 # resolution sticks...
    assert "NEW_WARNING_AFTER_REVIEW" in cell["flags"] and "VALUE_CHANGED_AFTER_REVIEW" in cell["reasons"]  # ...but is flagged
    with sf() as s:
        assert s.query(LlmCall).count() == calls                                    # no re-read, no model call
    actions = [e["action"] for e in c.get(f"/rfx/{rid}/audit").json()]
    assert "RECOMPUTE" in actions
    assert c.put("/settings/fx/USD", json={"rate_to_inr": "-1", "as_of": "x", "source": "y"}).status_code == 422


def test_constant_set_version_activation(processed):
    c, app, rid, v1, v5 = processed
    before = c.get(f"/rfx/{rid}/cells/{v5}/6").json()
    assert "WEIGHT_ESTIMATED" in before["cell"]["reasons"] and before["cell"]["constant_set_version"] == "v1"
    sets = c.get("/settings/constants").json()
    assert [s["version"] for s in sets] == ["v1"] and all(x["label"].endswith("not validated") for x in sets[0]["constants"])
    r = c.post("/settings/constants", json={"base_version": "v1", "new_version": "v2", "changes": {"takeup.C": "1.55"},
                                            "reason": "plant QA sample, Nov 2026"})
    assert r.status_code == 200
    assert c.post("/settings/constants", json={"base_version": "v1", "new_version": "v2", "changes": {},
                                               "reason": "x"}).status_code == 422          # versions are immutable
    assert c.post("/settings/constants", json={"base_version": "v1", "new_version": "v3", "changes": {"nope": "1"},
                                               "reason": "x"}).status_code == 422
    assert c.get(f"/rfx/{rid}/cells/{v5}/6").json()["cell"]["value"] == before["cell"]["value"]  # created ≠ active
    assert c.post("/settings/constants/v2/activate", json={"reason": "QA sign-off"}).status_code == 200
    after = c.get(f"/rfx/{rid}/cells/{v5}/6").json()
    assert after["cell"]["constant_set_version"] == "v2"
    assert Decimal(after["cell"]["weight_g"]) > Decimal(before["cell"]["weight_g"])
    assert Decimal(after["cell"]["value"]) > Decimal(before["cell"]["value"])
    cited = [x for t in after["trace"] for x in t.get("constants", []) if x.get("key") == "takeup.C"]
    assert cited and cited[0]["version"] == "v2" and cited[0]["value"] == "1.55"
    actions = [e["action"] for e in c.get(f"/rfx/{rid}/audit").json()]
    assert "RECOMPUTE" in actions
    with app.state.session_factory() as s:
        from app.db.models import AuditEvent
        assert {"CONSTANT_SET_CREATED", "CONSTANT_SET_ACTIVATED"} <= {e.action for e in s.query(AuditEvent).all()}
    assert c.post("/settings/constants/v1/activate", json={"reason": "rollback"}).status_code == 200
    assert c.get(f"/rfx/{rid}/cells/{v5}/6").json()["cell"]["value"] == before["cell"]["value"]  # deterministic
