"""Customer form (no AI): the buyer downloads a plain-text form, the customer returns it filled in, and each
value must appear in the returned text before it is applied (same rule as the AI path)."""
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app

SRC = Path(__file__).resolve().parents[2] / "app_data"


def _client(tmp_path):
    data = tmp_path / "app_data"
    shutil.copytree(SRC / "seed", data / "seed")
    shutil.copytree(SRC / "inbox", data / "inbox")
    app = create_app(env={"APP_DATA_ROOT": str(data), "APP_EVAL_ROOT_HINT": str(tmp_path / "eval")})
    c = TestClient(app)
    rid = c.post("/rfx/seeded-fallback", json={}).json()["rfx_id"]
    return c, rid


def test_form_download_lists_every_open_field(tmp_path):
    c, rid = _client(tmp_path)
    r = c.get(f"/rfx/{rid}/form")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    for field in ["scope:", "delivery_location:", "dimension_convention:", "validity_days:", "gst_treatment:"]:
        assert field in r.text


def test_returned_form_applies_values_that_appear_in_it(tmp_path):
    c, rid = _client(tmp_path)
    text = "scope: 30 box types, one year\ndelivery_location: Chakan plant, Pune\n# comment\nunit: \n"
    out = c.post(f"/rfx/{rid}/form/apply", json={"text": text}).json()
    assert set(out["applied"]) == {"scope", "delivery_location"}
    assert out["rejected"] == []


def test_empty_form_is_refused(tmp_path):
    c, rid = _client(tmp_path)
    r = c.post(f"/rfx/{rid}/form/apply", json={"text": "scope: \n# nothing filled\n"})
    assert r.status_code == 409
