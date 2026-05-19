"""
Catálogo de productos en PDF (admin): rejilla tipo folleto impreso, A4.
Las imágenes pasan por Pillow (RGBA/WebP → RGB PNG) para compatibilidad con ReportLab.
"""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import BinaryIO, Iterable

from django.conf import settings
from django.db.models import QuerySet

from PIL import Image

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth as rl_string_width
from reportlab.platypus import (
    Flowable,
    Image as RLImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


COLS = 4
MESES_ES = (
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
)

# Nombres de variante (minúsculas) → color aproximado para “muestrario”
COLOR_NAME_HEX = {
    "negro": "#1a1a1a",
    "black": "#1a1a1a",
    "blanco": "#f5f5f5",
    "white": "#f5f5f5",
    "rojo": "#c41e1e",
    "red": "#c41e1e",
    "azul": "#1e4d8c",
    "blue": "#1e4d8c",
    "amarillo": "#e6b800",
    "yellow": "#e6b800",
    "verde": "#1e6b3a",
    "green": "#1e6b3a",
    "gris": "#7a7a7a",
    "grey": "#7a7a7a",
    "gray": "#7a7a7a",
    "naranja": "#e85d04",
    "orange": "#e85d04",
    "morado": "#5c2d8c",
    "violeta": "#5c2d8c",
    "rosa": "#d63384",
    "pink": "#d63384",
    "café": "#5c3d2e",
    "cafe": "#5c3d2e",
    "marrón": "#5c3d2e",
    "marron": "#5c3d2e",
    "plateado": "#c0c0c0",
    "silver": "#c0c0c0",
    "dorado": "#c9a227",
    "gold": "#c9a227",
}

# Catálogo: precio final (negro verdoso), chips de talla, franja categoría
COLOR_PRICE_FINAL = "#0f211d"
COLOR_VARIANT_CHIP_BG = "#d2d7db"
COLOR_VARIANT_CHIP_TEXT = "#2a3236"
COLOR_VARIANT_CHIP_STROKE = "#b9c0c6"
COLOR_CATEGORY_RULE_RED = "#c41e1e"

# Enlaces y textos: templates/partials/_como_comprar_y_canales.html
CATALOG_CHANNEL_SPECS: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (
        ("instagramlogo.webp", "instagramlogo.png"),
        "https://www.instagram.com/motomotochile.cl/",
        "motomotochile.cl",
    ),
    (
        ("wsplogo.webp", "wsplogo.png"),
        "https://wa.me/56982177468",
        "+569 8217 7468",
    ),
    (
        ("weblogo.webp", "weblogo.png"),
        "https://www.motomotochile.cl",
        "www.motomotochile.cl",
    ),
)

KNOWN_SIZES = frozenset(
    {
        "XS",
        "S",
        "M",
        "L",
        "XL",
        "XXL",
        "XXXL",
        "ÚNICA",
        "UNICA",
        "UNICO",
        "ÚNICO",
        "STD",
        "ST",
    }
)

# Separación deseada entre precio y cuadros de talla (línea “verde” del mockup)
BADGE_TOP_SEP = 1.1 * mm
CARD_ROW_BADGES_CONTENT = 5.0 * mm * 1.12 * 1.10
CARD_ROW_BADGES = BADGE_TOP_SEP + CARD_ROW_BADGES_CONTENT

# Tarjetas compactas: título+desc con altura ajustada; fila muestras menor si no hay colores
CARD_ROW_IMAGE = 28 * mm * 1.30 * 1.10
CARD_ROW_TITLE = 12.0 * mm * 1.10
CARD_ROW_SWATCH = 2.85 * mm
CARD_ROW_SWATCH_EMPTY = 0.55 * mm
CARD_ROW_PRICE = 8.2 * mm * 1.22 * 1.10

# Descripción en varias líneas: más espacio al bloque título+texto sin cambiar la altura total
# de la tarjeta (se compensa reduciendo solo la fila de imagen).
TITLE_STACK_HEIGHT_BUF_PT = 4.0
CARD_ROW_IMAGE_MIN = 23.0 * mm


def _product_swatch_hexes(product) -> list[str]:
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


def _card_row_heights(product=None):
    """
    Alturas por fila de la tarjeta. Si ``product`` es None (celda vacía del grid),
    se usa la fila de muestras completa para alinear con el resto de columnas.
    """
    sw = CARD_ROW_SWATCH if (product is not None and _product_swatch_hexes(product)) else (
        CARD_ROW_SWATCH if product is None else CARD_ROW_SWATCH_EMPTY
    )
    return [
        CARD_ROW_IMAGE,
        CARD_ROW_TITLE,
        sw,
        CARD_ROW_PRICE,
        CARD_ROW_BADGES,
    ]


