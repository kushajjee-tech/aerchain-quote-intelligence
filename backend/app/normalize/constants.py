"""Versioned engineering constants and product heuristics (PRD §5.11, DL-18).

Every initial value is UNVALIDATED and must be shown as such. Sets are immutable; a trace records the
version and content hash used. Activation of a new version is an audited action (M2b/M5).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal

UNVALIDATED = "UNVALIDATED"
ENG_LABEL = "approximate engineering constant — not validated"
HEUR_LABEL = "product heuristic — not validated"

_V1 = [
    {"key": "takeup.A", "value": "1.50", "unit": "factor", "kind": "engineering"},
    {"key": "takeup.C", "value": "1.45", "unit": "factor", "kind": "engineering"},
    {"key": "takeup.B", "value": "1.35", "unit": "factor", "kind": "engineering"},
    {"key": "takeup.E", "value": "1.25", "unit": "factor", "kind": "engineering"},
    {"key": "rsc.joint_allowance_mm", "value": "35", "unit": "mm", "kind": "engineering"},
    {"key": "tol.gsm_lower_pct", "value": "5", "unit": "%", "kind": "heuristic"},
    {"key": "tol.dims_mm", "value": "2", "unit": "mm", "kind": "heuristic"},
    {"key": "tol.weight_mismatch_pct", "value": "10", "unit": "%", "kind": "heuristic"},
    {"key": "check.unit_suspect_ratio", "value": "20", "unit": "x", "kind": "heuristic"},
    {"key": "check.outlier_low", "value": "0.5", "unit": "x", "kind": "heuristic"},
    {"key": "check.outlier_high", "value": "2", "unit": "x", "kind": "heuristic"},
    {"key": "check.ocr_min_confidence", "value": "80", "unit": "%", "kind": "heuristic"},
]


@dataclass(frozen=True)
class ConstantSet:
    version: str
    constants: tuple[dict, ...]

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(json.dumps(list(self.constants), sort_keys=True).encode()).hexdigest()[:16]

    def get(self, key: str) -> Decimal:
        for c in self.constants:
            if c["key"] == key:
                return Decimal(c["value"])
        raise KeyError(key)

    def label(self, key: str) -> str:
        c = next(c for c in self.constants if c["key"] == key)
        if c.get("validation_status", UNVALIDATED) != UNVALIDATED:
            return "validated"
        return ENG_LABEL if c["kind"] == "engineering" else HEUR_LABEL

    def cite(self, key: str) -> dict:
        return {"key": key, "value": str(self.get(key)), "version": self.version,
                "hash": self.content_hash, "label": self.label(key)}


CONSTANT_SET_V1 = ConstantSet("v1", tuple({**c, "validation_status": UNVALIDATED, "source": "initial default"} for c in _V1))
