#!/usr/bin/env bash
# exit on error
set -o errexit

# Pillow necesita libwebp en el sistema para abrir imágenes .webp de productos (producción)
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq libwebp-dev zlib1g-dev libjpeg62-turbo-dev libpng-dev 2>/dev/null \
    || apt-get install -y -qq libwebp-dev zlib1g-dev libjpeg-dev libpng-dev 2>/dev/null \
    || true
fi

pip install --upgrade pip
pip install -r requirements.txt

# Recompilar Pillow tras instalar libwebp (wheel previo puede no traer WebP)
python - <<'PY'
from PIL import features
import subprocess
import sys

if not features.check("webp"):
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-cache-dir", "Pillow>=10.0.0"]
    )
    if not features.check("webp"):
        sys.stderr.write(
            "AVISO: Pillow sigue sin WebP; instala libwebp-dev en el build o usa imágenes JPEG/PNG.\n"
        )
PY

# Recopilar archivos estáticos
python manage.py collectstatic --no-input

# Ejecutar migraciones
python manage.py migrate

# Cargar datos iniciales (opcional - comentar si ya se cargaron)
# python manage.py load_initial_data

