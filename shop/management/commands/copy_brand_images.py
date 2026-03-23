"""
Comando para copiar imágenes de marcas desde static/img/ a media/brands/

Uso:
    python manage.py copy_brand_images
"""

import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Copia imágenes de marcas desde static/img/ a media/brands/'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Copiando imágenes de marcas...'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        
        # Directorio origen (static/img/)
        source_dir = Path(settings.BASE_DIR) / 'static' / 'img'
        
        # Directorio destino (media/brands/)
        dest_dir = Path(settings.MEDIA_ROOT) / 'brands'
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Nombres de archivos esperados (basados en los slugs)
        brand_images = [
            'hro.webp',
            'shaft.webp',
            '4rs.webp',
            'kovix.webp',
            'motocentric.webp',
            'ich.webp',
            'shot.webp',
        ]
        
        copied = 0
        not_found = 0
        
        for filename in brand_images:
            source_file = source_dir / filename
            dest_file = dest_dir / filename
            
            if source_file.exists():
                try:
                    shutil.copy2(source_file, dest_file)
                    self.stdout.write(self.style.SUCCESS(f'   [OK] {filename}'))
                    copied += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   [ERROR] No se pudo copiar {filename}: {str(e)}'))
            else:
                self.stdout.write(self.style.WARNING(f'   [NO ENCONTRADO] {filename}'))
                not_found += 1
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        if copied > 0:
            self.stdout.write(self.style.SUCCESS(f'¡Proceso completado! {copied}/{len(brand_images)} imágenes copiadas.'))
        if not_found > 0:
            self.stdout.write(self.style.WARNING(f'{not_found} imágenes no encontradas.'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
