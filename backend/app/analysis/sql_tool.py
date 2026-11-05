"""Read-only SQL over approved views (architecture §11.2): one SELECT, only approved views, row limit,
time limit, executed on a read-only connection."""
from __future__ import annotations

import sqlite3
import time
from decimal import Decimal

import sqlglot
from sqlglot import exp

from app.analysis.views import VIEWS

MAX_ROWS = 1000
TIMEOUT_S = 2.0


class SqlRejected(ValueError):
    pass


def check_sql(sql: str) -> str:
    try:
        stmts = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    except sqlglot.errors.ParseError as e:
        raise SqlRejected(f"could not parse SQL: {e}")
    if len(stmts) != 1:
        raise SqlRejected("exactly one statement is allowed")
    stmt = stmts[0]
    if not isinstance(stmt, (exp.Select, exp.Union)):
        raise SqlRejected("only SELECT queries are allowed")
    for node in stmt.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command, exp.Pragma)):
            raise SqlRejected("statement type not allowed")
    ctes = {c.alias_or_name for c in stmt.find_all(exp.CTE)}
    for t in stmt.find_all(exp.Table):
        if t.name not in VIEWS and t.name not in ctes:
            raise SqlRejected(f"table '{t.name}' is not an approved view ({', '.join(VIEWS)})")
    if not stmt.args.get("limit"):
        stmt = stmt.limit(MAX_ROWS)
    return stmt.sql(dialect="sqlite")


def run_sql(db_path: str, sql: str) -> dict:
    safe = check_sql(sql)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    deadline = time.monotonic() + TIMEOUT_S
    conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
    try:
        cur = conn.execute(safe)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchmany(MAX_ROWS)]
    except sqlite3.OperationalError as e:
        raise SqlRejected(f"query failed: {e}")
    finally:
        conn.close()
    return {"sql": safe, "columns": cols, "rows": rows}
