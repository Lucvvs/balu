"""
Management command para eliminar todos los productos y sus imágenes

Uso:
    python manage.py clean_products                    # Mostrar advertencia
    python manage.py clean_products --confirm          # Confirmar eliminación
    python manage.py clean_products --confirm --images # Eliminar también archivos físicos de imágenes
"""

from django.core.management.base import BaseCommand
from shop.models import Product, ProductImage
from django.conf import settings
from pathlib import Path
import os


class Command(BaseCommand):
    help = 'Elimina todos los productos y sus imágenes de la base de datos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar eliminación de todos los productos',
        )
        parser.add_argument(
            '--images',
            action='store_true',
            help='Eliminar también los archivos físicos de imágenes del disco',
        )

    def handle(self, *args, **options):
        product_count = Product.objects.count()
        image_count = ProductImage.objects.count()

        if product_count == 0:
            self.stdout.write(self.style.WARNING('No hay productos para eliminar.'))
            return

        if not options['confirm']:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('=' * 60))
            self.stdout.write(self.style.WARNING('ADVERTENCIA: Esta accion eliminara TODOS los productos'))
            self.stdout.write(self.style.WARNING('=' * 60))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(f'  • Productos a eliminar: {product_count}'))
            self.stdout.write(self.style.WARNING(f'  • Imágenes a eliminar: {image_count}'))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Usa --confirm para proceder con la eliminación.'))
            if options['images']:
                self.stdout.write(self.style.WARNING('Usa --images junto con --confirm para eliminar también los archivos físicos.'))
            return

        # Eliminar productos (las imágenes se eliminan automáticamente por CASCADE)
        deleted_products = Product.objects.all()
        product_names = [p.name for p in deleted_products]
        deleted_products.delete()

        # Si se solicita, eliminar también archivos físicos
        deleted_files = 0
        if options['images']:
            media_products_dir = Path(settings.MEDIA_ROOT) / 'products'
            if media_products_dir.exists():
                for img_file in media_products_dir.glob('*'):
                    if img_file.is_file():
                        try:
                            img_file.unlink()
                            deleted_files += 1
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Error al eliminar {img_file.name}: {str(e)}')
                            )

        # Resumen
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('[OK] Productos eliminados exitosamente'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'  • Productos eliminados: {product_count}'))
        self.stdout.write(self.style.SUCCESS(f'  • Imágenes eliminadas (BD): {image_count}'))
        if options['images']:
            self.stdout.write(self.style.SUCCESS(f'  • Archivos físicos eliminados: {deleted_files}'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        
        # Mostrar productos eliminados
        if product_names:
            self.stdout.write(self.style.SUCCESS('Productos eliminados:'))
            for name in product_names[:10]:  # Mostrar máximo 10
                self.stdout.write(self.style.SUCCESS(f'  • {name}'))
            if len(product_names) > 10:
                self.stdout.write(self.style.SUCCESS(f'  ... y {len(product_names) - 10} más'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Siguiente paso:'))
        self.stdout.write(self.style.SUCCESS('   python manage.py load_initial_products --data-dir media/productos'))

