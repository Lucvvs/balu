"""Tarjetas de producto: precio, texto e imagen."""
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from shop.catalog_pdf.constants import (
    CARD_ROW_BADGES_CONTENT,
    CARD_ROW_IMAGE,
    CARD_ROW_SWATCH,
    CARD_ROW_SWATCH_EMPTY,
    COLOR_PRICE_FINAL,
    FS_PRICE_FINAL,
    FS_PRICE_OLD,
    PRICE_BADGE_GAP,
    PRICE_ROW_FINAL_H,
    PRICE_ROW_OLD_H,
    TITLE_DESC_GAP,
    TITLE_PRICE_GAP,
    TITLE_STACK_HEIGHT_BUF_PT,
)
from shop.catalog_pdf.images import product_image_flowable
from shop.catalog_pdf.text import (
    badges_stack_height,
    default_text_price_row_height,
    desc_paragraph,
    price_block_height,
    text_stack_height,
    title_paragraph,
)
from shop.catalog_pdf.utils import flowable_height, format_clp, slot, text_wrap_width, truncate
from shop.catalog_pdf.variants import (
    color_swatches_flowable,
    product_has_size_badges,
    product_swatch_hexes,
    size_badges_flowable,
)


def card_row_heights(product=None):
    """
    Alturas por fila de la tarjeta. Si ``product`` es None (celda vacía del grid),
    se usa la fila de muestras completa para alinear con el resto de columnas.
    """
    sw = CARD_ROW_SWATCH if (product is not None and product_swatch_hexes(product)) else (
        CARD_ROW_SWATCH if product is None else CARD_ROW_SWATCH_EMPTY
    )
    return [
        CARD_ROW_IMAGE,
        default_text_price_row_height(),
        sw,
    ]


def card_body_row_heights(
    product,
    inner_w: float,
    name_raw: str,
    desc_raw: str,
    styles: dict,
) -> list[float]:
    """
    Alturas de filas de la tarjeta. La fila de imagen es siempre ``CARD_ROW_IMAGE``.
    El bloque texto+precio crece si hace falta (hasta 3 líneas de nombre y 2 de descripción).
    """
    h = card_row_heights(product)
    has_desc = bool((desc_raw or "").strip())
    has_badges = product_has_size_badges(product)
    need = (
        text_stack_height(inner_w, name_raw, desc_raw, styles, include_desc_row=has_desc)
        + TITLE_PRICE_GAP
        + price_block_height(product)
        + badges_stack_height(include_badges_row=has_badges)
        + TITLE_STACK_HEIGHT_BUF_PT
    )
    boost = need - h[1]
    if boost <= 0:
        return h
    out = list(h)
    out[1] = h[1] + boost
    return out


def unify_card_row_heights(per_card: list[list[float]]) -> list[float]:
    """Misma altura por fila en las 4 columnas; imagen siempre con alto fijo."""
    if not per_card:
        return card_row_heights(None)
    out = [CARD_ROW_IMAGE]
    for i in range(1, len(per_card[0])):
        out.append(max(row[i] for row in per_card))
    return out


