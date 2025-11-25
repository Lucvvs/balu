"""
Comando completo para cargar todos los datos iniciales
Ejecuta en orden: categorías, marcas, productos

Uso:
    python manage.py load_initial_data                              # Carga desde JSON (recomendado)
    python manage.py load_initial_data --auto-detect               # Usa detección automática desde imágenes
    python manage.py load_initial_data --force-products            # Forzar actualización de productos
    python manage.py load_initial_data --clean-products            # Limpiar productos antes de cargar
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
            '--clean-products',
            action='store_true',
            help='Limpiar todos los productos existentes antes de cargar',
        )
        parser.add_argument(
            '--auto-detect',
            action='store_true',
            help='Usar detección automática desde imágenes en lugar de JSON (método anterior)',
        )
        parser.add_argument(
            '--skip-featured',
            action='store_true',
            help='Saltar configuración de ofertas y más vendidos (solo para auto-detect)',
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
                if options['auto_detect']:
                    # Método anterior: detección automática desde imágenes
                    force_args = ['--force'] if options['force_products'] else []
                    call_command('load_initial_products', *force_args, verbosity=1)
                    self.stdout.write(self.style.SUCCESS('   [OK] Productos cargados (detección automática)'))
                    
                    # Asignar precios y stock automáticamente
                    if not options['skip_featured']:
                        self.stdout.write('')
                        self.stdout.write(self.style.SUCCESS('3.1. Asignando precios y stock...'))
                        call_command('set_product_prices', verbosity=1)
                        self.stdout.write(self.style.SUCCESS('   [OK] Precios y stock asignados'))
                        
                        self.stdout.write('')
                        self.stdout.write(self.style.SUCCESS('3.2. Corrigiendo imágenes principales...'))
                        call_command('fix_primary_images', verbosity=1)
                        self.stdout.write(self.style.SUCCESS('   [OK] Imágenes principales corregidas'))
                        
                        self.stdout.write('')
                        self.stdout.write(self.style.SUCCESS('3.3. Configurando ofertas y más vendidos...'))
                        call_command('set_featured_products', verbosity=1)
                        self.stdout.write(self.style.SUCCESS('   [OK] Ofertas y más vendidos configurados'))
                else:
                    # Método nuevo: carga desde JSON (recomendado)
                    force_args = ['--force'] if options['force_products'] else []
                    clean_args = ['--clean'] if options['clean_products'] else []
                    call_command('load_products_from_json', *force_args, *clean_args, verbosity=1)
                    self.stdout.write(self.style.SUCCESS('   [OK] Productos cargados desde JSON (con todos los campos)'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   [ERROR] Error: {str(e)}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('¡Carga inicial completada!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))

