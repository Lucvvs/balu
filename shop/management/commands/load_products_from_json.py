"""
Comando para cargar productos desde un archivo JSON con configuración completa

Uso:
    python manage.py load_products_from_json                    # Cargar desde shop/fixtures/initial_products.json
    python manage.py load_products_from_json --file ruta/json   # Especificar archivo JSON personalizado
    python manage.py load_products_from_json --force           # Actualizar productos existentes
    python manage.py load_products_from_json --clean           # Limpiar todos los productos antes de cargar
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files.images import ImageFile
from shop.models import Product, Category, Brand, ProductImage, OrderItem
from pathlib import Path
import json
import os


class Command(BaseCommand):
    help = 'Carga productos desde un archivo JSON con configuración completa de campos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='shop/fixtures/initial_products.json',
            help='Ruta al archivo JSON con productos (default: shop/fixtures/initial_products.json)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización de productos existentes',
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Eliminar todos los productos existentes antes de cargar (limpieza completa)',
        )
        parser.add_argument(
            '--data-dir',
            type=str,
            default='static/img/productos',
            help='Directorio con imágenes de productos (default: static/img/productos)'
        )

    def handle(self, *args, **options):
        # Limpiar productos existentes si se solicita
        if options['clean']:
            product_count = Product.objects.count()
            if product_count > 0:
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('=' * 60))
                self.stdout.write(self.style.WARNING(f'Limpiando {product_count} productos existentes...'))
                self.stdout.write(self.style.WARNING('=' * 60))
                
                # Eliminar primero los OrderItem que referencian productos
                order_items_count = OrderItem.objects.count()
                if order_items_count > 0:
                    self.stdout.write(self.style.WARNING(f'Eliminando {order_items_count} items de pedidos...'))
                    OrderItem.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'[OK] {order_items_count} items de pedidos eliminados'))
                
                # Ahora eliminar productos
                Product.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'[OK] {product_count} productos eliminados'))
                
                # Limpiar archivos físicos de imágenes
                media_products_dir = Path(settings.MEDIA_ROOT) / 'products'
                if media_products_dir.exists():
                    deleted_files = 0
                    for img_file in media_products_dir.glob('*'):
                        if img_file.is_file() and img_file.name != '.gitkeep':
                            try:
                                img_file.unlink()
                                deleted_files += 1
                            except Exception as e:
                                self.stdout.write(
                                    self.style.WARNING(f'No se pudo eliminar {img_file.name}: {str(e)}')
                                )
                    if deleted_files > 0:
                        self.stdout.write(self.style.SUCCESS(f'[OK] {deleted_files} archivos físicos eliminados'))
                
                self.stdout.write('')
            else:
                self.stdout.write(self.style.SUCCESS('No hay productos para limpiar.'))
                self.stdout.write('')

        # Resolver ruta del archivo JSON
        json_file_str = options['file']
        json_file = Path(json_file_str)
        
        # Si no es una ruta absoluta, resolverla desde BASE_DIR
        if not json_file.is_absolute():
            json_file = Path(settings.BASE_DIR) / json_file_str
        
        if not json_file.exists():
            raise CommandError(f'El archivo JSON no existe: {json_file}')
        
        # Resolver ruta del directorio de imágenes
        data_dir_str = options['data_dir']
        data_dir = Path(data_dir_str)
        
        # Si no es una ruta absoluta, resolverla desde BASE_DIR
        if not data_dir.is_absolute():
            data_dir = Path(settings.BASE_DIR) / data_dir_str
        
        if not data_dir.exists():
            raise CommandError(f'El directorio de imágenes no existe: {data_dir}')
        
        # Leer archivo JSON
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Cargando productos desde JSON...'))
        self.stdout.write(self.style.SUCCESS(f'Archivo: {json_file}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f'Error al leer el archivo JSON: {str(e)}')
        except Exception as e:
            raise CommandError(f'Error al abrir el archivo JSON: {str(e)}')
        
        # Filtrar productos (eliminar comentarios que empiezan con _)
        products_data = [
            {k: v for k, v in product.items() if not k.startswith('_')}
            for product in products_data
        ]
        
        # Media directory para productos
        media_products_dir = Path(settings.MEDIA_ROOT) / 'products'
        media_products_dir.mkdir(parents=True, exist_ok=True)
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        # Procesar cada producto
        for product_data in products_data:
            try:
                # Validar campos requeridos
                required_fields = ['name', 'category', 'price', 'stock']
                for field in required_fields:
                    if field not in product_data:
                        self.stdout.write(
                            self.style.ERROR(f'Producto sin campo requerido "{field}": {product_data.get("name", "Sin nombre")}')
                        )
                        error_count += 1
                        continue
                
                # Obtener categoría
                try:
                    category = Category.objects.get(name=product_data['category'])
                except Category.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"Categoría '{product_data['category']}' no existe para producto '{product_data['name']}'")
                    )
                    error_count += 1
                    continue
                
                # Obtener marca (opcional)
                brand = None
                if product_data.get('brand'):
                    try:
                        brand = Brand.objects.get(name=product_data['brand'])
                    except Brand.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"Marca '{product_data['brand']}' no existe para producto '{product_data['name']}' (se creará sin marca)")
                        )
                
                # Preparar datos del producto
                product_defaults = {
                    'category': category,
                    'brand': brand,
                    'short_description': product_data.get('short_description', product_data['name']),
                    'description': product_data.get('description', product_data.get('short_description', product_data['name'])),
                    'price': int(product_data['price']),
                    'offer_price': int(product_data['offer_price']) if product_data.get('offer_price') is not None else None,
                    'stock': int(product_data['stock']),
                    'available_sizes': product_data.get('available_sizes', ''),
                    'is_active': product_data.get('is_active', True),
                    'is_offer': product_data.get('is_offer', False),
                    'is_best_seller': product_data.get('is_best_seller', False),
                    'offer_order': int(product_data.get('offer_order', 0)),
                    'featured_order': int(product_data.get('featured_order', 0)),
                }
                
                # Crear o actualizar producto
                product, created = Product.objects.get_or_create(
                    name=product_data['name'],
                    defaults=product_defaults
                )
                
                if not created and not options['force']:
                    self.stdout.write(
                        self.style.WARNING(f'Producto "{product.name}" ya existe. Usa --force para actualizar.')
                    )
                    continue
                elif not created and options['force']:
                    # Actualizar producto existente
                    for key, value in product_defaults.items():
                        setattr(product, key, value)
                    product.save()
                    updated_count += 1
                    
                    # Limpiar imágenes existentes de la BD (se recargarán)
                    ProductImage.objects.filter(product=product).delete()
                else:
                    created_count += 1
                
                # Cargar imágenes
                images_data = product_data.get('images', [])
                if images_data:
                    # Ordenar imágenes por 'order'
                    images_data = sorted(images_data, key=lambda x: x.get('order', 0))
                    
                    for img_data in images_data:
                        img_filename = img_data['file']
                        img_path = data_dir / img_filename
                        
                        if not img_path.exists():
                            self.stdout.write(
                                self.style.WARNING(f'  [ADVERTENCIA] Imagen no encontrada: {img_filename}')
                            )
                            continue
                        
                        try:
                            is_primary = img_data.get('is_primary', False)
                            img_order = img_data.get('order', 0)
                            
                            # Verificar si la imagen ya existe (solo si no se usa --force)
                            if not options['force']:
                                existing_image = ProductImage.objects.filter(
                                    product=product,
                                    image__icontains=img_path.stem
                                ).first()
                                
                                if existing_image:
                                    # Si existe, solo actualizar is_primary y order si es necesario
                                    if existing_image.is_primary != is_primary or existing_image.order != img_order:
                                        existing_image.is_primary = is_primary
                                        existing_image.order = img_order
                                        existing_image.save()
                                    continue
                            
                            # Leer y guardar la imagen
                            with open(img_path, 'rb') as f:
                                django_file = ImageFile(f, name=img_filename)
                                product_image = ProductImage(
                                    product=product,
                                    is_primary=is_primary,
                                    order=img_order
                                )
                                product_image.image.save(
                                    img_filename,
                                    django_file,
                                    save=True
                                )
                                django_file.close()
                            
                            primary_tag = " (principal)" if is_primary else ""
                            self.stdout.write(
                                self.style.SUCCESS(f'  [OK] Imagen {img_filename} cargada{primary_tag}')
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'  [ERROR] Error al cargar imagen {img_filename}: {str(e)}')
                            )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  [ADVERTENCIA] Producto "{product.name}" no tiene imágenes definidas')
                    )
                
                action = "Creado" if created else "Actualizado"
                price_info = f'${product.price:,}'
                if product.offer_price:
                    price_info += f' (Oferta: ${product.offer_price:,})'
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{action}: {product.name} | Stock: {product.stock} | Precio: {price_info}'
                    )
                )
                self.stdout.write('')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error al procesar producto {product_data.get("name", "Sin nombre")}: {str(e)}')
                )
                error_count += 1
                continue
        
        # Resumen
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Resumen de carga:'))
        self.stdout.write(self.style.SUCCESS(f'  Productos creados: {created_count}'))
        if updated_count > 0:
            self.stdout.write(self.style.SUCCESS(f'  Productos actualizados: {updated_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'  Errores: {error_count}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