# Tamaños de texto tarjeta (escala acumulada respecto a base; último paso +10%)
FS_TITLE = 7 * 1.20 * 1.10 * 1.10
FS_DESC = 6.2 * 1.20 * 1.10 * 1.10
FS_PRICE_OLD = 6.5 * 1.20 * 1.10 * 1.10
FS_PRICE_FINAL = 8 * 1.40 * 1.10 * 1.10
FS_CHIP = 5.5 * 1.20 * 1.15 * 1.10

# Alturas de filas dentro del bloque precio (precio final siempre en la misma línea)
PRICE_ROW_OLD_H = FS_PRICE_OLD * 1.12
PRICE_ROW_FINAL_H = FS_PRICE_FINAL * 1.04


def format_clp(value: int) -> str:
    return f"${int(value):,}".replace(",", ".")


def _truncate(s: str, max_len: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max(0, max_len - 1)].rstrip() + "\u2026"


def _balance_title_lines(name_plain: str, max_width_pt: float, font_size: float) -> str:
    """
    Parte el título en líneas según ancho; si la última línea quedaría con una sola palabra,
    pasa palabra(s) desde la penúltima para que haya al menos 2 en la última.
    """
    words = [w for w in (name_plain or "").strip().split() if w]
    if len(words) < 3:
        return _esc_xml(" ".join(words))
    font = "Helvetica-Bold"
    lines: list[list[str]] = []
    cur: list[str] = []
    cur_w = 0.0
    for w in words:
        sep = " " if cur else ""
        piece = sep + w
        pw = rl_string_width(piece, font, font_size)
        if cur and cur_w + pw > max_width_pt + 1.0:
            lines.append(cur)
            cur = [w]
            cur_w = rl_string_width(w, font, font_size)
        else:
            cur.append(w)
            cur_w += pw
    if cur:
        lines.append(cur)
    if len(lines) < 2:
        return _esc_xml(" ".join(words))
    while len(lines) >= 2 and len(lines[-1]) == 1:
        if len(lines[-2]) < 2:
            break
        moved = lines[-2].pop()
        lines[-1].insert(0, moved)
        if not lines[-2]:
            del lines[-2]
    return "<br/>".join(_esc_xml(" ".join(line)) for line in lines)


def _slot(w: float, h: float, flowable, valign: str = "TOP"):
    """Celda de altura fija. Por defecto TOP para compactar (sin hueco vertical central)."""
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


def _title_desc_paragraph(name_plain: str, desc_raw: str, styles: dict, inner_w: float) -> Paragraph:
    tw = max(20.0, float(inner_w) - 4.0)
    balanced = _balance_title_lines(name_plain, tw, FS_TITLE)
    desc_esc = _esc_xml(desc_raw)
    line_lead = max(FS_DESC * 1.10, FS_TITLE * 1.08)
    st = ParagraphStyle(
        "CardTitleDescStack",
        parent=styles["pname"],
        fontName="Helvetica-Bold",
        fontSize=FS_TITLE,
        leading=line_lead,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceBefore=0,
        spaceAfter=0,
    )
    fs_d = f"{FS_DESC:.2f}"
    xml = (
        f"<b>{balanced}</b><br size=\"{FS_DESC * 0.35}\"/>"
        f'<font face="Helvetica" size="{fs_d}" color="#444444">{desc_esc}</font>'
    )
    return Paragraph(xml, st, bulletText=None)


def _title_desc_natural_height(inner_w: float, name_plain: str, desc_raw: str, styles: dict) -> float:
    """Alto en puntos del párrafo título+descripción al ancho real de la celda."""
    p = _title_desc_paragraph(name_plain, desc_raw, styles, inner_w)
    tw = max(20.0, float(inner_w) - 4.0)
    _, h = p.wrap(tw, 10**6)
    return float(h)


