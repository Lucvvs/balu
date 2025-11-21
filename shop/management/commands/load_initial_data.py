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

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Cargando datos iniciales...'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        
        # 1. Cargar categorías
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('1. Cargando categorías...'))
        try:
            call_command('loaddata', 'shop/fixtures/initial_categories.json', verbosity=1)
            self.stdout.write(self.style.SUCCESS('   ✓ Categorías cargadas'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Error: {str(e)}'))
        
        # 2. Cargar marcas
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('2. Cargando marcas...'))
        try:
            call_command('loaddata', 'shop/fixtures/initial_brands.json', verbosity=1)
            self.stdout.write(self.style.SUCCESS('   ✓ Marcas cargadas'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Error: {str(e)}'))
        
        # 3. Cargar productos
        if not options['skip_products']:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('3. Cargando productos...'))
            try:
                force_args = ['--force'] if options['force_products'] else []
                call_command('load_initial_products', *force_args, verbosity=1)
                self.stdout.write(self.style.SUCCESS('   ✓ Productos cargados'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ✗ Error: {str(e)}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('¡Carga inicial completada!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))

