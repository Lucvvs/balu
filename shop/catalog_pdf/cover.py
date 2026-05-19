"""Portada y decoraciones de página del catálogo PDF."""
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth as rl_string_width
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from shop.catalog_pdf.constants import (
    CATALOG_CHANNEL_BELOW_LOGO,
    CATALOG_CHANNEL_FONT,
    CATALOG_CHANNEL_ICON_H,
    CATALOG_CHANNEL_ICON_TEXT_GAP,
    CATALOG_CHANNEL_ROW_GAP,
    CATALOG_CHANNEL_SPECS,
    CATALOG_LOGO_MAX_H,
    CATALOG_LOGO_MAX_W,
    CATALOG_LOGO_SHIFT_UP,
    MESES_ES,
)
from shop.catalog_pdf.images import static_asset_to_png_dict


def catalog_header_block(styles: dict, doc_width: float):
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
            [Paragraph("CATÁLOGO", styles["cat_main"])],
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


def prepare_catalog_logo():
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
    return static_asset_to_png_dict(path)


def prepare_catalog_channel_icons() -> list[dict]:
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
        d = static_asset_to_png_dict(path)
        if d:
            d["url"] = url
            d["label"] = label
            out.append(d)
    return out


def channel_stack_height(n_channels: int) -> float:
    """Alto aproximado de la lista de canales bajo el logo (puntos)."""
    if n_channels <= 0:
        return 0.0
    return (
        CATALOG_CHANNEL_BELOW_LOGO
        + n_channels * CATALOG_CHANNEL_ICON_H
        + max(0, n_channels - 1) * CATALOG_CHANNEL_ROW_GAP
    )


def draw_catalog_logo(canv: canvas.Canvas, logo: dict) -> tuple[float, float, float, float] | None:
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


def draw_catalog_channel_links_list(
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


def draw_catalog_page_decorations(
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
            box = draw_catalog_logo(canv, logo_info)
            if channel_icons and box:
                draw_catalog_channel_links_list(canv, box, channel_icons)
        except Exception:
            pass
    elif channel_icons:
        w, h = A4
        m = 11 * mm
        fake_lw, fake_lh = CATALOG_LOGO_MAX_W, CATALOG_LOGO_MAX_H
        x = w - m - fake_lw - 0.10 * fake_lw
        y = h - m - fake_lh + CATALOG_LOGO_SHIFT_UP
        draw_catalog_channel_links_list(canv, (x, y, fake_lw, fake_lh), channel_icons)

    canv.restoreState()
