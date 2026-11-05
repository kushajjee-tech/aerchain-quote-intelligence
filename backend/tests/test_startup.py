"""M0: startup isolation check + app factory (architecture §5.1 control 3)."""
import pytest
from fastapi.testclient import TestClient

from app.config import StartupIsolationError, load_settings
from app.main import create_app


def _env(data_root, eval_hint):
    return {"APP_DATA_ROOT": str(data_root), "APP_EVAL_ROOT_HINT": str(eval_hint)}


def test_refuses_when_eval_root_env_set(data_root, tmp_path):
    env = _env(data_root, tmp_path / "eval") | {"EVAL_ROOT": str(tmp_path / "eval")}
    with pytest.raises(StartupIsolationError):
        create_app(env=env)


def test_refuses_when_roots_overlap(tmp_path):
    eval_root = tmp_path / "eval"
    data_root = eval_root / "app_data"
    data_root.mkdir(parents=True)
    with pytest.raises(StartupIsolationError):
        create_app(env=_env(data_root, eval_root))


def test_health_ok(data_root, tmp_path):
    app = create_app(env=_env(data_root, tmp_path / "eval"))
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert load_settings(_env(data_root, tmp_path / "eval")).db_path == data_root.resolve() / "app.db"
