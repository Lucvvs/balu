"""
Management command para cargar productos iniciales desde imágenes en static/img/productos/

Uso:
    python manage.py load_initial_products

El comando espera encontrar las imágenes en static/img/productos/ con el siguiente formato:
- producto-nombre.png (imagen principal)
- producto-nombre-2.png, producto-nombre-3.png, etc. (imágenes secundarias)

Los datos de los productos se definen en este archivo en PRODUCTS_DATA.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files import File
from django.core.files.images import ImageFile
from shop.models import Product, Category, Brand, ProductImage
from pathlib import Path
import os
import shutil


# Datos iniciales de productos
# Modifica esta lista según tus productos reales
PRODUCTS_DATA = [
    {
        'name': 'Casco Shoei X-Spirit III',
        'category': 'Equipamiento',
        'brand': 'Shoei',
        'short_description': 'Casco premium de fibra de carbono',
        'description': 'Casco de alta gama con tecnología avanzada. Certificado DOT y ECE. Visera anti-empañante incluida.',
        'price': 450000,
        'offer_price': 399000,
        'stock': 5,
        'available_sizes': 'S,M,L,XL',
        'is_offer': True,
        'is_best_seller': True,
        'is_active': True,
        'image_files': ['casco-shoei-1.png', 'casco-shoei-2.png', 'casco-shoei-3.png']
    },
    # Agrega más productos aquí siguiendo el mismo formato
]


class Command(BaseCommand):
    help = 'Carga productos iniciales desde imágenes en static/img/productos/'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='static/img/productos',
            help='Directorio con imágenes de productos (default: static/img/productos)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización de productos existentes',
        )

    def handle(self, *args, **options):
        data_dir = Path(options['data_dir'])
        
        if not data_dir.exists():
            self.stdout.write(
                self.style.WARNING(f'Directorio {data_dir} no existe. Creándolo...')
            )
            data_dir.mkdir(parents=True, exist_ok=True)
            self.stdout.write(
                self.style.SUCCESS(f'Directorio creado. Agrega tus imágenes en: {data_dir}')
            )
            return

        # Media directory para productos
        media_products_dir = settings.MEDIA_ROOT / 'products'
        media_products_dir.mkdir(parents=True, exist_ok=True)

        created_count = 0
        updated_count = 0
        error_count = 0

        for product_data in PRODUCTS_DATA:
            try:
                # Obtener categoría y marca
                try:
                    category = Category.objects.get(name=product_data['category'])
                except Category.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Categoría '{product_data['category']}' no existe. "
                            "Ejecuta primero: python manage.py loaddata initial_categories.json"
                        )
                    )
                    error_count += 1
                    continue

                brand = None
                if product_data.get('brand'):
                    try:
                        brand = Brand.objects.get(name=product_data['brand'])
                    except Brand.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Marca '{product_data['brand']}' no existe. "
                                "El producto se creará sin marca."
                            )
                        )

                # Verificar si el producto ya existe
                product, created = Product.objects.get_or_create(
                    name=product_data['name'],
                    defaults={
                        'category': category,
                        'brand': brand,
                        'short_description': product_data.get('short_description', ''),
                        'description': product_data.get('description', ''),
                        'price': product_data.get('price', 0),
                        'offer_price': product_data.get('offer_price'),
                        'stock': product_data.get('stock', 0),
                        'available_sizes': product_data.get('available_sizes', ''),
                        'is_offer': product_data.get('is_offer', False),
                        'is_best_seller': product_data.get('is_best_seller', False),
                        'is_active': product_data.get('is_active', True),
                    }
                )

                if not created and not options['force']:
                    self.stdout.write(
                        self.style.WARNING(f'Producto "{product.name}" ya existe. Usa --force para actualizar.')
                    )
                    continue
                elif not created and options['force']:
                    # Actualizar producto existente
                    for key, value in product_data.items():
                        if key not in ['name', 'image_files']:
                            if key == 'category':
                                setattr(product, key, category)
                            elif key == 'brand':
                                setattr(product, key, brand)
                            else:
                                setattr(product, key, value)
                    product.save()
                    updated_count += 1
                else:
                    created_count += 1

                # Procesar imágenes
                image_files = product_data.get('image_files', [])
                if not image_files:
                    # Si no hay imágenes especificadas, buscar automáticamente
                    # Buscar archivos que empiecen con el slug del producto
                    slug_prefix = product.slug.replace('-', '_')  # Variaciones de slug
                    slug_alt = product.slug
                    found_files = []
                    for ext in ['png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG']:
                        # Buscar con diferentes variaciones
                        for prefix in [slug_prefix, slug_alt, slug_prefix.replace('_', '-'), slug_alt.replace('-', '_')]:
                            pattern = f"{prefix}*.{ext}"
                            matching_files = list(data_dir.glob(pattern))
                            if matching_files:
                                found_files.extend([f.name for f in sorted(matching_files)])
                                break
                        if found_files:
                            break
                    if found_files:
                        # Ordenar: primero la que no tiene número o tiene -1, luego las demás
                        def sort_key(fname):
                            if '-1.' in fname or fname.endswith(f'.{ext}') and not any(f'-{i}.' in fname for i in range(2, 10)):
                                return (0, fname)
                            return (1, fname)
                        image_files = sorted(list(set(found_files)), key=sort_key)

                # Limpiar imágenes existentes si se fuerza actualización
                if options['force'] and not created:
                    ProductImage.objects.filter(product=product).delete()

                # Cargar imágenes
                for idx, image_file in enumerate(image_files):
                    source_path = data_dir / image_file
                    
                    if not source_path.exists():
                        self.stdout.write(
                            self.style.WARNING(
                                f'Imagen {image_file} no encontrada para producto {product.name}'
                            )
                        )
                        continue

                    # Copiar imagen a media/products/
                    destination_path = media_products_dir / image_file
                    
                    try:
                        # Crear registro de ProductImage
                        is_primary = (idx == 0)  # Primera imagen es principal
                        
                        # Si ya existe una imagen principal, marcar como False
                        if is_primary and ProductImage.objects.filter(product=product, is_primary=True).exists():
                            # Asegurar que solo una sea principal
                            ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)
                        
                        # Leer y guardar la imagen directamente desde el origen
                        # Django se encargará de copiarla a media/products/ automáticamente
                        with open(source_path, 'rb') as f:
                            django_file = ImageFile(f, name=image_file)
                            product_image = ProductImage(
                                product=product,
                                is_primary=is_primary,
                                order=idx
                            )
                            # Guardar archivo en el campo ImageField
                            # Django copiará el archivo a media/products/ automáticamente
                            product_image.image.save(
                                image_file,
                                django_file,
                                save=True
                            )
                            django_file.close()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Imagen {image_file} cargada{" (principal)" if is_primary else ""}'
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error al cargar {image_file}: {str(e)}')
                        )
                        error_count += 1

                action = "Creado" if created else "Actualizado"
                self.stdout.write(
                    self.style.SUCCESS(f'{action}: {product.name} (Stock: {product.stock})')
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error al procesar {product_data.get("name", "producto desconocido")}: {str(e)}')
                )
                error_count += 1
                continue

        # Resumen
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Resumen de carga:'))
        self.stdout.write(self.style.SUCCESS(f'  Productos creados: {created_count}'))
        if updated_count > 0:
            self.stdout.write(self.style.SUCCESS(f'  Productos actualizados: {updated_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'  Errores: {error_count}'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        
        if created_count == 0 and updated_count == 0 and error_count == 0:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'No se procesaron productos. Verifica que:'
            ))
            self.stdout.write(self.style.WARNING(
                '  1. PRODUCTS_DATA en load_initial_products.py tenga datos'
            ))
            self.stdout.write(self.style.WARNING(
                '  2. Las categorías y marcas existan (ejecuta loaddata)'
            ))
            self.stdout.write(self.style.WARNING(
                f'  3. Las imágenes estén en {data_dir}'
            ))