def _card_body_row_heights(
    product,
    inner_w: float,
    name_raw: str,
    desc_raw: str,
    styles: dict,
) -> list[float]:
    """
    Alturas de filas de la tarjeta. Si el texto título+descripción no cabe en
    ``CARD_ROW_TITLE``, se amplía esa fila y se reduce la de imagen la misma
    cantidad (altura total de la tarjeta sin cambios).
    """
    h = _card_row_heights(product)
    need = _title_desc_natural_height(inner_w, name_raw, desc_raw, styles)
    boost = need - h[1] + TITLE_STACK_HEIGHT_BUF_PT
    if boost <= 0:
        return h
    max_boost = h[0] - CARD_ROW_IMAGE_MIN
    if max_boost <= 0:
        return h
    b = min(boost, max_boost)
    out = list(h)
    out[0] = h[0] - b
    out[1] = h[1] + b
    return out


def _title_desc_block(name_plain: str, desc_raw: str, styles: dict, inner_w: float):
    """
    Un solo Paragraph: título con salto manual (<br/>) cuando hace falta, evitando
    que la última línea del nombre quede con una sola palabra (si hay ≥3 palabras).
    Un <br/> antes de la descripción para que quede siempre debajo del título.
    """
    return _title_desc_paragraph(name_plain, desc_raw, styles, inner_w)


