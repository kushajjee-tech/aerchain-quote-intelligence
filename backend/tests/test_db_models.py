"""M0: schema creates, core round trips, append-only tables enforced in the database."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from app.db.models import AuditEvent, Base, BaselinePrice, Rfx, RfxLine, Vendor


def test_all_tables_created(session_factory):
    with session_factory() as s:
        names = {r[0] for r in s.execute(text("select name from sqlite_master where type='table'"))}
    assert set(Base.metadata.tables) <= names


def test_round_trip_core_entities(session_factory):
    with session_factory.begin() as s:
        rfx = Rfx(title="t", kind="primary", origin="COPILOT_LIVE", response_basis={"gst_treatment": "ex"})
        s.add(rfx)
        s.flush()
        s.add(RfxLine(rfx_id=rfx.id, line_no=1, sku_code="S1", description="box", item_type="RSC",
                      dims_mm={"L": 1, "W": 2, "H": 3}, ply=3, flute_profile="B",
                      layers=[{"role": "liner", "gsm": 150}], annual_qty=10, reference_unit_weight_g="123.0",
                      reference_weight_source="IM-1", food_contact=True))
        s.add(Vendor(name="V", contact_email="v@x"))
        s.add(BaselinePrice(rfx_line_sku="S1", vendor_name="V", unit_price_inr_ex_gst="10.0000",
                            freight_basis="INCLUDED", spec_signature="sig", period="FY25", awarded=True, source="contract"))
    with session_factory() as s:
        line = s.query(RfxLine).one()
        assert line.dims_mm == {"L": 1, "W": 2, "H": 3} and line.food_contact is True
        assert s.query(BaselinePrice).one().unit_price_inr_ex_gst == "10.0000"


@pytest.mark.parametrize("stmt", ["update audit_event set actor='x'", "delete from audit_event"])
def test_audit_event_append_only(session_factory, stmt):
    with session_factory.begin() as s:
        s.add(AuditEvent(actor="buyer", action="TEST", target={"x": 1}))
    with pytest.raises(DatabaseError):
        with session_factory.begin() as s:
            s.execute(text(stmt))


def test_stale_schema_refuses_to_start_with_clear_message(tmp_path):
    import pytest
    from sqlalchemy import text
    from app.db.session import SchemaOutOfDate, init_db, make_engine
    engine = make_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as c:  # a database created by an older build
        c.execute(text("CREATE TABLE rfx (id INTEGER PRIMARY KEY, title VARCHAR)"))
    with pytest.raises(SchemaOutOfDate, match="make reset"):
        init_db(engine)
    fresh = make_engine(f"sqlite:///{tmp_path / 'new.db'}")
    init_db(fresh)
    init_db(fresh)  # idempotent on a current schema
