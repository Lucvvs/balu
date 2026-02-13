"""
Comando para cargar métodos de envío y pago iniciales por defecto
Incluye imágenes desde static/img/

Uso:
    python manage.py load_payment_shipping_methods
"""

import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from shop.models import ShippingMethod, PaymentMethod


class Command(BaseCommand):
    help = 'Carga métodos de envío y pago iniciales por defecto con imágenes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización de métodos existentes',
        )

    def copy_image(self, source_path, dest_dir, filename):
        """
        Copia una imagen desde static/img/ a media/payment_methods/
        
        Returns:
            File: Objeto File de Django o None si no existe
        """
        source_file = Path(settings.BASE_DIR) / 'static' / 'img' / source_path
        dest_dir_path = Path(settings.MEDIA_ROOT) / dest_dir
        
        # Crear directorio si no existe
        dest_dir_path.mkdir(parents=True, exist_ok=True)
        
        if source_file.exists():
            try:
                # Abrir el archivo y crear un objeto File de Django
                with open(source_file, 'rb') as f:
                    django_file = File(f, name=filename)
                    return django_file
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'   [ADVERTENCIA] No se pudo leer {source_path}: {str(e)}'))
                return None
        else:
            self.stdout.write(self.style.WARNING(f'   [ADVERTENCIA] Imagen no encontrada: {source_file}'))
            return None

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
        
        # Métodos de pago con imágenes
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('2. Cargando métodos de pago con imágenes...'))
        
        payment_methods = [
            {
                'name': 'Efectivo',
                'description': 'Pago en efectivo al momento de la entrega o retiro.',
                'is_active': True,
                'image_source': 'efectivo.png',
            },
            {
                'name': 'Transferencia Bancaria',
                'description': 'Realiza una transferencia bancaria. Te enviaremos los datos por email.',
                'is_active': True,
                'image_source': 'transferencia.png',
            },
            {
                'name': 'Tarjeta de Crédito',
                'description': 'Pago con tarjeta de crédito a través de Mercado Pago.',
                'is_active': True,
                'image_source': 'credito.png',
            },
            {
                'name': 'Tarjeta de Débito',
                'description': 'Pago con tarjeta de débito a través de Mercado Pago.',
                'is_active': True,
                'image_source': 'debito.png',
            },
        ]
        
        for method_data in payment_methods:
            # Extraer image_source antes de crear el método
            image_source = method_data.pop('image_source', None)
            
            method, created = PaymentMethod.objects.get_or_create(
                name=method_data['name'],
                defaults=method_data
            )
            
            # Copiar imagen si existe y el método fue creado o se está forzando actualización
            if image_source and (created or options['force']):
                django_file = self.copy_image(
                    image_source,
                    'payment_methods',
                    image_source
                )
                if django_file:
                    method.image.save(image_source, django_file, save=True)
                    self.stdout.write(self.style.SUCCESS(f'      → Imagen copiada: {image_source}'))
            
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
        self.stdout.write(self.style.WARNING('NOTA: Las imágenes se copiaron desde static/img/ a media/payment_methods/'))
