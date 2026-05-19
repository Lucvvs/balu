"""Constantes de layout y estilo del catálogo PDF."""
from reportlab.lib.units import mm

COLS = 4

CATALOG_CATEGORY_ORDER = (
    "cascos",
    "seguridad",
    "maletas",
    "equipamiento",
    "accesorios",
)
CATALOG_CATEGORY_OTROS = "otros"

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

COLOR_PRICE_FINAL = "#0f211d"
COLOR_VARIANT_CHIP_BG = "#d2d7db"
COLOR_VARIANT_CHIP_TEXT = "#2a3236"
COLOR_VARIANT_CHIP_STROKE = "#b9c0c6"
COLOR_CATEGORY_RULE_RED = "#c41e1e"

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

PRICE_BADGE_GAP = 1.05 * mm
CARD_ROW_BADGES_CONTENT = 4.4 * mm
CARD_ROW_IMAGE = 28 * mm * 1.30 * 1.10
CARD_ROW_SWATCH = 2.85 * mm
CARD_ROW_SWATCH_EMPTY = 0.55 * mm
TITLE_DESC_GAP = 0.2 * mm
TITLE_PRICE_GAP = 0.25 * mm
CARD_MAX_TITLE_LINES = 3
CARD_MAX_DESC_LINES = 2
TEXT_MEASURE_HEIGHT_FUDGE_PT = 1.5
TITLE_STACK_HEIGHT_BUF_PT = 1.0

FS_TITLE = 7 * 1.20 * 1.10 * 1.10
FS_DESC = 6.2 * 1.20 * 1.10 * 1.10
FS_PRICE_OLD = 6.5 * 1.20 * 1.10 * 1.10
FS_PRICE_FINAL = 8 * 1.40 * 1.10 * 1.10
FS_CHIP = 5.5 * 1.20 * 1.15 * 1.10
PRICE_ROW_OLD_H = FS_PRICE_OLD * 1.02
PRICE_ROW_FINAL_H = FS_PRICE_FINAL * 1.01

CATEGORY_BANNER_GAP_BELOW = 2.0 * mm
CATEGORY_BANNER_GAP_ABOVE = 2.0 * mm
CATEGORY_BANNER_GAP_PAGE_TOP = 0.8 * mm
CATEGORY_RED_BAR_H = 2.0
CATALOG_GRID_ROW_GAP = 2.0 * mm
ROWS_PER_PAGE_FROM_PAGE_TWO = 3

CATALOG_LOGO_MAX_W = 58 * mm * 1.20
CATALOG_LOGO_MAX_H = 30 * mm * 1.20
CATALOG_LOGO_SHIFT_UP = 10 * mm
CATALOG_CHANNEL_ICON_H = 4.2 * mm * 1.20 * 1.10
CATALOG_CHANNEL_FONT = 7.0 * 1.20 * 1.10
CATALOG_CHANNEL_ICON_TEXT_GAP = 2.0 * mm * 1.20 * 1.10
CATALOG_CHANNEL_ROW_GAP = 2.2 * mm * 1.20 * 1.10
CATALOG_CHANNEL_BELOW_LOGO = 2.2 * mm
CATALOG_FIRST_PAGE_CLEARANCE_EXTRA = 2 * mm
CATALOG_FIRST_PAGE_CLEARANCE_SCALE = 0.5
