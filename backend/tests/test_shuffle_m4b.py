"""IA-06 (FN-07, MAT-1 AC, EDGE-01): shuffling the data rows of V1's own-layout sheet produces identical
matches and identical normalised cells. Lines are matched by item code / spec, never by row position."""
import io
import json
import random

import pytest
from openpyxl import load_workbook

from app.ingest.extract import TextExtractionResult
from app.ingest.parsers import parse_message
from app.ingest.parsers.xlsx import parse_xlsx
from app.ingest.schemas import DocumentExtraction
from app.ingest.verify import check_evidence, verify_line
from app.normalize.constants import CONSTANT_SET_V1
from app.process.phase_a import phase_a
from tests.test_slice_t_slice_01 import SRC, v1_extraction_from

pytestmark = pytest.mark.skipif(not (SRC / "inbox/03_V1_quotation.eml").exists(), reason="M1a dataset not generated")


def _rfx():
    canon = json.loads((SRC / "seed/canonical_rfx.json").read_text())
    return {"response_basis": {"gst_treatment": canon["response_basis"]["gst_treatment"]}, "questionnaire": [],
            "lines": canon["lines"]}


def _shuffled(xlsx: bytes, seed: int) -> bytes:
    wb = load_workbook(io.BytesIO(xlsx))
    ws = wb["Quotation"]
    data_rows = [r for r in range(1, ws.max_row + 1) if str(ws.cell(r, 3).value or "").startswith("PK-")]
    values = [[ws.cell(r, c).value for c in range(1, ws.max_column + 1)] for r in data_rows]
    order = list(range(len(values)))
    random.Random(seed).shuffle(order)
    assert order != sorted(order)
    for r, i in zip(data_rows, order):
        for c, v in enumerate(values[i], start=1):
            ws.cell(r, c).value = v
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _cells(docs):
    ex = DocumentExtraction.model_validate(v1_extraction_from(docs))
    units = {u.id: u for d in docs for u in d.units}
    res = TextExtractionResult(ex, [verify_line(l, units) for l in ex.line_quotes],
                               [check_evidence(t.evidence, units).reasons for t in ex.document_terms], [], units,
                               {d.ref: d.filename for d in docs})
    out = phase_a(_rfx(), [res], vendor_name="Deccan Kraft & Board Pvt. Ltd.", constants=CONSTANT_SET_V1)
    return {c.line_no: (str(c.cell.unit_price_inr_ex_gst), str(c.cell.unit_status), c.cell.reasons, c.match_how) for c in out}


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_row_shuffle_gives_identical_matches(seed):
    _, docs = parse_message((SRC / "inbox/03_V1_quotation.eml").read_bytes())
    original = _cells(docs)
    xlsx = docs[1]
    shuffled_doc = parse_xlsx(xlsx.ref, xlsx.filename, _shuffled(xlsx.data, seed), xlsx.mime)
    shuffled = _cells([docs[0], shuffled_doc] + docs[2:])
    assert shuffled == original
    priced = [n for n, c in original.items() if c[0] != "None"]
    assert len(priced) >= 25 and all(original[n][3] == "item_code" for n in priced)
