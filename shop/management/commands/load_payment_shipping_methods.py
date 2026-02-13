"""
Comando para cargar métodos de envío y pago iniciales por defecto

Uso:
    python manage.py load_payment_shipping_methods
"""

from django.core.management.base import BaseCommand
from shop.models import ShippingMethod, PaymentMethod


class Command(BaseCommand):
    help = 'Carga métodos de envío y pago iniciales por defecto'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización de métodos existentes',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Cargando métodos de envío y pago...'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        
        # Métodos de envío
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('1. Cargando métodos de envío...'))
        
        shipping_methods = [
            {
                'name': 'Envío a domicilio',
                'description': 'Envío a la dirección que indiques. El costo es de $5.000 CLP.',
                'base_price': 5000,
                'is_active': True,
            },
            {
                'name': 'Retiro en bodega',
                'description': 'Retira tu pedido directamente en nuestra bodega. Sin costo adicional.',
                'base_price': 0,
                'is_active': True,
            },
        ]
        
        for method_data in shipping_methods:
            method, created = ShippingMethod.objects.get_or_create(
                name=method_data['name'],
                defaults=method_data
            )
            if not created and options['force']:
                for key, value in method_data.items():
                    setattr(method, key, value)
                method.save()
                self.stdout.write(self.style.WARNING(f'   [ACTUALIZADO] {method.name}'))
            elif created:
                self.stdout.write(self.style.SUCCESS(f'   [CREADO] {method.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'   [EXISTE] {method.name} (usa --force para actualizar)'))
        
        # Métodos de pago
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('2. Cargando métodos de pago...'))
        
        payment_methods = [
            {
                'name': 'Efectivo',
                'description': 'Pago en efectivo al momento de la entrega o retiro.',
                'is_active': True,
            },
            {
                'name': 'Transferencia Bancaria',
                'description': 'Realiza una transferencia bancaria. Te enviaremos los datos por email.',
                'is_active': True,
            },
            {
                'name': 'Tarjeta de Crédito',
                'description': 'Pago con tarjeta de crédito a través de Mercado Pago.',
                'is_active': True,
            },
            {
                'name': 'Tarjeta de Débito',
                'description': 'Pago con tarjeta de débito a través de Mercado Pago.',
                'is_active': True,
            },
        ]
        
        for method_data in payment_methods:
            method, created = PaymentMethod.objects.get_or_create(
                name=method_data['name'],
                defaults=method_data
            )
            if not created and options['force']:
                for key, value in method_data.items():
                    setattr(method, key, value)
                method.save()
                self.stdout.write(self.style.WARNING(f'   [ACTUALIZADO] {method.name}'))
            elif created:
                self.stdout.write(self.style.SUCCESS(f'   [CREADO] {method.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'   [EXISTE] {method.name} (usa --force para actualizar)'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('¡Métodos cargados correctamente!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('NOTA: Puedes agregar imágenes a los métodos de pago desde el panel de administración.'))