def _esc_xml(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _paragraph_styles():
    base = getSampleStyleSheet()
    cat_main = ParagraphStyle(
        name="GridCatMain",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=2,
        leading=26,
    )
    cat_month = ParagraphStyle(
        name="GridCatMonth",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=12,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=10,
        leading=14,
    )
    cat_bullet = ParagraphStyle(
        name="GridCatBullet",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        textColor=colors.HexColor("#222222"),
        alignment=TA_LEFT,
        leading=12,
        leftIndent=0,
    )
    cat_section = ParagraphStyle(
        name="GridCatSection",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.white,
        alignment=TA_CENTER,
        leading=12,
    )
    pname = ParagraphStyle(
        name="GridPName",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=FS_TITLE,
        textColor=colors.black,
        alignment=TA_CENTER,
        leading=FS_TITLE * 1.12,
        spaceBefore=0,
        spaceAfter=0,
    )
    pdesc = ParagraphStyle(
        name="GridPDesc",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=FS_DESC,
        textColor=colors.HexColor("#333333"),
        alignment=TA_CENTER,
        leading=FS_DESC * 1.12,
        spaceAfter=0,
        spaceBefore=0,
    )
    price_sale = ParagraphStyle(
        name="GridPriceSale",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=FS_PRICE_FINAL,
        textColor=colors.HexColor(COLOR_PRICE_FINAL),
        alignment=TA_CENTER,
        leading=FS_PRICE_FINAL * 1.08,
    )
    price_old = ParagraphStyle(
        name="GridPriceOld",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=FS_PRICE_OLD,
        textColor=colors.HexColor("#c41e1e"),
        alignment=TA_CENTER,
        leading=FS_PRICE_OLD * 1.12,
    )
    price_single = ParagraphStyle(
        name="GridPriceSingle",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=FS_PRICE_FINAL,
        textColor=colors.HexColor(COLOR_PRICE_FINAL),
        alignment=TA_CENTER,
        leading=FS_PRICE_FINAL * 1.04,
        spaceBefore=0,
        spaceAfter=0,
    )
    no_img = ParagraphStyle(
        name="GridNoImg",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=FS_DESC,
        textColor=colors.HexColor("#999999"),
        alignment=TA_CENTER,
        leading=FS_DESC * 1.25,
    )
    return {
        "cat_main": cat_main,
        "cat_month": cat_month,
        "cat_bullet": cat_bullet,
        "cat_section": cat_section,
        "pname": pname,
        "pdesc": pdesc,
        "price_sale": price_sale,
        "price_old": price_old,
        "price_single": price_single,
        "no_img": no_img,
    }


def _is_webp_bytes(raw: bytes) -> bool:
    return len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"


def _pil_webp_supported() -> bool:
    try:
        from PIL import features

        return bool(features.check("webp"))
    except Exception:
        return False


def _open_image_from_bytes(raw: bytes) -> Image.Image | None:
    """Abre bytes de imagen; en producción los productos suelen ser .webp."""
    if not raw:
        return None
    bio = io.BytesIO(raw)
    is_webp = _is_webp_bytes(raw)
    attempts: list[object] = []
    if is_webp:
        attempts.append(["WEBP"])
    attempts.extend([None, ["PNG", "JPEG", "GIF", "WEBP"]])
    for fmts in attempts:
        try:
            bio.seek(0)
            im = Image.open(bio) if fmts is None else Image.open(bio, formats=fmts)
            im.load()
            return im
        except Exception:
            continue
    return None


def _pil_to_rgb(im: Image.Image) -> Image.Image:
    """Normaliza a RGB (fondo blanco si hay transparencia)."""
    if im.mode in ("RGBA", "LA"):
        background = Image.new("RGB", im.size, (255, 255, 255))
        if im.mode == "RGBA":
            background.paste(im, mask=im.split()[3])
        else:
            background.paste(im, mask=im.split()[1])
        return background
    if im.mode == "P":
        im = im.convert("RGBA")
        background = Image.new("RGB", im.size, (255, 255, 255))
        background.paste(im, mask=im.split()[3])
        return background
    if im.mode != "RGB":
        return im.convert("RGB")
    return im


def _save_pil_to_buffer(im: Image.Image, *, prefer_jpeg: bool = False) -> io.BytesIO | None:
    """
    Guarda imagen en BytesIO para ReportLab.
    No usar optimize=True en PNG (falla en Pillow con BytesIO: fileno / _idat).
    JPEG es más rápido para muchas fotos de producto en producción.
    """
    out = io.BytesIO()
    if prefer_jpeg:
        try:
            im.save(out, format="JPEG", quality=82, subsampling=2)
            out.seek(0)
            return out
        except Exception:
            out.seek(0)
            out.truncate(0)
    try:
        im.save(out, format="PNG", compress_level=6)
        out.seek(0)
        return out
    except Exception:
        return None


def _read_image_field_bytes(field_file) -> bytes | None:
    if not field_file or not getattr(field_file, "name", None):
        return None
    try:
        field_file.open("rb")
        try:
            return field_file.read()
        finally:
            field_file.close()
    except Exception:
        return None


def _bytes_to_rl_image(raw: bytes, max_w_pt: float, max_h_pt: float):
    """
    Convierte bytes de imagen (JPEG/PNG/WebP/…) a buffer RGB y devuelve RLImage
    dimensionado en puntos (mantiene proporción).
    """
    if not raw:
        return None
    if _is_webp_bytes(raw) and not _pil_webp_supported():
        return None
    im = _open_image_from_bytes(raw)
    if im is None:
        return None

    try:
        im = _pil_to_rgb(im)
    except Exception:
        return None

    iw, ih = im.size
    if iw < 1 or ih < 1:
        return None

    ar_img = iw / float(ih)
    box_ar = max_w_pt / max_h_pt
    if ar_img >= box_ar:
        w_pt = max_w_pt
        h_pt = max_w_pt / ar_img
    else:
        h_pt = max_h_pt
        w_pt = max_h_pt * ar_img

    w_pt = max(8.0, min(float(max_w_pt), float(w_pt)))
    h_pt = max(8.0, min(float(max_h_pt), float(h_pt)))

    # Resolución moderada: suficiente en tarjeta y evita timeout en gunicorn con catálogos grandes
    max_px = 480
    scale_px = min(1.0, max_px / max(iw, ih))
    if scale_px < 1.0:
        nw = max(1, int(iw * scale_px))
        nh = max(1, int(ih * scale_px))
        im = im.resize((nw, nh), Image.Resampling.LANCZOS)

    out = _save_pil_to_buffer(im, prefer_jpeg=True)
    if out is None:
        return None
    img = RLImage(out, width=w_pt, height=h_pt)
    img._catalog_png_buffer = out  # noqa: SLF001
    return img


def _product_image_flowable(product, max_w_pt: float, max_h_pt: float, styles: dict):
    pi = product.get_primary_image()
    field = pi.image if pi else None
    raw = _read_image_field_bytes(field)
    if raw:
        rl = _bytes_to_rl_image(raw, max_w_pt, max_h_pt)
        if rl:
            t = Table([[rl]], colWidths=[max_w_pt])
            t.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            return t
    return Table(
        [[Paragraph("Sin imagen", styles["no_img"])]],
        colWidths=[max_w_pt],
        style=TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f4f4")),
            ]
        ),
    )


class _RoundedVariantChipFlowable(Flowable):
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


def _size_badges_flowable(product, cell_inner_w: float):
    """Recuadros grises redondeados (una talla por caja)."""
    names = []
    for v in sorted(product.variants.all(), key=lambda x: (x.sort_order, x.name)):
        if v.stock <= 0:
            continue
        key = (v.name or "").strip().upper()
        if key in KNOWN_SIZES or (len(key) <= 4 and re.match(r"^[A-Z0-9ÁÉÍÓÚÑ]+$", key)):
            names.append(key[:6])
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
        return _RoundedVariantChipFlowable(lbl, side, FS_CHIP)

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


