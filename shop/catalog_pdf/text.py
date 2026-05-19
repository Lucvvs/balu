"""Texto de tarjetas: ajuste de líneas, párrafos y alturas."""
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth as rl_string_width
from reportlab.platypus import Paragraph

from shop.catalog_pdf.constants import (
    CARD_MAX_DESC_LINES,
    CARD_MAX_TITLE_LINES,
    CARD_ROW_BADGES_CONTENT,
    FS_DESC,
    FS_PRICE_FINAL,
    FS_PRICE_OLD,
    FS_TITLE,
    PRICE_BADGE_GAP,
    PRICE_ROW_FINAL_H,
    PRICE_ROW_OLD_H,
    TEXT_MEASURE_HEIGHT_FUDGE_PT,
    TITLE_DESC_GAP,
    TITLE_PRICE_GAP,
    TITLE_STACK_HEIGHT_BUF_PT,
)
from shop.catalog_pdf.utils import esc_xml, flowable_height, text_wrap_width


def wrap_words_to_line_groups(
    words: list[str],
    max_width_pt: float,
    font: str,
    font_size: float,
) -> list[list[str]]:
    lines: list[list[str]] = []
    cur: list[str] = []
    cur_w = 0.0
    for w in words:
        sep = " " if cur else ""
        pw = rl_string_width(sep + w, font, font_size)
        if cur and cur_w + pw > max_width_pt + 1.0:
            lines.append(cur)
            cur = [w]
            cur_w = rl_string_width(w, font, font_size)
        else:
            cur.append(w)
            cur_w += pw
    if cur:
        lines.append(cur)
    return lines


def balance_word_line_groups(lines: list[list[str]]) -> list[list[str]]:
    """Evita que la última línea del título quede con una sola palabra (si hay ≥3 palabras)."""
    if len(lines) < 2:
        return lines
    while len(lines) >= 2 and len(lines[-1]) == 1:
        if len(lines[-2]) < 2:
            break
        moved = lines[-2].pop()
        lines[-1].insert(0, moved)
        if not lines[-2]:
            del lines[-2]
    return lines


def cap_word_line_groups(
    lines: list[list[str]],
    max_lines: int,
    max_width_pt: float,
    font: str,
    font_size: float,
) -> list[list[str]]:
    if len(lines) <= max_lines:
        return lines
    kept = lines[: max_lines - 1]
    tail_words: list[str] = []
    for group in lines[max_lines - 1 :]:
        tail_words.extend(group)
    text = " ".join(tail_words)
    ell = "\u2026"
    while text and rl_string_width(text + ell, font, font_size) > max_width_pt + 1.0:
        if " " in text:
            text = text.rsplit(" ", 1)[0]
        else:
            text = text[:-1]
    kept.append([text + ell] if text else [ell])
    return kept


def title_lines_xml(name_plain: str, max_width_pt: float, font_size: float) -> str:
    words = [w for w in (name_plain or "").strip().split() if w]
    if not words:
        return ""
    font = "Helvetica-Bold"
    lines = wrap_words_to_line_groups(words, max_width_pt, font, font_size)
    lines = cap_word_line_groups(lines, CARD_MAX_TITLE_LINES, max_width_pt, font, font_size)
    if len(words) >= 3:
        lines = balance_word_line_groups(lines)
    return "<br/>".join(esc_xml(" ".join(group)) for group in lines)


def desc_lines_xml(desc_plain: str, max_width_pt: float, font_size: float) -> str:
    words = [w for w in (desc_plain or "").strip().split() if w]
    if not words:
        return ""
    font = "Helvetica"
    lines = wrap_words_to_line_groups(words, max_width_pt, font, font_size)
    lines = cap_word_line_groups(lines, CARD_MAX_DESC_LINES, max_width_pt, font, font_size)
    return "<br/>".join(esc_xml(" ".join(group)) for group in lines)


def title_paragraph(name_plain: str, styles: dict, inner_w: float) -> Paragraph:
    tw = text_wrap_width(inner_w)
    xml = title_lines_xml(name_plain, tw, FS_TITLE)
    line_lead = FS_TITLE * 1.08
    st = ParagraphStyle(
        "CardTitle",
        parent=styles["pname"],
        fontName="Helvetica-Bold",
        fontSize=FS_TITLE,
        leading=line_lead,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceBefore=0,
        spaceAfter=0,
    )
    return Paragraph(f"<b>{xml}</b>" if xml else " ", st)


def desc_paragraph(desc_plain: str, styles: dict, inner_w: float) -> Paragraph:
    tw = text_wrap_width(inner_w)
    xml = desc_lines_xml(desc_plain, tw, FS_DESC)
    line_lead = FS_DESC * 1.08
    st = ParagraphStyle(
        "CardDesc",
        parent=styles["pname"],
        fontName="Helvetica",
        fontSize=FS_DESC,
        leading=line_lead,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#444444"),
        spaceBefore=0,
        spaceAfter=0,
    )
    fs_d = f"{FS_DESC:.2f}"
    body = xml if xml else " "
    return Paragraph(f'<font face="Helvetica" size="{fs_d}" color="#444444">{body}</font>', st)


def card_text_block_heights(inner_w: float, name_raw: str, desc_raw: str, styles: dict) -> tuple[float, float]:
    """Alturas naturales (título y descripción por separado) para una tarjeta."""
    tw = text_wrap_width(inner_w)
    th = 0.0
    if (name_raw or "").strip():
        th = flowable_height(title_paragraph(name_raw, styles, inner_w), tw)
    dh = 0.0
    if (desc_raw or "").strip():
        dh = flowable_height(desc_paragraph(desc_raw, styles, inner_w), tw)
    return th, dh


def text_stack_height(
    inner_w: float,
    name_raw: str,
    desc_raw: str,
    styles: dict,
    *,
    title_h: float | None = None,
    desc_h: float | None = None,
    include_desc_row: bool = False,
    include_badges_row: bool = False,
    badge_content_h: float | None = None,
) -> float:
    """Alto del bloque título + descripción (opcional); sin precio ni tallas."""
    th, dh = card_text_block_heights(inner_w, name_raw, desc_raw, styles)
    if title_h is not None:
        th = max(th, title_h)
    if desc_h is not None:
        dh = max(dh, desc_h)
    total = th
    if include_desc_row:
        total += TITLE_DESC_GAP + dh
    return total


def price_block_height(product) -> float:
    _ = product
    return PRICE_ROW_OLD_H + PRICE_ROW_FINAL_H


def badges_stack_height(*, include_badges_row: bool, badge_content_h: float | None = None) -> float:
    if not include_badges_row:
        return 0.0
    bh = badge_content_h if badge_content_h is not None else CARD_ROW_BADGES_CONTENT
    return PRICE_BADGE_GAP + bh


def default_text_price_row_height() -> float:
    """Alto base del bloque texto+precio (peor caso: 3 líneas de nombre + 2 de descripción + oferta)."""
    title_lead = FS_TITLE * 1.08
    desc_lead = FS_DESC * 1.08
    return (
        CARD_MAX_TITLE_LINES * title_lead
        + TITLE_DESC_GAP
        + CARD_MAX_DESC_LINES * desc_lead
        + TITLE_PRICE_GAP
        + PRICE_ROW_OLD_H
        + PRICE_ROW_FINAL_H
        + PRICE_BADGE_GAP
        + CARD_ROW_BADGES_CONTENT
        + TEXT_MEASURE_HEIGHT_FUDGE_PT
        + TITLE_STACK_HEIGHT_BUF_PT
    )
