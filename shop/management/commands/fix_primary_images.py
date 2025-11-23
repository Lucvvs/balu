"""
Comando para corregir las imágenes principales de todos los productos

Uso:
    python manage.py fix_primary_images
"""

from django.core.management.base import BaseCommand
from shop.models import Product, ProductImage


class Command(BaseCommand):
    help = 'Corrige las imágenes principales de todos los productos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Corrigiendo imágenes principales...'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        products = Product.objects.filter(is_active=True)
        fixed_count = 0
        
        for product in products:
            images = product.images.all().order_by('order', 'id')
            
            if images.count() == 0:
                continue
            
            # Verificar si ya hay una imagen principal
            primary_exists = images.filter(is_primary=True).exists()
            
            if not primary_exists:
                # Marcar la primera imagen como principal
                first_image = images.first()
                first_image.is_primary = True
                first_image.save()
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  [OK] {product.name}: Marcada {first_image.image.name} como principal')
                )
            else:
                # Verificar que solo haya una principal
                primary_images = images.filter(is_primary=True)
                if primary_images.count() > 1:
                    # Dejar solo la primera como principal
                    first_primary = primary_images.first()
                    for img in primary_images.exclude(id=first_primary.id):
                        img.is_primary = False
                        img.save()
                    fixed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  [OK] {product.name}: Corregidas múltiples imágenes principales')
                    )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'Total productos corregidos: {fixed_count}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

