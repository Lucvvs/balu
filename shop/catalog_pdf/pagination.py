"""Paginación del catálogo PDF."""
from reportlab.lib.units import mm
from reportlab.platypus import CondPageBreak, SimpleDocTemplate, Spacer, Table, TableStyle

from shop.catalog_pdf.constants import (
    CATALOG_GRID_ROW_GAP,
    CATEGORY_BANNER_GAP_ABOVE,
    CATEGORY_BANNER_GAP_BELOW,
    CATEGORY_BANNER_GAP_PAGE_TOP,
    ROWS_PER_PAGE_FROM_PAGE_TWO,
)
from shop.catalog_pdf.utils import platypus_height


def catalog_segment_height(segment: dict, full_w: float) -> float:
    h = 0.0
    if segment.get("banner"):
        if segment.get("gap_above_banner"):
            h += CATEGORY_BANNER_GAP_ABOVE
        elif segment.get("gap_page_top"):
            h += CATEGORY_BANNER_GAP_PAGE_TOP
        h += platypus_height(segment["banner"], full_w)
        h += CATEGORY_BANNER_GAP_BELOW
    h += platypus_height(segment["row"], full_w)
    h += CATALOG_GRID_ROW_GAP
    return h


def append_catalog_segment(story: list, segment: dict) -> None:
    if segment.get("banner"):
        if segment.get("gap_above_banner"):
            story.append(Spacer(1, CATEGORY_BANNER_GAP_ABOVE))
        elif segment.get("gap_page_top"):
            story.append(Spacer(1, CATEGORY_BANNER_GAP_PAGE_TOP))
        story.append(segment["banner"])
        story.append(Spacer(1, CATEGORY_BANNER_GAP_BELOW))
    story.append(segment["row"])
    story.append(Spacer(1, CATALOG_GRID_ROW_GAP))


def segment_flow_rows(segment: dict, flags: dict, full_w: float) -> list[tuple]:
    """Pares (flowable, alto) de un segmento para apilar en tabla vertical."""
    rows: list[tuple] = []
    if segment.get("banner"):
        if flags.get("gap_above_banner"):
            rows.append((Spacer(1, CATEGORY_BANNER_GAP_ABOVE), CATEGORY_BANNER_GAP_ABOVE))
        elif flags.get("gap_page_top"):
            rows.append((Spacer(1, CATEGORY_BANNER_GAP_PAGE_TOP), CATEGORY_BANNER_GAP_PAGE_TOP))
        banner = segment["banner"]
        rows.append((banner, platypus_height(banner, full_w)))
        rows.append((Spacer(1, CATEGORY_BANNER_GAP_BELOW), CATEGORY_BANNER_GAP_BELOW))
    product_row = segment["row"]
    rows.append((product_row, platypus_height(product_row, full_w)))
    rows.append((Spacer(1, CATALOG_GRID_ROW_GAP), CATALOG_GRID_ROW_GAP))
    return rows


def build_chunk_inner_table(
    chunk: list[dict],
    full_w: float,
    *,
    first_row_gap_page_top: bool,
) -> Table:
    table_rows: list[list] = []
    row_heights: list[float] = []
    for j, seg in enumerate(chunk):
        flags = {
            "gap_above_banner": bool(seg.get("banner")) and j > 0,
            "gap_page_top": bool(seg.get("banner")) and j == 0 and first_row_gap_page_top,
        }
        for flowable, rh in segment_flow_rows(seg, flags, full_w):
            table_rows.append([flowable])
            row_heights.append(rh)
    inner = Table(table_rows, colWidths=[full_w], rowHeights=row_heights)
    inner.setStyle(
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
    return inner


def centered_later_page_block(inner_table: Table, full_w: float, page_usable_h: float) -> Table:
    """Bloque de altura de página completa con el chunk centrado verticalmente."""
    outer = Table([[inner_table]], colWidths=[full_w], rowHeights=[page_usable_h])
    outer.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return outer


def catalog_usable_page_height(doc: SimpleDocTemplate) -> float:
    return float(doc.pagesize[1] - doc.topMargin - doc.bottomMargin - 10 * mm)


def append_catalog_segments_paginated(
    story: list,
    segments: list[dict],
    *,
    full_w: float,
    doc: SimpleDocTemplate,
    first_page_overhead: float,
) -> None:
    """
    Página 1: cabecera + tantas filas que quepan.
    Desde la página 2: hasta 3 filas por hoja, centradas verticalmente en el área útil.
    """
    usable_h = catalog_usable_page_height(doc)

    idx = 0
    first_budget = max(0.0, usable_h - first_page_overhead)
    while idx < len(segments):
        seg_h = catalog_segment_height(segments[idx], full_w)
        if seg_h > first_budget and idx > 0:
            break
        if seg_h > first_budget and idx == 0:
            break
        first_budget -= seg_h
        append_catalog_segment(story, segments[idx])
        idx += 1

    grid_started = idx > 0
    while idx < len(segments):
        chunk = segments[idx : idx + ROWS_PER_PAGE_FROM_PAGE_TWO]
        inner = build_chunk_inner_table(
            chunk,
            full_w,
            first_row_gap_page_top=not grid_started,
        )
        page_block = centered_later_page_block(inner, full_w, usable_h)
        story.append(CondPageBreak(usable_h))
        story.append(page_block)
        grid_started = True
        idx += ROWS_PER_PAGE_FROM_PAGE_TWO
