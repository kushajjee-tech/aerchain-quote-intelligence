"""Spec comparison (MAT-3, DL-6): COMPLIANT / ALTERNATE (differences listed) / NOT_RESTATED.
Tolerances come from the active constant set and are cited in each difference."""
from __future__ import annotations

import re

from app.ingest.schemas import SpecStated
from app.normalize.constants import CONSTANT_SET_V1, ConstantSet


def _dims(text: str | None) -> tuple[int, ...] | None:
    m = re.search(r"(\d{2,4})\s*[x×*]\s*(\d{2,4})(?:\s*[x×*]\s*(\d{2,4}))?", text or "")
    return tuple(int(x) for x in m.groups() if x) if m else None


def spec_diff(line: dict, spec: SpecStated | None, cs: ConstantSet = CONSTANT_SET_V1) -> tuple[str, list[dict]]:
    if spec is None or not any([spec.ply, spec.flute_profile, spec.dims_as_stated, spec.layer_gsm, spec.bf_as_stated]):
        return "NOT_RESTATED", []
    diffs = []
    if spec.ply is not None and spec.ply != line["ply"]:
        diffs.append({"field": "ply", "rfx": line["ply"], "vendor": spec.ply})
    if spec.flute_profile and line.get("flute_profile") and spec.flute_profile.replace(" ", "").upper() != line["flute_profile"].upper():
        diffs.append({"field": "flute_profile", "rfx": line["flute_profile"], "vendor": spec.flute_profile})
    tol = cs.get("tol.dims_mm")
    d, rd = _dims(spec.dims_as_stated), line.get("dims_mm") or {}
    want = tuple(v for v in (rd.get("L"), rd.get("W"), rd.get("H")) if v is not None)
    if d is not None and want:
        if len(d) != len(want) or any(abs(a - b) > tol for a, b in zip(d, want)):
            diffs.append({"field": "dims_mm", "rfx": "x".join(map(str, want)), "vendor": "x".join(map(str, d)),
                          "tolerance": cs.cite("tol.dims_mm")})
    layers = line.get("layers") or []
    pct = cs.get("tol.gsm_lower_pct")
    if spec.layer_gsm and layers:
        if len(spec.layer_gsm) != len(layers):
            diffs.append({"field": "layer_count", "rfx": len(layers), "vendor": len(spec.layer_gsm)})
        else:
            for i, (v, l) in enumerate(zip(spec.layer_gsm, layers), start=1):
                if l.get("gsm") and v < l["gsm"] * (1 - pct / 100):
                    diffs.append({"field": f"gsm_layer_{i}", "rfx": l["gsm"], "vendor": v, "tolerance": cs.cite("tol.gsm_lower_pct")})
    if spec.bf_as_stated and layers:
        stated = [int(x) for x in re.findall(r"\d+", spec.bf_as_stated)]
        need = [l.get("bf") for l in layers]
        if stated and len(stated) == len(need):  # one BF per layer: compare layer by layer
            for i, (v, n) in enumerate(zip(stated, need), start=1):
                if n and v < n:
                    diffs.append({"field": f"bf_layer_{i}", "rfx": n, "vendor": v})
        elif stated and any(need):  # a single board BF: must meet the strictest layer
            if min(stated) < max(n for n in need if n):
                diffs.append({"field": "bf", "rfx": max(n for n in need if n), "vendor": min(stated)})
    return ("ALTERNATE" if diffs else "COMPLIANT"), diffs
