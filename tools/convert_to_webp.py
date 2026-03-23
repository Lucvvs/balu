"""
Convierte PNG/JPEG bajo static/img y media/ (brands, products, payment_methods) a WebP
y elimina los originales. Uso desde la raíz del proyecto Django (MotoMotoCR):

    python tools/convert_to_webp.py

Requiere Pillow.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Instala Pillow: pip install Pillow", file=sys.stderr)
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_IMG = BASE_DIR / "static" / "img"
MEDIA = BASE_DIR / "media"
SUBDIRS = ("brands", "products", "payment_methods", "productos")

EXTENSIONS = {".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"}


def to_webp(src: Path) -> Path | None:
    dest = src.with_suffix(".webp")
    if dest == src:
        return None
    try:
        st = src.stat()
    except FileNotFoundError:
        return None
    if st.st_size == 0:
        print(f"[SKIP] Vacío: {src}", flush=True)
        try:
            src.unlink()
        except OSError:
            pass
        return None
    try:
        with Image.open(src) as im:
            mode = im.mode
            if mode == "P":
                im = im.convert("RGBA")
            elif mode == "RGBA":
                pass
            elif mode == "LA":
                im = im.convert("RGBA")
            else:
                im = im.convert("RGB")
            im.save(dest, "WEBP", quality=85, method=6)
    except Exception as e:
        print(f"[ERROR] {src}: {e}", file=sys.stderr)
        return None
    try:
        src.unlink()
    except FileNotFoundError:
        pass
    except OSError as e:
        print(f"[WARN] No se pudo borrar {src}: {e}", file=sys.stderr)
    return dest


def collect_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    out: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in EXTENSIONS:
            out.append(p)
    return out


def ensure_motoestado(static_img: Path) -> None:
    """Si no existe motoestado, copia logo.webp como recurso de estado de pedido."""
    moto = static_img / "motoestado.webp"
    logo = static_img / "logo.webp"
    if moto.exists() or not logo.exists():
        return
    import shutil

    shutil.copy2(logo, moto)
    print(f"[OK] Creado {moto.name} desde logo.webp (reemplazar si hace falta un asset propio)")


def main() -> None:
    all_paths: list[Path] = []
    all_paths.extend(collect_files(STATIC_IMG))
    for sub in SUBDIRS:
        all_paths.extend(collect_files(MEDIA / sub))

    # favicon.ico u otros no raster
    all_paths = [p for p in all_paths if p.suffix in EXTENSIONS]

    converted = 0
    for src in sorted(all_paths, key=lambda x: str(x)):
        dest = to_webp(src)
        if dest:
            print(f"OK {src.relative_to(BASE_DIR)} -> {dest.name}", flush=True)
            converted += 1

    ensure_motoestado(STATIC_IMG)
    print(f"Total convertidos: {converted}")


if __name__ == "__main__":
    main()
