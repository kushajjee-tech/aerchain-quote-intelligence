from __future__ import annotations

import pytest

from app.db.session import init_db, make_engine, make_session_factory


@pytest.fixture()
def data_root(tmp_path):
    root = tmp_path / "app_data"
    root.mkdir()
    return root


@pytest.fixture()
def session_factory(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(engine)
    return make_session_factory(engine)
