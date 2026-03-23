"""
Actualiza rutas en ImageField tras migrar archivos a .webp (misma ruta relativa, nueva extensión).

Uso:
    python manage.py sync_image_paths_to_webp
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from shop.models import Brand, PaymentMethod, ProductImage


RASTER_EXT = {".png", ".jpg", ".jpeg"}


def _to_webp(name: str) -> str:
    p = Path(name)
    if p.suffix.lower() in RASTER_EXT:
        return p.with_suffix(".webp").as_posix()
    return name


class Command(BaseCommand):
    help = "Sincroniza ImageField a .webp si el archivo .webp existe en MEDIA_ROOT"

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        updated = 0

        for pi in ProductImage.objects.all().iterator():
            old = pi.image.name
            new = _to_webp(old)
            if new == old:
                continue
            if not (media_root / new).exists():
                self.stdout.write(
                    self.style.WARNING(f"[SKIP] Falta archivo: {new} (ProductImage pk={pi.pk})")
                )
                continue
            pi.image.name = new
            pi.save(update_fields=["image"])
            updated += 1
            self.stdout.write(self.style.SUCCESS(f"OK ProductImage pk={pi.pk}: {old} -> {new}"))

        for pm in PaymentMethod.objects.exclude(image="").iterator():
            old = pm.image.name
            new = _to_webp(old)
            if new == old:
                continue
            if not (media_root / new).exists():
                self.stdout.write(
                    self.style.WARNING(f"[SKIP] Falta archivo: {new} (PaymentMethod pk={pm.pk})")
                )
                continue
            pm.image.name = new
            pm.save(update_fields=["image"])
            updated += 1
            self.stdout.write(self.style.SUCCESS(f"OK PaymentMethod pk={pm.pk}: {old} -> {new}"))

        for br in Brand.objects.exclude(logo="").iterator():
            old = br.logo.name
            new = _to_webp(old)
            if new == old:
                continue
            if not (media_root / new).exists():
                self.stdout.write(
                    self.style.WARNING(f"[SKIP] Falta archivo: {new} (Brand pk={br.pk})")
                )
                continue
            br.logo.name = new
            br.save(update_fields=["logo"])
            updated += 1
            self.stdout.write(self.style.SUCCESS(f"OK Brand pk={br.pk}: {old} -> {new}"))

        self.stdout.write(self.style.SUCCESS(f"Total registros actualizados: {updated}"))
