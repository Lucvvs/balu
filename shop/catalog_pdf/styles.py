"""Estilos de párrafo Platypus para el catálogo PDF."""
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

from shop.catalog_pdf.constants import (
    COLOR_PRICE_FINAL,
    FS_DESC,
    FS_PRICE_FINAL,
    FS_PRICE_OLD,
    FS_TITLE,
)


def paragraph_styles():
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
        fontSize=8.5,
        textColor=colors.white,
        alignment=TA_CENTER,
        leading=10,
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
