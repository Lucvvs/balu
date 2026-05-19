"""Imágenes PIL/ReportLab para tarjetas y assets estáticos."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.platypus import Image as RLImage, Paragraph, Table, TableStyle


def is_webp_bytes(raw: bytes) -> bool:
    return len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"


def pil_webp_supported() -> bool:
    try:
        from PIL import features

        return bool(features.check("webp"))
    except Exception:
        return False


def open_image_from_bytes(raw: bytes) -> Image.Image | None:
    """Abre bytes de imagen; en producción los productos suelen ser .webp."""
    if not raw:
        return None
    bio = io.BytesIO(raw)
    is_webp = is_webp_bytes(raw)
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


def pil_to_rgb(im: Image.Image) -> Image.Image:
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


def save_pil_to_buffer(im: Image.Image, *, prefer_jpeg: bool = False) -> io.BytesIO | None:
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


def read_image_field_bytes(field_file) -> bytes | None:
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


def bytes_to_rl_image(raw: bytes, max_w_pt: float, max_h_pt: float):
    """
    Convierte bytes de imagen (JPEG/PNG/WebP/…) a buffer RGB y devuelve RLImage
    dimensionado en puntos (mantiene proporción).
    """
    if not raw:
        return None
    if is_webp_bytes(raw) and not pil_webp_supported():
        return None
    im = open_image_from_bytes(raw)
    if im is None:
        return None

    try:
        im = pil_to_rgb(im)
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

    out = save_pil_to_buffer(im, prefer_jpeg=True)
    if out is None:
        return None
    img = RLImage(out, width=w_pt, height=h_pt)
    img._catalog_png_buffer = out  # noqa: SLF001
    return img


def product_image_flowable(product, max_w_pt: float, max_h_pt: float, styles: dict):
    """
    Caja de imagen de alto fijo (``max_h_pt``). La foto se escala dentro y se alinea
    al borde inferior para que el título empiece siempre en la misma línea.
    """
    pi = product.get_primary_image()
    field = pi.image if pi else None
    raw = read_image_field_bytes(field)
    has_image = False
    if raw:
        content = bytes_to_rl_image(raw, max_w_pt, max_h_pt)
        has_image = content is not None
    if not has_image:
        content = Paragraph("Sin imagen", styles["no_img"])

    t = Table([[content]], colWidths=[max_w_pt], rowHeights=[max_h_pt])
    style_rows = [
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]
    if not has_image:
        style_rows.append(("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f4f4")))
    t.setStyle(TableStyle(style_rows))
    return t


def static_asset_to_png_dict(path: Path) -> dict | None:
    """Imagen estática (webp/png/jpg) → buffer RGB para ReportLab."""
    try:
        raw = path.read_bytes()
        if path.suffix.lower() == ".webp" and not pil_webp_supported():
            return None
        im = open_image_from_bytes(raw)
        if im is None:
            return None
        im = pil_to_rgb(im)
        bio = save_pil_to_buffer(im, prefer_jpeg=False)
        if bio is None:
            return None
        iw, ih = im.size
        return {"buffer": bio, "iw": float(iw), "ih": float(ih)}
    except Exception:
        return None
