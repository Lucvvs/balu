"""Franja de categoría en el catálogo PDF."""
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from shop.catalog_pdf.constants import CATEGORY_RED_BAR_H, COLOR_CATEGORY_RULE_RED
from shop.catalog_pdf.utils import esc_xml, platypus_height


def category_banner_table(cat_name: str, styles: dict, full_w: float) -> Table:
    """
    Título en franja negra + fila roja propia (sin LINEBELOW, que se solapaba con productos).
    """
    banner = Table(
        [
            [Paragraph(esc_xml(cat_name.upper()), styles["cat_section"])],
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
                ("TOPPADDING", (0, 0), (-1, 0), 3),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
                ("TOPPADDING", (0, 1), (-1, 1), 0),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return banner


def category_banner_block_height(styles: dict, full_w: float) -> float:
    return platypus_height(category_banner_table("Cascos", styles, full_w), full_w)
