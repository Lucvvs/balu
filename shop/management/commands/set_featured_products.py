"""
Comando para establecer productos en oferta y más vendidos

Uso:
    python manage.py set_featured_products
    python manage.py set_featured_products --offers-only
    python manage.py set_featured_products --best-sellers-only
"""

from django.core.management.base import BaseCommand
from shop.models import Product


class Command(BaseCommand):
    help = 'Establece productos en oferta y más vendidos automáticamente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--offers-only',
            action='store_true',
            help='Solo establecer ofertas',
        )
        parser.add_argument(
            '--best-sellers-only',
            action='store_true',
            help='Solo establecer más vendidos',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Configurando productos destacados...'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Limpiar ofertas y más vendidos existentes
        if not options['offers_only']:
            Product.objects.update(is_best_seller=False)
            self.stdout.write(self.style.SUCCESS('[OK] Más vendidos limpiados'))
        
        if not options['best_sellers_only']:
            Product.objects.update(is_offer=False)
            self.stdout.write(self.style.SUCCESS('[OK] Ofertas limpiadas'))
        
        self.stdout.write('')
        
        # Establecer ofertas (3 productos con stock > 0)
        if not options['best_sellers_only']:
            self.stdout.write(self.style.SUCCESS('Estableciendo ofertas...'))
            # Primero intentar productos con offer_price
            offers_with_price = Product.objects.filter(
                is_active=True,
                stock__gt=0,
                offer_price__isnull=False
            ).exclude(offer_price=0).order_by('offer_price')[:3]
            
            # Si no hay suficientes con oferta, completar con productos más baratos
            if offers_with_price.count() < 3:
                remaining = 3 - offers_with_price.count()
                # Excluir los que ya están en ofertas
                excluded_ids = list(offers_with_price.values_list('id', flat=True))
                additional_offers = Product.objects.filter(
                    is_active=True,
                    stock__gt=0
                ).exclude(id__in=excluded_ids).order_by('price')[:remaining]
                offers = list(offers_with_price) + list(additional_offers)
            else:
                offers = offers_with_price
            
            for product in offers:
                product.is_offer = True
                product.save()
                self.stdout.write(
                    self.style.SUCCESS(f'  [OK] Oferta: {product.name}')
                )
            
            if offers.count() == 0:
                self.stdout.write(
                    self.style.WARNING('  [ADVERTENCIA] No se encontraron productos para ofertas')
                )
        
        self.stdout.write('')
        
        # Establecer más vendidos (3 productos con stock > 0, ordenados por fecha de creación)
        if not options['offers_only']:
            self.stdout.write(self.style.SUCCESS('Estableciendo más vendidos...'))
            best_sellers = Product.objects.filter(
                is_active=True,
                stock__gt=0
            ).order_by('-created_at')[:3]
            
            for product in best_sellers:
                product.is_best_seller = True
                product.save()
                self.stdout.write(
                    self.style.SUCCESS(f'  [OK] Más vendido: {product.name}')
                )
            
            if best_sellers.count() == 0:
                self.stdout.write(
                    self.style.WARNING('  [ADVERTENCIA] No se encontraron productos para más vendidos')
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('¡Configuración completada!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

