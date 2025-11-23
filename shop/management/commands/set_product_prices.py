"""
Comando para asignar precios y stock realistas a los productos

Uso:
    python manage.py set_product_prices
"""

from django.core.management.base import BaseCommand
from shop.models import Product
import random


# Precios base por categoría (en CLP)
PRICE_RANGES = {
    'Cascos': {
        'HRO': {'min': 45000, 'max': 65000},
        'SHAFT': {'min': 55000, 'max': 85000},
        'default': {'min': 50000, 'max': 70000}
    },
    'Maletas': {
        '4RS': {'min': 80000, 'max': 150000},
        'default': {'min': 70000, 'max': 120000}
    },
    'Seguridad': {
        'KOVIX': {'min': 25000, 'max': 45000},
        'default': {'min': 20000, 'max': 40000}
    },
    'Accesorios': {
        'motocentric': {'min': 15000, 'max': 35000},
        'default': {'min': 10000, 'max': 30000}
    }
}

# Stock base por categoría
STOCK_RANGES = {
    'Cascos': {'min': 2, 'max': 8},
    'Maletas': {'min': 1, 'max': 5},
    'Seguridad': {'min': 3, 'max': 10},
    'Accesorios': {'min': 5, 'max': 15}
}


def get_price_for_product(product):
    """Calcula un precio realista para el producto"""
    category_name = product.category.name if product.category else 'Accesorios'
    brand_name = product.brand.name if product.brand else None
    
    # Obtener rango de precios
    if category_name in PRICE_RANGES:
        category_prices = PRICE_RANGES[category_name]
        if brand_name and brand_name in category_prices:
            price_range = category_prices[brand_name]
        else:
            price_range = category_prices.get('default', {'min': 20000, 'max': 50000})
    else:
        price_range = {'min': 20000, 'max': 50000}
    
    # Generar precio aleatorio dentro del rango
    base_price = random.randint(price_range['min'], price_range['max'])
    
    # Redondear a múltiplos de 1000 para precios más realistas
    base_price = (base_price // 1000) * 1000
    
    return base_price


def get_stock_for_product(product):
    """Calcula un stock realista para el producto"""
    category_name = product.category.name if product.category else 'Accesorios'
    
    if category_name in STOCK_RANGES:
        stock_range = STOCK_RANGES[category_name]
    else:
        stock_range = {'min': 1, 'max': 5}
    
    return random.randint(stock_range['min'], stock_range['max'])


def should_have_offer(product):
    """Determina si un producto debería tener oferta (30% de probabilidad)"""
    return random.random() < 0.3


def get_offer_price(base_price):
    """Calcula un precio de oferta (10-25% de descuento)"""
    discount_percent = random.randint(10, 25)
    offer_price = int(base_price * (1 - discount_percent / 100))
    # Redondear a múltiplos de 1000
    return (offer_price // 1000) * 1000


class Command(BaseCommand):
    help = 'Asigna precios y stock realistas a todos los productos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización incluso si ya tienen precio/stock',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Asignando precios y stock a productos...'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        products = Product.objects.filter(is_active=True)
        updated_count = 0
        
        for product in products:
            updated = False
            
            # Asignar precio si no tiene o si se fuerza
            if options['force'] or product.price == 0:
                new_price = get_price_for_product(product)
                product.price = new_price
                updated = True
            
            # Asignar stock si no tiene o si se fuerza
            if options['force'] or product.stock == 0:
                new_stock = get_stock_for_product(product)
                product.stock = new_stock
                updated = True
            
            # Asignar oferta (30% de probabilidad) si no tiene o si se fuerza
            if options['force'] or (not product.offer_price and should_have_offer(product)):
                if product.price > 0:
                    product.offer_price = get_offer_price(product.price)
                    updated = True
            
            if updated:
                product.save()
                updated_count += 1
                price_info = f'${product.price:,}'
                if product.offer_price:
                    price_info += f' (Oferta: ${product.offer_price:,})'
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  [OK] {product.name}: Stock={product.stock}, Precio={price_info}'
                    )
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'Total productos actualizados: {updated_count}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

