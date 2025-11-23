"""
Comando para verificar el estado de las imágenes de productos

Uso:
    python manage.py verify_images
    python manage.py verify_images --offers-only
    python manage.py verify_images --related-only
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from shop.models import Product, ProductImage
from django.db.models import Prefetch
from pathlib import Path
import os


class Command(BaseCommand):
    help = 'Verifica el estado de las imágenes de productos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--offers-only',
            action='store_true',
            help='Solo verificar ofertas',
        )
        parser.add_argument(
            '--related-only',
            action='store_true',
            help='Solo verificar productos relacionados',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('VERIFICACIÓN DE IMÁGENES DE PRODUCTOS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Información del entorno
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('CONFIGURACIÓN:'))
        self.stdout.write(f'  MEDIA_ROOT: {settings.MEDIA_ROOT}')
        self.stdout.write(f'  MEDIA_URL: {settings.MEDIA_URL}')
        self.stdout.write(f'  DEBUG: {settings.DEBUG}')
        
        media_products_dir = Path(settings.MEDIA_ROOT) / 'products'
        self.stdout.write(f'  Directorio media/products: {media_products_dir}')
        self.stdout.write(f'  Existe: {media_products_dir.exists()}')
        if media_products_dir.exists():
            files_count = len(list(media_products_dir.glob('*')))
            self.stdout.write(f'  Archivos en directorio: {files_count}')
        
        self.stdout.write('')
        
        # Verificar ofertas
        if not options['related_only']:
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('PRODUCTOS EN OFERTA:'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
            offers = Product.objects.filter(
                is_active=True,
                is_offer=True,
                stock__gt=0
            ).select_related('category', 'brand').prefetch_related(
                Prefetch('images', queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id'))
            )[:3]
            
            for product in offers:
                self.stdout.write('')
                self.stdout.write(self.style.WARNING(f'Producto: {product.name} (ID: {product.id})'))
                self.stdout.write(f'  Categoría: {product.category.name if product.category else "None"}')
                self.stdout.write(f'  Marca: {product.brand.name if product.brand else "None"}')
                self.stdout.write(f'  Stock: {product.stock}')
                
                images = product.images.all()
                self.stdout.write(f'  Total imágenes en BD: {images.count()}')
                
                if images.count() > 0:
                    for idx, img in enumerate(images):
                        self.stdout.write(f'    [{idx}] {img.image.name}')
                        self.stdout.write(f'        URL: {img.image.url}')
                        self.stdout.write(f'        Path: {img.image.path if hasattr(img.image, "path") else "N/A"}')
                        self.stdout.write(f'        is_primary: {img.is_primary}')
                        self.stdout.write(f'        order: {img.order}')
                        
                        # Verificar si el archivo existe
                        try:
                            if hasattr(img.image, 'path'):
                                file_exists = os.path.exists(img.image.path)
                                self.stdout.write(f'        Archivo existe: {file_exists}')
                                if file_exists:
                                    file_size = os.path.getsize(img.image.path)
                                    self.stdout.write(f'        Tamaño: {file_size} bytes')
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'        Error al verificar archivo: {str(e)}'))
                    
                    # Probar get_primary_image
                    primary_img = product.get_primary_image()
                    if primary_img:
                        self.stdout.write(f'  get_primary_image() retorna: {primary_img.image.name}')
                        self.stdout.write(f'    URL: {primary_img.image.url}')
                    else:
                        self.stdout.write(self.style.ERROR('  get_primary_image() retorna: None'))
                    
                    # Probar images.first
                    first_img = images.first()
                    if first_img:
                        self.stdout.write(f'  images.first() retorna: {first_img.image.name}')
                        self.stdout.write(f'    URL: {first_img.image.url}')
                else:
                    self.stdout.write(self.style.ERROR('  [ERROR] No hay imágenes asociadas'))
        
        # Verificar productos relacionados (simular vista product_detail)
        if not options['offers_only']:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('PRODUCTOS RELACIONADOS (simulación):'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            
            # Tomar un producto de ejemplo
            sample_product = Product.objects.filter(is_active=True).first()
            if sample_product:
                self.stdout.write(f'Producto base: {sample_product.name} (Categoría: {sample_product.category.name if sample_product.category else "None"})')
                
                related_products = Product.objects.filter(
                    category=sample_product.category,
                    is_active=True
                ).exclude(id=sample_product.id).select_related('category', 'brand').prefetch_related(
                    Prefetch('images', queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id'))
                )[:4]
                
                self.stdout.write(f'Productos relacionados encontrados: {related_products.count()}')
                
                for product in related_products:
                    self.stdout.write('')
                    self.stdout.write(self.style.WARNING(f'Producto: {product.name} (ID: {product.id})'))
                    
                    images = product.images.all()
                    self.stdout.write(f'  Total imágenes en BD: {images.count()}')
                    
                    if images.count() > 0:
                        first_img = images.first()
                        self.stdout.write(f'  images.first(): {first_img.image.name}')
                        self.stdout.write(f'    URL: {first_img.image.url}')
                        
                        primary_img = product.get_primary_image()
                        if primary_img:
                            self.stdout.write(f'  get_primary_image(): {primary_img.image.name}')
                            self.stdout.write(f'    URL: {primary_img.image.url}')
                        else:
                            self.stdout.write(self.style.ERROR('  get_primary_image(): None'))
                    else:
                        self.stdout.write(self.style.ERROR('  [ERROR] No hay imágenes asociadas'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('VERIFICACIÓN COMPLETADA'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