def _color_swatches_flowable(product, cell_inner_w: float):
    """Cuadrados de color según nombres de variantes reconocidos (con stock)."""
    hexes = _product_swatch_hexes(product)[:6]
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


def _badges_block_with_top_gap(product, inner: float):
    """Tallas con separación superior respecto al precio (espacio tipo línea verde)."""
    fb = _size_badges_flowable(product, inner)
    t = Table(
        [[Spacer(1, BADGE_TOP_SEP)], [fb]],
        colWidths=[inner],
        rowHeights=[BADGE_TOP_SEP, CARD_ROW_BADGES_CONTENT],
    )
    t.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return t


def _badges_empty_block(inner: float):
    t = Table(
        [[Spacer(1, BADGE_TOP_SEP)], [Spacer(1, 0.1)]],
        colWidths=[inner],
        rowHeights=[BADGE_TOP_SEP, CARD_ROW_BADGES_CONTENT],
    )
    t.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return t


def _price_block(product, styles: dict, inner_w: float):
    """
    Dos filas fijas: línea superior (tachado o reservada) + precio final abajo,
    para que oferta y precio único queden alineados entre tarjetas.
    """
    w = max(20.0, float(inner_w) - 2)
    fs_o = f"{FS_PRICE_OLD:.2f}"
    fs_f = f"{FS_PRICE_FINAL:.2f}"
    st_old = ParagraphStyle(
        "_priceRowOld",
        parent=styles["price_old"],
        fontSize=FS_PRICE_OLD,
        leading=PRICE_ROW_OLD_H,
        alignment=TA_CENTER,
        spaceBefore=0,
        spaceAfter=0,
    )
    st_final = ParagraphStyle(
        "_priceRowFinal",
        parent=styles["price_single"],
        fontSize=FS_PRICE_FINAL,
        leading=PRICE_ROW_FINAL_H,
        alignment=TA_CENTER,
        spaceBefore=0,
        spaceAfter=0,
    )
    if product.has_offer:
        top = Paragraph(
            f'<font size="{fs_o}" color="#c41e1e"><strike>{format_clp(product.price)}</strike></font>',
            st_old,
        )
        bottom = Paragraph(
            f'<font size="{fs_f}" color="{COLOR_PRICE_FINAL}"><b>{format_clp(product.offer_price)}</b></font>',
            st_final,
        )
    else:
        top = Paragraph(
            f'<font size="{fs_o}" color="#ffffff"> </font>',
            st_old,
        )
        bottom = Paragraph(format_clp(product.price), st_final)
    t = Table(
        [[top], [bottom]],
        colWidths=[w],
        rowHeights=[PRICE_ROW_OLD_H, PRICE_ROW_FINAL_H],
    )
    t.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return t


def _product_cell(product, styles: dict, cell_w: float):
    inner = cell_w - 4 * mm
    img_pad = 0.2 * mm
    name_raw = _truncate((product.name or "").upper(), 68)
    desc_raw = _truncate((product.short_description or "") or "", 80)
    h = _card_body_row_heights(product, inner, name_raw, desc_raw, styles)
    img_w = max(12.0, inner - 2 * img_pad)
    img_h = max(12.0, h[0] - 2 * img_pad)
    body = Table(
        [
            [_slot(inner, h[0], _product_image_flowable(product, img_w, img_h, styles), "TOP")],
            [_slot(inner, h[1], _title_desc_block(name_raw, desc_raw, styles, inner), "TOP")],
            [_slot(inner, h[2], _color_swatches_flowable(product, inner), "BOTTOM")],
            [_slot(inner, h[3], _price_block(product, styles, inner), "BOTTOM")],
            [_slot(inner, h[4], _badges_block_with_top_gap(product, inner), "TOP")],
        ],
        colWidths=[inner],
        rowHeights=h,
    )
    body.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0.5),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]
        )
    )
    wrap = Table([[body]], colWidths=[cell_w])
    wrap.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return wrap


def _empty_cell(cell_w: float):
    inner = cell_w - 4 * mm
    h = _card_row_heights(None)
    rows = [
        [_slot(inner, h[0], Spacer(1, 0.1))],
        [_slot(inner, h[1], Spacer(1, 0.1))],
        [_slot(inner, h[2], Spacer(1, 0.1))],
        [_slot(inner, h[3], Spacer(1, 0.1))],
        [_slot(inner, h[4], _badges_empty_block(inner))],
    ]
    body = Table(rows, colWidths=[inner], rowHeights=h)
    body.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0.5),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]
        )
    )
    wrap = Table([[body]], colWidths=[cell_w])
    wrap.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return wrap


