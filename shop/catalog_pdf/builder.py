"""Construcción del PDF del catálogo."""
from __future__ import annotations

import io
from typing import BinaryIO, Iterable

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Spacer

from shop.catalog_pdf.category import category_banner_block_height, category_banner_table
from shop.catalog_pdf.constants import (
    CATALOG_FIRST_PAGE_CLEARANCE_EXTRA,
    CATALOG_FIRST_PAGE_CLEARANCE_SCALE,
    COLS,
    ROWS_PER_PAGE_FROM_PAGE_TWO,
)
from shop.catalog_pdf.cover import (
    catalog_header_block,
    channel_stack_height,
    draw_catalog_page_decorations,
    prepare_catalog_channel_icons,
    prepare_catalog_logo,
)
from shop.catalog_pdf.grid import (
    build_grid_row_table,
    compute_grid_row_layout,
    fit_card_heights_for_grid_pages,
    global_max_card_heights,
)
from shop.catalog_pdf.pagination import (
    append_catalog_segments_paginated,
    catalog_usable_page_height,
)
from shop.catalog_pdf.products import catalog_category_sort_key, filter_products_for_catalog_pdf
from shop.catalog_pdf.styles import paragraph_styles
from shop.catalog_pdf.utils import platypus_height


def build_catalog_pdf_bytes(products: Iterable, *, generated_label: str | None = None) -> bytes:
    _ = generated_label  # compatibilidad con llamadas anteriores (sin texto en cabecera)
    items = list(filter_products_for_catalog_pdf(products))
    items.sort(key=catalog_category_sort_key)

    styles = paragraph_styles()
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

    logo_info = prepare_catalog_logo()
    channel_icons = prepare_catalog_channel_icons()
    if logo_info is not None:
        doc._catalog_logo_keepalive = logo_info["buffer"]  # noqa: SLF001
    if channel_icons:
        doc._catalog_channels_keepalive = [c["buffer"] for c in channel_icons]  # noqa: SLF001

    story = []
    story.append(catalog_header_block(styles, full_w))
    if channel_icons:
        raw_clear = channel_stack_height(len(channel_icons)) + CATALOG_FIRST_PAGE_CLEARANCE_EXTRA
        clearance = raw_clear * CATALOG_FIRST_PAGE_CLEARANCE_SCALE
        story.append(Spacer(1, clearance))
    else:
        story.append(Spacer(1, 5 * mm))

    inner = cell_w - 4 * mm
    row_buf_products: list = []
    row_layouts: list[dict] = []
    pending_banner = None
    prev_cat = None

    def flush_row_buf() -> None:
        nonlocal pending_banner
        if not row_buf_products:
            return
        prods = row_buf_products[:]
        row_buf_products.clear()
        while len(prods) < COLS:
            prods.append(None)
        row_layouts.append(
            {
                "prods": prods,
                "layout": compute_grid_row_layout(prods, inner, styles),
                "banner": pending_banner,
            }
        )
        pending_banner = None

    for p in items:
        cat = p.category.name if p.category else "Sin categoría"
        if cat != prev_cat:
            flush_row_buf()
            pending_banner = category_banner_table(cat, styles, full_w)
            prev_cat = cat
        row_buf_products.append(p)
        if len(row_buf_products) >= COLS:
            flush_row_buf()

    flush_row_buf()

    usable_h = catalog_usable_page_height(doc)
    banner_block_h = category_banner_block_height(styles, full_w)
    global_card_heights = global_max_card_heights([r["layout"]["card_heights"] for r in row_layouts])
    global_card_heights = fit_card_heights_for_grid_pages(
        global_card_heights,
        usable_h,
        rows_per_page=ROWS_PER_PAGE_FROM_PAGE_TWO,
        banner_block_h=banner_block_h,
    )
    segments: list[dict] = []
    for spec in row_layouts:
        segments.append(
            {
                "banner": spec["banner"],
                "row": build_grid_row_table(
                    spec["prods"],
                    cell_w,
                    inner,
                    styles,
                    global_card_heights,
                    spec["layout"],
                ),
            }
        )

    header_block = catalog_header_block(styles, full_w)
    clearance = 0.0
    if channel_icons:
        raw_clear = channel_stack_height(len(channel_icons)) + CATALOG_FIRST_PAGE_CLEARANCE_EXTRA
        clearance = raw_clear * CATALOG_FIRST_PAGE_CLEARANCE_SCALE
    else:
        clearance = 5 * mm

    first_overhead = platypus_height(header_block, full_w) + clearance
    append_catalog_segments_paginated(
        story,
        segments,
        full_w=full_w,
        doc=doc,
        first_page_overhead=first_overhead,
    )

    def _on_first_page(canv, doc):
        draw_catalog_page_decorations(
            canv, doc, logo_info=logo_info, channel_icons=channel_icons
        )

    def _on_later_pages(canv, doc):
        draw_catalog_page_decorations(canv, doc, logo_info=None, channel_icons=None)

    doc.build(story, onFirstPage=_on_first_page, onLaterPages=_on_later_pages)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def build_catalog_pdf_file(products: Iterable, fileobj: BinaryIO, **kwargs) -> None:
    fileobj.write(build_catalog_pdf_bytes(products, **kwargs))
