"""Variantes: muestras de color, chips de talla."""
from __future__ import annotations

import re

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth as rl_string_width
from reportlab.platypus import Flowable, Spacer, Table, TableStyle

from shop.catalog_pdf.constants import (
    CARD_ROW_BADGES_CONTENT,
    COLOR_NAME_HEX,
    COLOR_VARIANT_CHIP_BG,
    COLOR_VARIANT_CHIP_STROKE,
    COLOR_VARIANT_CHIP_TEXT,
    FS_CHIP,
)


def product_swatch_hexes(product) -> list[str]:
    """Colores reconocidos (hex) con stock, para muestrario y altura de fila."""
    hexes: list[str] = []
    for v in product.variants.all():
        if v.stock <= 0:
            continue
        nm = (v.name or "").strip().lower()
        hx = COLOR_NAME_HEX.get(nm)
        if hx:
            hexes.append(hx)
    return hexes


def product_has_size_badges(product) -> bool:
    for v in product.variants.all():
        if v.stock <= 0:
            continue
        if variant_name_is_size_label((v.name or "").strip().upper()):
            return True
    return False


def variant_name_is_size_label(name: str) -> bool:
    """True solo para tallas: nombre de variante de 1 o 2 letras (S, M, XL, etc.)."""
    key = (name or "").strip().upper()
    return 1 <= len(key) <= 2 and bool(re.match(r"^[A-ZÁÉÍÓÚÑ]+$", key))


class RoundedVariantChipFlowable(Flowable):
    """Talla en recuadro gris con esquinas redondeadas."""

    def __init__(self, label: str, side_pt: float, font_pt: float):
        super().__init__()
        self._label = (label or "").strip()
        self._side = float(side_pt)
        self._font_pt = float(font_pt)
        self.width = self._side
        self.height = self._side

    def draw(self):
        c = self.canv
        s = self._side
        r = min(2.4 * mm, s * 0.22)
        c.setFillColor(colors.HexColor(COLOR_VARIANT_CHIP_BG))
        c.setStrokeColor(colors.HexColor(COLOR_VARIANT_CHIP_STROKE))
        c.setLineWidth(0.4)
        c.roundRect(0, 0, s, s, r, stroke=1, fill=1)
        c.setFillColor(colors.HexColor(COLOR_VARIANT_CHIP_TEXT))
        c.setFont("Helvetica-Bold", self._font_pt)
        tw = rl_string_width(self._label, "Helvetica-Bold", self._font_pt)
        tx = max(0.0, (s - tw) / 2)
        ty = s * 0.5 - self._font_pt * 0.32
        c.drawString(tx, ty, self._label)


def size_badges_flowable(product, cell_inner_w: float):
    """Recuadros grises redondeados (una talla por caja)."""
    names = []
    for v in sorted(product.variants.all(), key=lambda x: (x.sort_order, x.name)):
        if v.stock <= 0:
            continue
        key = (v.name or "").strip().upper()
        if variant_name_is_size_label(key):
            names.append(key)
    if not names:
        return Spacer(1, 0.1)

    chip_gap = 2.0 * mm
    max_w = max(12.0, float(cell_inner_w) - 2)
    max_side = min(4.8 * mm, CARD_ROW_BADGES_CONTENT - 1 * mm)

    names = names[:8]
    while len(names) > 1:
        n = len(names)
        side_try = (max_w - (n - 1) * chip_gap) / n
        if side_try >= 4.2 * mm:
            break
        names.pop()

    n = len(names)
    side = (max_w - (n - 1) * chip_gap) / n
    side = max(4.0 * mm, min(max_side, side))

    def _one_tile(lbl: str) -> Flowable:
        return RoundedVariantChipFlowable(lbl, side, FS_CHIP)

    row = []
    col_widths = []
    for i, lbl in enumerate(names):
        if i > 0:
            row.append(Spacer(chip_gap, side))
            col_widths.append(chip_gap)
        row.append(_one_tile(lbl))
        col_widths.append(side)

    outer = Table([row], colWidths=col_widths, hAlign="CENTER")
    outer.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return outer


def color_swatches_flowable(product, cell_inner_w: float):
    """Cuadrados de color según nombres de variantes reconocidos (con stock)."""
    hexes = product_swatch_hexes(product)[:6]
    if not hexes:
        return Spacer(1, 0.1)
    gap = 1.2 * mm
    max_w = max(16.0, float(cell_inner_w) - 2)
    while len(hexes) > 1:
        n = len(hexes)
        sq_try = (max_w - gap * (n - 1)) / n
        if sq_try >= 4.0:
            break
        hexes.pop()
    n = len(hexes)
    sq = (max_w - gap * (n - 1)) / n
    sq = max(4.0, min(2.8 * mm, sq))
    row = []
    for hx in hexes:
        row.append(
            Table(
                [[""]],
                colWidths=[sq],
                rowHeights=[sq],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(hx)),
                        ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                ),
            )
        )
    outer = Table([row], colWidths=[sq] * len(row), hAlign="CENTER")
    outer.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return outer
