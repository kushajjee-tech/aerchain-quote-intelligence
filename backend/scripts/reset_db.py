"""`make reset`: recreate the app database (schema only in M0; seed loading arrives with M1/M6)."""
from __future__ import annotations

from app.config import load_settings, startup_check
from app.db.session import init_db, make_engine
from app.storage import Storage

settings = load_settings()
startup_check(settings)
storage = Storage(settings.data_root)
if storage.exists("app.db"):
    storage.safe_path("app.db").unlink()
init_db(make_engine(settings.db_url))
print(f"database reset at {settings.db_path}")
