"""M3a: eml + xlsx parsers produce citable EvidenceUnits with correct locators."""
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.ingest.parsers import XLSX_MIME, parse_message
from app.ingest.parsers.xlsx import display, parse_xlsx

INBOX = Path(__file__).resolve().parents[2] / "app_data" / "inbox"
SENTENCE = "₹42/kg for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra."


def _xlsx() -> bytes:
    wb = Workbook(); ws = wb.active; ws.title = "Quotation"
    ws.merge_cells("A1:C1"); ws["A1"] = "ACME CORRUGATORS"
    ws.append(["Sr", "Code", "Rate"]); ws.append([1, "SKU-1", 10.37]); ws.append([2, "SKU-2", 42000.0])
    bio = BytesIO(); wb.save(bio); return bio.getvalue()


def test_display_formatting():
    assert display(42000.0) == "42000" and display(10.37) == "10.37" and display(7) == "7"


def test_xlsx_units_and_locators():
    doc = parse_xlsx("D2", "q.xlsx", _xlsx(), XLSX_MIME)
    by_id = {u.id: u for u in doc.units}
    assert by_id["D2:Quotation!A1"].locator["merged"] == "A1:C1"
    assert by_id["D2:Quotation!C3"].text == "10.37" and by_id["D2:Quotation!C4"].text == "42000"
    assert by_id["D2:Quotation!B3"].locator == {"sheet": "Quotation", "cell": "B3", "row": 3, "col": 2}


def test_corrupt_xlsx_fails_visibly():
    doc = parse_xlsx("D2", "bad.xlsx", b"not a workbook", XLSX_MIME)
    assert doc.parse_status == "failed" and doc.failure_reason and not doc.units


def test_eml_body_lines_and_attachments():
    m = EmailMessage(); m["From"] = "v@x.example"; m["Subject"] = "Quote"; m["Message-ID"] = "<1@x>"
    m.set_content("Line one\n\nLine three ₹42/kg")
    m.add_attachment(_xlsx(), maintype="application", subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="q.xlsx")
    m.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf", filename="cert.pdf")
    msg, docs = parse_message(m.as_bytes())
    assert [u.id for u in docs[0].units] == ["D1:l1", "D1:l3"] and docs[0].units[1].text == "Line three ₹42/kg"
    assert docs[1].kind == "xlsx" and docs[1].parse_status == "parsed"
    assert docs[2].kind == "pdf" and docs[2].parse_status == "failed" and docs[2].failure_reason  # never silently empty


@pytest.mark.skipif(not (INBOX / "01_V5_quote.eml").exists(), reason="M1a dataset not generated")
def test_generated_inbox_parses():
    _, v5 = parse_message((INBOX / "01_V5_quote.eml").read_bytes())
    assert len(v5) == 1 and [u.text for u in v5[0].units] == [SENTENCE]
    _, v1 = parse_message((INBOX / "03_V1_quotation.eml").read_bytes())
    xlsx = v1[1]
    assert xlsx.kind == "xlsx" and any(u.text == "PK-C101" for u in xlsx.units)
    assert {u.locator["sheet"] for u in xlsx.units} == {"Quotation", "Supplier Questionnaire"}
    pdfs = v1[2:]
    assert all(d.kind == "pdf" and d.parse_status == "parsed" for d in pdfs)
    iso = next(d for d in pdfs if "ISO" in d.filename)
    texts = [u.text for u in iso.units]
    assert "Certificate of Registration" in texts  # NFKC folds the 'ﬁ' ligature
    assert any(t.startswith("Valid until") for t in texts) and iso.units[0].id == "D3:p1l1"


def test_docx_paragraphs_and_tables():
    import io
    import docx
    from app.ingest.parsers.docx_ import parse_docx
    d = docx.Document(); d.add_paragraph("QC-01 — ISO 9001"); d.add_paragraph(""); t = d.add_table(rows=1, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "Q1", "Yes"
    buf = io.BytesIO(); d.save(buf)
    doc = parse_docx("D2", "q.docx", buf.getvalue())
    assert [(u.id, u.text) for u in doc.units] == [("D2:p1", "QC-01 — ISO 9001"), ("D2:t1r1c1", "Q1"), ("D2:t1r1c2", "Yes")]
    assert parse_docx("D2", "bad.docx", b"nope").parse_status == "failed"


def test_scanned_pdf_is_deferred_not_empty():
    from pypdf import PdfWriter
    import io
    from app.ingest.parsers.pdf import parse_pdf
    w = PdfWriter(); w.add_blank_page(width=200, height=200); buf = io.BytesIO(); w.write(buf)
    doc = parse_pdf("D4", "scan.pdf", buf.getvalue())
    assert doc.parse_status == "deferred" and "OCR" in doc.failure_reason


def test_photo_is_flattened_and_ocr_read_on_stdin():
    """M3b (OCR path): a rotated page on a dark background is found, flattened and read; one unit per OCR line."""
    import io, shutil
    from PIL import Image, ImageDraw, ImageFont
    from app.ingest.parsers.image import parse_image
    if shutil.which("tesseract") is None:
        pytest.skip("tesseract not installed")
    page = Image.new("RGB", (900, 1270), "white")
    d = ImageDraw.Draw(page)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
    except OSError:
        font = ImageFont.load_default()
    for i, t in enumerate(["RATE LIST", "Box 250x200x150   671", "Box 300x250x200   982"]):
        d.text((80, 120 + i * 80), t, fill="black", font=font)
    bg = Image.new("RGB", (1400, 1500), (120, 105, 85))
    bg.paste(page.rotate(4, expand=True, fillcolor=(120, 105, 85)), (200, 60))
    buf = io.BytesIO(); bg.save(buf, format="JPEG")
    doc = parse_image("D2", "card.jpg", buf.getvalue(), "image/jpeg")
    text = " ".join(u.text for u in doc.units)
    assert doc.parse_status == "parsed" and doc.meta["flattened"] and doc.meta["path"] == "OCR"
    assert "RATE LIST" in text and "671" in text and all(u.kind == "ocr_line" and "ocr_conf" in u.locator for u in doc.units)
    assert parse_image("D2", "bad.jpg", b"not an image", "image/jpeg").parse_status == "failed"