def price_block(product, styles: dict, inner_w: float):
    """
    Siempre dos filas de alto fijo: superior (tachado o vacía) + precio final,
    para que todos los precios queden en la misma línea en la rejilla.
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
        top = Paragraph(f'<font size="{fs_o}" color="#ffffff"> </font>', st_old)
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


def text_price_block(
    product,
    name_raw: str,
    desc_raw: str,
    styles: dict,
    inner_w: float,
    *,
    unified_title_h: float | None = None,
    unified_desc_h: float | None = None,
    include_desc_row: bool = False,
    include_badges_row: bool = False,
    unified_badge_h: float | None = None,
):
    """
    Título, descripción, precio y tallas (chips) en un bloque; colores van en otra fila debajo.
    ``unified_*`` iguala alturas en la fila del grid.
    """
    w = float(inner_w)
    tw = text_wrap_width(inner_w)
    rows: list[list] = []
    row_heights: list[float] = []
    pad_cmds: list[tuple] = []
    row_i = 0

    if (name_raw or "").strip():
        title_p = title_paragraph(name_raw, styles, inner_w)
        th = flowable_height(title_p, tw)
        if unified_title_h is not None:
            th = max(th, unified_title_h)
        rows.append([title_p])
        row_heights.append(th)
        row_i += 1

    if include_desc_row:
        if (desc_raw or "").strip():
            desc_p = desc_paragraph(desc_raw, styles, inner_w)
            dh = flowable_height(desc_p, tw)
        else:
            desc_p = Spacer(1, 0.1)
            dh = 0.0
        if unified_desc_h is not None:
            dh = max(dh, unified_desc_h)
        if row_i > 0:
            pad_cmds.append(("TOPPADDING", (0, row_i), (-1, row_i), TITLE_DESC_GAP))
        rows.append([desc_p])
        row_heights.append(dh)
        row_i += 1

    price_t = price_block(product, styles, inner_w)
    ph = price_block_height(product)
    if row_i > 0:
        pad_cmds.append(("TOPPADDING", (0, row_i), (-1, row_i), TITLE_PRICE_GAP))
    rows.append([price_t])
    row_heights.append(ph)
    row_i += 1

    if include_badges_row:
        if product_has_size_badges(product):
            badges_fb = size_badges_flowable(product, inner_w)
        else:
            badges_fb = Spacer(1, 0.1)
        bh = CARD_ROW_BADGES_CONTENT
        if unified_badge_h is not None:
            bh = max(bh, unified_badge_h)
        pad_cmds.append(("TOPPADDING", (0, row_i), (-1, row_i), PRICE_BADGE_GAP))
        rows.append([badges_fb])
        row_heights.append(bh)
        row_i += 1

    t = Table(rows, colWidths=[w], rowHeights=row_heights)
    style_cmds = [
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ] + pad_cmds
    t.setStyle(TableStyle(style_cmds))
    return t


def product_cell(
    product,
    styles: dict,
    cell_w: float,
    *,
    row_heights: list[float] | None = None,
    unified_title_h: float | None = None,
    unified_desc_h: float | None = None,
    include_desc_row: bool | None = None,
    include_badges_row: bool | None = None,
    unified_badge_h: float | None = None,
):
    inner = cell_w - 4 * mm
    img_pad = 0.2 * mm
    name_raw = truncate((product.name or "").upper(), 120)
    desc_raw = truncate((product.short_description or "") or "", 200)
    if include_desc_row is None:
        include_desc_row = bool(desc_raw.strip())
    if include_badges_row is None:
        include_badges_row = product_has_size_badges(product)
    h = row_heights or card_body_row_heights(product, inner, name_raw, desc_raw, styles)
    img_w = max(12.0, inner - 2 * img_pad)
    img_h = max(12.0, h[0] - 2 * img_pad)
    body = Table(
        [
            [slot(inner, h[0], product_image_flowable(product, img_w, img_h, styles), "TOP")],
            [
                slot(
                    inner,
                    h[1],
                    text_price_block(
                        product,
                        name_raw,
                        desc_raw,
                        styles,
                        inner,
                        unified_title_h=unified_title_h,
                        unified_desc_h=unified_desc_h,
                        include_desc_row=include_desc_row,
                        include_badges_row=include_badges_row,
                        unified_badge_h=unified_badge_h,
                    ),
                    "TOP",
                )
            ],
            [slot(inner, h[2], color_swatches_flowable(product, inner), "TOP")],
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


def empty_cell(cell_w: float, *, row_heights: list[float] | None = None):
    inner = cell_w - 4 * mm
    h = row_heights or card_row_heights(None)
    rows = [
        [slot(inner, h[0], Spacer(1, 0.1))],
        [slot(inner, h[1], Spacer(1, 0.1))],
        [slot(inner, h[2], Spacer(1, 0.1))],
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
