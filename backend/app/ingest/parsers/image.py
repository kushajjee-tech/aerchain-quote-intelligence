"""Image (photo / scan) → EvidenceUnits via the OCR path (architecture §6): find the page, flatten its perspective,
run Tesseract, one unit per OCR line with its mean word confidence. The image is passed to Tesseract on stdin, so
no file is written. There is one read path (OCR) in this build: every price read from an image is single-source
and stays UNRESOLVED until confirmed (see extract.py), never auto-verified."""
from __future__ import annotations

import io
import math
import subprocess

import numpy as np
from PIL import Image

from app.ingest.evidence import EvidenceUnit, ParsedDocument

A4 = math.sqrt(2)


def _corners(img: Image.Image) -> np.ndarray | None:
    g = np.asarray(img.convert("L"), dtype=np.float32)
    mask = g > min(235.0, max(200.0, float(np.percentile(g, 60))))  # page brighter than background; capped for page-filling shots
    ys, xs = np.nonzero(mask)
    if len(xs) < 1000:
        return None
    s, d = xs + ys, xs - ys
    return np.array([(xs[s.argmin()], ys[s.argmin()]), (xs[d.argmax()], ys[d.argmax()]),
                     (xs[s.argmax()], ys[s.argmax()]), (xs[d.argmin()], ys[d.argmin()])], dtype=np.float64)


def flatten(img: Image.Image, width: int = 2480) -> tuple[Image.Image, dict]:
    c = _corners(img)
    if c is None:
        return img.convert("RGB"), {"flattened": False}
    h = int(width * A4)
    dst = np.array([[0, 0], [width, 0], [width, h], [0, h]], dtype=np.float64)
    A, b = [], []
    for (x, y), (u, v) in zip(dst, c):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        b += [u, v]
    coeffs = np.linalg.solve(np.array(A), np.array(b))
    rot = math.degrees(math.atan2(c[1][1] - c[0][1], c[1][0] - c[0][0]))
    return (img.convert("RGB").transform((width, h), Image.PERSPECTIVE, tuple(coeffs), Image.BICUBIC),
            {"flattened": True, "corners": c.round(1).tolist(), "rotation_deg": round(rot, 2)})


def _ocr_lines(img: Image.Image) -> list[tuple[str, float]]:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    out = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "6", "-l", "eng", "tsv"],
                         input=buf.getvalue(), capture_output=True, check=True).stdout.decode("utf-8", "replace")
    lines: dict[tuple, list] = {}
    for row in out.splitlines()[1:]:
        f = row.split("\t")
        if len(f) < 12 or f[0] != "5" or not f[11].strip():
            continue
        key = (int(f[2]), int(f[3]), int(f[4]))  # block, paragraph, line
        lines.setdefault(key, []).append((f[11], float(f[10])))
    return [(" ".join(w for w, _ in ws), sum(c for _, c in ws) / len(ws)) for _, ws in sorted(lines.items())]


def parse_image(ref: str, filename: str, data: bytes, mime: str) -> ParsedDocument:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as e:
        return ParsedDocument(ref, filename, mime, "image", data=data, parse_status="failed", failure_reason=f"unreadable image: {e}")
    flat, meta = flatten(img)
    try:
        lines = _ocr_lines(flat)
    except FileNotFoundError:
        return ParsedDocument(ref, filename, mime, "image", data=data, parse_status="deferred",
                              failure_reason="OCR engine (tesseract) not installed", meta=meta)
    units = [EvidenceUnit(f"{ref}:o{i}", ref, "ocr_line", {"line": i, "ocr_conf": round(conf, 1)}, text)
             for i, (text, conf) in enumerate(lines, start=1)]
    meta |= {"path": "OCR", "ocr_lines": len(units),
             "mean_conf": round(sum(u.locator["ocr_conf"] for u in units) / len(units), 1) if units else 0}
    if not units:
        return ParsedDocument(ref, filename, mime, "image", data=data, parse_status="failed",
                              failure_reason="OCR found no text", meta=meta)
    return ParsedDocument(ref, filename, mime, "image", units=units, data=data, meta=meta)
