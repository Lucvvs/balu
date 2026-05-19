"""Rejilla de productos: layout y tablas por fila."""
from reportlab.platypus import Table, TableStyle

from shop.catalog_pdf.cards import (
    card_row_heights,
    empty_cell,
    product_cell,
    unify_card_row_heights,
)
from shop.catalog_pdf.constants import (
    CARD_ROW_BADGES_CONTENT,
    CATALOG_GRID_ROW_GAP,
    CATEGORY_BANNER_GAP_ABOVE,
    CATEGORY_BANNER_GAP_BELOW,
    CATEGORY_BANNER_GAP_PAGE_TOP,
    COLS,
    TITLE_PRICE_GAP,
    TITLE_STACK_HEIGHT_BUF_PT,
)
from shop.catalog_pdf.text import (
    badges_stack_height,
    card_text_block_heights,
    price_block_height,
    text_stack_height,
)
from shop.catalog_pdf.utils import truncate
from shop.catalog_pdf.variants import product_has_size_badges


def global_max_card_heights(per_row_unified: list[list[float]]) -> list[float]:
    merged: list[float] = []
    for unified in per_row_unified:
        for i, val in enumerate(unified):
            if i >= len(merged):
                merged.extend([0.0] * (i - len(merged) + 1))
            merged[i] = max(merged[i], val)
    return merged or card_row_heights(None)


def compute_grid_row_layout(prods: list, inner: float, styles: dict) -> dict:
    """Alturas unificadas y metadatos de texto para una fila de hasta COLS productos."""
    text_dims: list[tuple[float, float, bool]] = []
    for p in prods:
        if p is None:
            continue
        name_raw = truncate((p.name or "").upper(), 120)
        desc_raw = truncate((p.short_description or "") or "", 200)
        th, dh = card_text_block_heights(inner, name_raw, desc_raw, styles)
        text_dims.append((th, dh, bool(desc_raw.strip())))

    max_title_h = max((d[0] for d in text_dims), default=0.0)
    include_desc_row = any(d[2] for d in text_dims)
    max_desc_h = max((d[1] for d in text_dims), default=0.0) if include_desc_row else 0.0
    include_badges_row = any(product_has_size_badges(p) for p in prods if p is not None)
    unified_badge_h = CARD_ROW_BADGES_CONTENT if include_badges_row else 0.0

    per_heights: list[list[float]] = []
    for p in prods:
        if p is None:
            per_heights.append(card_row_heights(None))
        else:
            name_raw = truncate((p.name or "").upper(), 120)
            desc_raw = truncate((p.short_description or "") or "", 200)
            h = card_row_heights(p)
            need = (
                text_stack_height(
                    inner,
                    name_raw,
                    desc_raw,
                    styles,
                    title_h=max_title_h,
                    desc_h=max_desc_h,
                    include_desc_row=include_desc_row,
                )
                + TITLE_PRICE_GAP
                + price_block_height(p)
                + badges_stack_height(
                    include_badges_row=include_badges_row,
                    badge_content_h=unified_badge_h,
                )
                + TITLE_STACK_HEIGHT_BUF_PT
            )
            per_heights.append([h[0], max(h[1], need), h[2]])

    unified = unify_card_row_heights(per_heights)
    return {
        "card_heights": unified,
        "max_title_h": max_title_h,
        "max_desc_h": max_desc_h,
        "include_desc_row": include_desc_row,
        "include_badges_row": include_badges_row,
        "unified_badge_h": unified_badge_h,
    }


def build_grid_row_table(
    prods: list,
    cell_w: float,
    inner: float,
    styles: dict,
    card_heights: list[float],
    layout: dict,
) -> Table:
    row_cells = []
    for p in prods:
        if p is None:
            row_cells.append(empty_cell(cell_w, row_heights=card_heights))
        else:
            name_raw = truncate((p.name or "").upper(), 120)
            desc_raw = truncate((p.short_description or "") or "", 200)
            row_cells.append(
                product_cell(
                    p,
                    styles,
                    cell_w,
                    row_heights=card_heights,
                    unified_title_h=layout["max_title_h"],
                    unified_desc_h=layout["max_desc_h"],
                    include_desc_row=layout["include_desc_row"],
                    include_badges_row=layout["include_badges_row"],
                    unified_badge_h=layout["unified_badge_h"],
                )
            )
    t = Table([row_cells], colWidths=[cell_w] * COLS, repeatRows=0)
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
    return t


def worst_chunk_height(
    card_heights: list[float],
    banner_block_h: float,
    rows_per_page: int,
    *,
    first_on_page: bool = True,
) -> float:
    """Peor caso: cada fila del bloque abre categoría nueva (3 banners en la misma página)."""
    row_block_h = sum(card_heights)
    total = 0.0
    for j in range(rows_per_page):
        if j > 0:
            total += CATEGORY_BANNER_GAP_ABOVE
        elif first_on_page:
            total += CATEGORY_BANNER_GAP_PAGE_TOP
        total += banner_block_h + CATEGORY_BANNER_GAP_BELOW + row_block_h + CATALOG_GRID_ROW_GAP
    return total


def fit_card_heights_for_grid_pages(
    heights: list[float],
    usable_h: float,
    *,
    rows_per_page: int,
    banner_block_h: float,
) -> list[float]:
    """Escala tarjetas hasta que un bloque de N filas (con banners) quepa en una hoja."""
    target = usable_h * 0.96
    scaled = list(heights)
    for _ in range(12):
        if worst_chunk_height(scaled, banner_block_h, rows_per_page) <= target:
            return scaled
        scale = target / worst_chunk_height(scaled, banner_block_h, rows_per_page)
        scaled = [h * scale for h in scaled]
    return scaled
