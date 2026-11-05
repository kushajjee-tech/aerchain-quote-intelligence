"""GST treatment (PRD NRM-6, DL-26): silent → RFx basis as a disclosed assumption; undefined basis or
ambiguous statement → UNRESOLVED (GST_UNCLEAR). Nothing is assumed silently."""
from __future__ import annotations


def gst_reasons(gst_statement: str, rfx_gst_basis: str | None, stated_exclusive: bool | None = None) -> tuple[list[str], dict]:
    if gst_statement == "AMBIGUOUS":
        return ["GST_UNCLEAR"], {"step": "gst", "label": "vendor GST statement ambiguous"}
    if gst_statement == "SILENT":
        if rfx_gst_basis:
            return ["GST_PER_RFX_BASIS"], {"step": "gst", "label": f"vendor silent; RFx basis applied: {rfx_gst_basis}"}
        return ["GST_UNCLEAR"], {"step": "gst", "label": "vendor silent and the RFx defines no GST basis"}
    if stated_exclusive is False:
        return ["GST_UNCLEAR"], {"step": "gst", "label": "GST-inclusive price without a stated rate (M2b: back-out)"}
    return [], {"step": "gst", "label": "stated exclusive of GST"}
