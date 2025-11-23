"""
Comando completo para cargar todos los datos iniciales
Ejecuta en orden: categorías, marcas, productos

Uso:
    python manage.py load_initial_data
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Carga todos los datos iniciales (categorías, marcas y productos)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-products',
            action='store_true',
            help='Saltar carga de productos',
        )
        parser.add_argument(
            '--force-products',
            action='store_true',
            help='Forzar actualización de productos existentes',
        )
        parser.add_argument(
            '--skip-featured',
            action='store_true',
            help='Saltar configuración de ofertas y más vendidos',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Cargando datos iniciales...'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        
        # 1. Cargar categorías
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('1. Cargando categorías...'))
        try:
            call_command('loaddata', 'shop/fixtures/initial_categories.json', verbosity=1)
            self.stdout.write(self.style.SUCCESS('   [OK] Categorías cargadas'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   [ERROR] Error: {str(e)}'))
        
        # 2. Cargar marcas
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('2. Cargando marcas...'))
        try:
            call_command('loaddata', 'shop/fixtures/initial_brands.json', verbosity=1)
            self.stdout.write(self.style.SUCCESS('   [OK] Marcas cargadas'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   [ERROR] Error: {str(e)}'))
        
        # 3. Cargar productos
        if not options['skip_products']:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('3. Cargando productos...'))
            try:
                force_args = ['--force'] if options['force_products'] else []
                call_command('load_initial_products', *force_args, verbosity=1)
                self.stdout.write(self.style.SUCCESS('   [OK] Productos cargados'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   [ERROR] Error: {str(e)}'))
        
        # 4. Asignar precios y stock
        if not options['skip_products']:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('4. Asignando precios y stock...'))
            try:
                call_command('set_product_prices', verbosity=1)
                self.stdout.write(self.style.SUCCESS('   [OK] Precios y stock asignados'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   [ERROR] Error: {str(e)}'))
        
        # 5. Corregir imágenes principales
        if not options['skip_products']:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('5. Corrigiendo imágenes principales...'))
            try:
                call_command('fix_primary_images', verbosity=1)
                self.stdout.write(self.style.SUCCESS('   [OK] Imágenes principales corregidas'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   [ERROR] Error: {str(e)}'))
        
        # 6. Configurar ofertas y más vendidos
        if not options['skip_featured'] and not options['skip_products']:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('6. Configurando ofertas y más vendidos...'))
            try:
                call_command('set_featured_products', verbosity=1)
                self.stdout.write(self.style.SUCCESS('   [OK] Ofertas y más vendidos configurados'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   [ERROR] Error: {str(e)}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('¡Carga inicial completada!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))

