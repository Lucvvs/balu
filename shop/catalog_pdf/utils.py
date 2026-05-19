"""Utilidades de texto y layout Platypus."""
from reportlab.platypus import Table, TableStyle


def format_clp(value: int) -> str:
    return f"${int(value):,}".replace(",", ".")


def truncate(s: str, max_len: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max(0, max_len - 1)].rstrip() + "\u2026"


def esc_xml(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text_wrap_width(inner_w: float) -> float:
    return max(20.0, float(inner_w) - 4.0)


def flowable_height(flowable, wrap_w: float) -> float:
    from shop.catalog_pdf.constants import TEXT_MEASURE_HEIGHT_FUDGE_PT

    _, h = flowable.wrap(wrap_w, 10**6)
    return float(h) + TEXT_MEASURE_HEIGHT_FUDGE_PT


def platypus_height(flowable, width: float) -> float:
    _, h = flowable.wrap(width, 10**7)
    return float(h)


def slot(w: float, h: float, flowable, valign: str = "TOP"):
    t = Table([[flowable]], colWidths=[w], rowHeights=[h])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), valign),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return t
