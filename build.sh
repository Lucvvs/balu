#!/usr/bin/env bash
# exit on error
set -o errexit

# libwebp vía apt solo en entornos Debian con filesystem de escritura (no Render native build)
if command -v apt-get >/dev/null 2>&1; then
  (
    set +e
    apt-get update -qq 2>/dev/null
    apt-get install -y -qq libwebp-dev zlib1g-dev libjpeg-dev libpng-dev 2>/dev/null
    true
  )
fi

pip install --upgrade pip
pip install -r requirements.txt

# En Render, el wheel de Pillow suele incluir WebP; reinstalar solo si hace falta (sin fallar el build)
python - <<'PY'
from PIL import features
import subprocess
import sys

if not features.check("webp"):
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-cache-dir", "Pillow>=10.0.0"],
        check=False,
    )
    if not features.check("webp"):
        sys.stderr.write(
            "AVISO: Pillow sin WebP en este build; el catálogo PDF puede omitir fotos .webp.\n"
        )
PY

# Recopilar archivos estáticos
python manage.py collectstatic --no-input

# Ejecutar migraciones
python manage.py migrate

# Cargar datos iniciales (opcional - comentar si ya se cargaron)
# python manage.py load_initial_data