def _catalog_header_block(styles: dict, doc_width: float):
    from django.utils import timezone

    now = timezone.now()
    mes = MESES_ES[now.month - 1]
    bullets = (
        "• Envíos a todo Chile (Región Metropolitana $3000 otras regiones consultar valor).<br/>"
        "• Retiros en Bodega MotoMoto (Puente Alto).<br/>"
        "• Entregas metro Elisa Correa (Línea 4).<br/>"
        "• Precios en CLP; sujetos a cambio sin previo aviso.<br/>"
        
    )
    inner = Table(
        [
            [Paragraph("CATALOGO", styles["cat_main"])],
            [Paragraph(mes, styles["cat_month"])],
            [Paragraph(bullets, styles["cat_bullet"])],
        ],
        colWidths=[doc_width],
    )
    inner.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 2), (0, 2), "LEFT"),
                ("LEFTPADDING", (0, 2), (0, 2), 8 * mm),
                ("RIGHTPADDING", (0, 2), (0, 2), 8 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return inner


def _static_asset_to_png_dict(path: Path) -> dict | None:
    """Imagen estática (webp/png/jpg) → buffer RGB para ReportLab."""
    try:
        raw = path.read_bytes()
        if path.suffix.lower() == ".webp" and not _pil_webp_supported():
            return None
        im = _open_image_from_bytes(raw)
        if im is None:
            return None
        im = _pil_to_rgb(im)
        bio = _save_pil_to_buffer(im, prefer_jpeg=False)
        if bio is None:
            return None
        iw, ih = im.size
        return {"buffer": bio, "iw": float(iw), "ih": float(ih)}
    except Exception:
        return None


def _prepare_catalog_logo():
    """Logo MotoMoto (static/img/logo.webp o .png) para dibujar en portada del PDF."""
    base = Path(settings.BASE_DIR) / "static" / "img"
    path = None
    for name in ("logo.webp", "logo.png", "logo.jpg"):
        p = base / name
        if p.is_file():
            path = p
            break
    if path is None:
        return None
    return _static_asset_to_png_dict(path)


def _prepare_catalog_channel_icons() -> list[dict]:
    """
    Iconos Instagram, WhatsApp y Web (mismos assets y URLs que _como_comprar_y_canales.html).
    Cada elemento: buffer, iw, ih, url
    """
    base = Path(settings.BASE_DIR) / "static" / "img"
    out: list[dict] = []
    for names, url, label in CATALOG_CHANNEL_SPECS:
        path = None
        for n in names:
            p = base / n
            if p.is_file():
                path = p
                break
        if path is None:
            continue
        d = _static_asset_to_png_dict(path)
        if d:
            d["url"] = url
            d["label"] = label
            out.append(d)
    return out


# Espacio entre franja de categoría y la primera fila de productos (dentro de KeepTogether)
CATEGORY_BANNER_GAP_BELOW = 4.5 * mm
CATEGORY_BANNER_GAP_ABOVE = 5.0 * mm
CATEGORY_RED_BAR_H = 2.8


def _category_banner_table(cat_name: str, styles: dict, full_w: float) -> Table:
    """
    Título en franja negra + fila roja propia (sin LINEBELOW, que se solapaba con productos).
    """
    banner = Table(
        [
            [Paragraph(_esc_xml(cat_name.upper()), styles["cat_section"])],
            [Spacer(1, CATEGORY_RED_BAR_H)],
        ],
        colWidths=[full_w],
        rowHeights=[None, CATEGORY_RED_BAR_H],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor(COLOR_CATEGORY_RULE_RED)),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
                ("TOPPADDING", (0, 1), (-1, 1), 0),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return banner


# Portada PDF: logo y lista de canales (+20% respecto a tamaño anterior)
CATALOG_LOGO_MAX_W = 58 * mm * 1.20
CATALOG_LOGO_MAX_H = 30 * mm * 1.20
CATALOG_LOGO_SHIFT_UP = 10 * mm
CATALOG_CHANNEL_ICON_H = 4.2 * mm * 1.20 * 1.10
CATALOG_CHANNEL_FONT = 7.0 * 1.20 * 1.10
CATALOG_CHANNEL_ICON_TEXT_GAP = 2.0 * mm * 1.20 * 1.10
CATALOG_CHANNEL_ROW_GAP = 2.2 * mm * 1.20 * 1.10
CATALOG_CHANNEL_BELOW_LOGO = 2.2 * mm
# Reserva vertical antes de la 1ª categoría (mitad del cálculo anterior)
CATALOG_FIRST_PAGE_CLEARANCE_EXTRA = 2 * mm
CATALOG_FIRST_PAGE_CLEARANCE_SCALE = 0.5


def _catalog_channel_stack_height(n_channels: int) -> float:
    """Alto aproximado de la lista de canales bajo el logo (puntos)."""
    if n_channels <= 0:
        return 0.0
    return (
        CATALOG_CHANNEL_BELOW_LOGO
        + n_channels * CATALOG_CHANNEL_ICON_H
        + max(0, n_channels - 1) * CATALOG_CHANNEL_ROW_GAP
    )


def _draw_catalog_logo(canv: canvas.Canvas, logo: dict) -> tuple[float, float, float, float] | None:
    from reportlab.lib.utils import ImageReader

    w, h = A4
    m = 11 * mm
    max_w = CATALOG_LOGO_MAX_W
    max_h = CATALOG_LOGO_MAX_H
    iw, ih = logo["iw"], logo["ih"]
    if ih < 1:
        return None
    ar = iw / ih
    box_ar = max_w / max_h
    if ar >= box_ar:
        lw = max_w
        lh = max_w / ar
    else:
        lh = max_h
        lw = max_h * ar
    # 10% hacia la izquierda; un poco más arriba para dejar sitio a la lista de canales
    x = w - m - lw - 0.10 * lw
    y = h - m - lh + CATALOG_LOGO_SHIFT_UP
    buf = logo["buffer"]
    buf.seek(0)
    ir = ImageReader(buf)
    canv.drawImage(ir, x, y, lw, lh, mask="auto")
    return (x, y, lw, lh)


def _draw_catalog_channel_links_list(
    canv: canvas.Canvas,
    logo_box: tuple[float, float, float, float],
    channels: list[dict],
) -> None:
    """
    Lista vertical bajo el logo: icono + texto, toda la fila clickeable.
    Orden: Instagram, WhatsApp, Web (como en el sitio).
    """
    if not channels:
        return
    from reportlab.lib.utils import ImageReader

    lx, ly, lw, _lh = logo_box
    icon_h = CATALOG_CHANNEL_ICON_H
    icon_text_gap = CATALOG_CHANNEL_ICON_TEXT_GAP
    row_gap = CATALOG_CHANNEL_ROW_GAP
    font_size = CATALOG_CHANNEL_FONT
    text_color = colors.HexColor("#333333")

    # Cursor justo bajo el logo (sin bajar demasiado hacia el contenido del story)
    y = ly - CATALOG_CHANNEL_BELOW_LOGO
    for ch in channels:
        iw, ih = ch["iw"], ch["ih"]
        if ih < 1:
            continue
        rh = icon_h
        rw = iw * (rh / ih)
        label = (ch.get("label") or "").strip()
        url = ch.get("url") or ""
        y -= rh
        buf = ch["buffer"]
        buf.seek(0)
        ir = ImageReader(buf)
        canv.drawImage(ir, lx, y, rw, rh, mask="auto")
        tx = lx + rw + icon_text_gap
        ty = y + rh * 0.28
        canv.setFont("Helvetica", font_size)
        canv.setFillColor(text_color)
        canv.drawString(tx, ty, label)
        tw = rl_string_width(label, "Helvetica", font_size)
        row_w = (tx + tw) - lx
        row_h = rh
        if url:
            try:
                canv.linkURL(url, (lx, y, lx + row_w, y + row_h), relative=0)
            except Exception:
                pass
        y -= row_gap


def _draw_catalog_page_decorations(
    canv: canvas.Canvas,
    doc,
    *,
    logo_info: dict | None,
    channel_icons: list[dict] | None = None,
):
    w, h = A4
    canv.saveState()
    canv.setStrokeColor(colors.black)
    canv.setLineWidth(0.6)
    m = 11 * mm
    L = 16 * mm
    canv.line(m, h - m, m + L, h - m)
    canv.line(m, h - m, m, h - m - L)
    canv.line(w - m, m, w - m - L, m)
    canv.line(w - m, m, w - m, m + L)

    canv.setFont("Helvetica", 7.5)
    canv.setFillColor(colors.HexColor("#666666"))
    canv.drawString(m, 8 * mm, "MotoMoto")
    canv.drawRightString(w - m, 8 * mm, f"Página {doc.page}")

    if logo_info:
        try:
            box = _draw_catalog_logo(canv, logo_info)
            if channel_icons and box:
                _draw_catalog_channel_links_list(canv, box, channel_icons)
        except Exception:
            pass
    elif channel_icons:
        w, h = A4
        m = 11 * mm
        fake_lw, fake_lh = CATALOG_LOGO_MAX_W, CATALOG_LOGO_MAX_H
        x = w - m - fake_lw - 0.10 * fake_lw
        y = h - m - fake_lh + CATALOG_LOGO_SHIFT_UP
        _draw_catalog_channel_links_list(canv, (x, y, fake_lw, fake_lh), channel_icons)

    canv.restoreState()


def build_catalog_pdf_bytes(products: Iterable | QuerySet, *, generated_label: str | None = None) -> bytes:
    _ = generated_label  # compatibilidad con llamadas anteriores (sin texto en cabecera)
    items = list(products)
    items.sort(key=lambda p: ((p.category.name if p.category else "").lower(), p.name.lower()))

    styles = _paragraph_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Catálogo MotoMoto",
        author="MotoMoto",
    )
    full_w = doc.width
    cell_w = full_w / COLS

    logo_info = _prepare_catalog_logo()
    channel_icons = _prepare_catalog_channel_icons()
    if logo_info is not None:
        doc._catalog_logo_keepalive = logo_info["buffer"]  # noqa: SLF001
    if channel_icons:
        doc._catalog_channels_keepalive = [c["buffer"] for c in channel_icons]  # noqa: SLF001

    story = []
    story.append(_catalog_header_block(styles, full_w))
    if channel_icons:
        raw_clear = _catalog_channel_stack_height(len(channel_icons)) + CATALOG_FIRST_PAGE_CLEARANCE_EXTRA
        clearance = raw_clear * CATALOG_FIRST_PAGE_CLEARANCE_SCALE
        story.append(Spacer(1, clearance))
    else:
        story.append(Spacer(1, 5 * mm))

    prev_cat = None
    row_buf: list = []
    # ("banner" | "row", flowable)
    grid_rows: list[tuple[str, Table]] = []

    def flush_row():
        if not row_buf:
            return
        row = row_buf[:]
        row_buf.clear()
        while len(row) < COLS:
            row.append(_empty_cell(cell_w))
        t = Table([row], colWidths=[cell_w] * COLS, repeatRows=0)
        t.setStyle(
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
        grid_rows.append(("row", t))

    for p in items:
        cat = p.category.name if p.category else "Sin categoría"
        if cat != prev_cat:
            flush_row()
            grid_rows.append(("banner", _category_banner_table(cat, styles, full_w)))
            prev_cat = cat

        row_buf.append(_product_cell(p, styles, cell_w))
        if len(row_buf) >= COLS:
            flush_row()

    flush_row()

    i = 0
    while i < len(grid_rows):
        kind, block = grid_rows[i]
        if kind == "banner":
            if i > 0:
                story.append(Spacer(1, CATEGORY_BANNER_GAP_ABOVE))
            if i + 1 < len(grid_rows) and grid_rows[i + 1][0] == "row":
                story.append(
                    KeepTogether(
                        [
                            block,
                            Spacer(1, CATEGORY_BANNER_GAP_BELOW),
                            grid_rows[i + 1][1],
                        ]
                    )
                )
                i += 2
                story.append(Spacer(1, 3 * mm))
                continue
            story.append(block)
            story.append(Spacer(1, CATEGORY_BANNER_GAP_BELOW))
            i += 1
            continue
        story.append(block)
        if kind == "row":
            story.append(Spacer(1, 3 * mm))
        i += 1

    def _on_first_page(canv, doc):
        _draw_catalog_page_decorations(
            canv, doc, logo_info=logo_info, channel_icons=channel_icons
        )

    def _on_later_pages(canv, doc):
        _draw_catalog_page_decorations(canv, doc, logo_info=None, channel_icons=None)

    doc.build(story, onFirstPage=_on_first_page, onLaterPages=_on_later_pages)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def build_catalog_pdf_file(products: Iterable | QuerySet, fileobj: BinaryIO, **kwargs) -> None:
    fileobj.write(build_catalog_pdf_bytes(products, **kwargs))
