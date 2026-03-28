"""
Elimina pedidos completos, carritos, productos, variantes e imágenes (BD + archivos en media).

Uso:
    python manage.py wipe_products_and_orders --yes

Solo ejecutar en entornos donde quieras dejar el catálogo y pedidos en cero antes de repoblar.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shop.models import Cart, CartItem, Order, Product, ProductImage


class Command(BaseCommand):
    help = (
        'Borra todos los pedidos (y pagos), todos los carritos y sus líneas (CartItem), '
        'productos, variantes e imágenes; elimina archivos en MEDIA_ROOT/products/.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Confirmar eliminación (obligatorio).',
        )
        parser.add_argument(
            '--skip-media-sweep',
            action='store_true',
            help='No borrar archivos sueltos restantes en media/products/ tras vaciar la BD.',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            raise CommandError(
                'Operación destructiva. Añade --yes para confirmar.\n'
                'Ejemplo: python manage.py wipe_products_and_orders --yes'
            )

        with transaction.atomic():
            n_products = Product.objects.count()
            n_images = ProductImage.objects.count()

            self.stdout.write(self.style.WARNING('=' * 60))
            n_carts = Cart.objects.count()
            n_cart_items = CartItem.objects.count()
            self.stdout.write(
                self.style.WARNING(
                    f'Pedidos: {Order.objects.count()} · Carritos: {n_carts} · '
                    f'Líneas de carrito: {n_cart_items} · Productos: {n_products} · Imágenes: {n_images}'
                )
            )
            self.stdout.write(self.style.WARNING('Eliminando…'))
            self.stdout.write(self.style.WARNING('=' * 60))

            _, detail_orders = Order.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f'Pedidos eliminados (detalle por modelo: {detail_orders}).')
            )

            # Carrito: borrar ítems primero (claro en logs); al borrar Cart igual hay CASCADE.
            deleted_items, _ = CartItem.objects.all().delete()
            _, detail_carts = Cart.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Carritos eliminados: {n_carts} carritos, {deleted_items} líneas; '
                    f'detalle CASCADE: {detail_carts}.'
                )
            )

            files_removed = 0
            for img in ProductImage.objects.iterator(chunk_size=200):
                if img.image and img.image.name:
                    try:
                        img.image.delete(save=False)
                        files_removed += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'No se pudo borrar archivo de imagen id={img.pk}: {e}')
                        )
                img.delete()

            self.stdout.write(
                self.style.SUCCESS(f'Imágenes en BD: {n_images} filas; archivos intentados: {files_removed}.')
            )

            Product.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Productos eliminados: {n_products}.'))

        if not options['skip_media_sweep']:
            media_products = Path(settings.MEDIA_ROOT) / 'products'
            if media_products.is_dir():
                extra = 0
                for f in media_products.iterdir():
                    if f.is_file() and f.name != '.gitkeep':
                        try:
                            f.unlink()
                            extra += 1
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'No se pudo eliminar {f.name}: {e}'))
                if extra:
                    self.stdout.write(
                        self.style.SUCCESS(f'Archivos extra en media/products/: {extra} eliminados.')
                    )

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                'Listo: pedidos, carritos (e ítems), productos e imágenes de catálogo eliminados. '
                'Categorías, marcas, métodos de envío/pago y usuarios no se tocaron.'
            )
        )
