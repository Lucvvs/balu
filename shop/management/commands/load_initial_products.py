"""
Management command para cargar productos iniciales detectando automáticamente desde imágenes

Uso:
    python manage.py load_initial_products                    # Cargar productos desde imágenes
    python manage.py load_initial_products --force           # Actualizar productos existentes
    python manage.py load_initial_products --clean           # Limpiar y cargar desde cero
    python manage.py load_initial_products --data-dir ruta   # Especificar directorio de imágenes

El comando:
1. (Opcional) Limpia productos existentes si se usa --clean
2. Escanea el directorio de imágenes (static/img/productos/ por defecto)
3. Detecta automáticamente productos basándose en los nombres de archivo
4. Asigna categorías y marcas según patrones en los nombres
5. Asigna imágenes globales (AccesoriosShaftGLOB.webp, soportemaletaGLOB.webp)
6. Crea/actualiza los productos en la base de datos
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files import File
from django.core.files.images import ImageFile
from shop.models import Product, Category, Brand, ProductImage, OrderItem
from pathlib import Path
import os
import re
from collections import defaultdict


class Command(BaseCommand):
    help = 'Carga productos iniciales detectando automáticamente desde imágenes'

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
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Eliminar todos los productos existentes antes de cargar (limpieza completa)',
        )

    def detect_product_info(self, filename):
        """
        Detecta información del producto desde el nombre del archivo
        Retorna: (product_name, brand_name, category_name, is_global)
        """
        filename_upper = filename.upper()
        base_name = Path(filename).stem
        
        # Imágenes globales
        if 'ACCESORIOSSHAFTGLOB' in filename_upper:
            return None, 'SHAFT', 'Cascos', True
        if 'SOPORTEMALETAGLOB' in filename_upper:
            return None, '4RS', 'Maletas', True
        
        # Detectar marca y categoría
        brand = None
        category = None
        
        # Marcas
        if filename_upper.startswith('HRO'):
            brand = 'HRO'
            category = 'Cascos'
        elif filename_upper.startswith('SHAFT') or filename_upper.startswith('SHAFT'):
            brand = 'SHAFT'
            category = 'Cascos'
        elif 'KOVIX' in filename_upper:
            brand = 'KOVIX'
            category = 'Seguridad'
        elif 'MALETA' in filename_upper or filename_upper.startswith('E'):
            brand = '4RS'
            category = 'Maletas'
        elif 'MOTOCENTRIC' in filename_upper or 'MC' in filename_upper or 'MUSLERA' in filename_upper or 'PROTECTO' in filename_upper or 'CUBRE' in filename_upper:
            brand = 'motocentric'
            category = 'Accesorios'
        
        # Productos específicos
        product_name = None
        
        # Cascos HRO
        if brand == 'HRO':
            if '514' in base_name:
                if 'BILT' in filename_upper:
                    product_name = 'Casco HRO 514 BILT'
                elif 'GRI' in filename_upper:  # Gris, GRis, GRIS, etc.
                    product_name = 'Casco HRO 514 Gris'
                elif 'MORA' in filename_upper:
                    product_name = 'Casco HRO 514 Mora'
                elif 'NEGRO' in filename_upper and 'ROJO' in filename_upper:
                    product_name = 'Casco HRO 514 Negro-Rojo'
        
        # Cascos SHAFT
        elif brand == 'SHAFT':
            if '502' in base_name:
                if 'SP' in filename_upper and 'AZUL' in filename_upper:
                    product_name = 'Casco SHAFT 502 SP Azul'
                elif 'NEGRIS' in filename_upper or ('NEGRO' in filename_upper and 'SPIKE' not in filename_upper):
                    product_name = 'Casco SHAFT 502 Negris'
                elif 'ROSADO' in filename_upper:
                    product_name = 'Casco SHAFT 502 Rosado'
                elif 'SPIKE' in filename_upper:
                    product_name = 'Casco SHAFT 502 Spike Rojo-Negro'
            elif '560' in base_name or 'EVO' in filename_upper:
                product_name = 'Casco SHAFT 560 EVO Negro-Dorado'
        
        # Maletas 4RS
        elif brand == '4RS':
            if 'E570' in base_name or '570' in base_name:
                product_name = 'Maleta 4RS E570 Tipo AL'
            elif 'E63' in base_name or '63' in base_name:
                product_name = 'Maleta 4RS E63 Parrilla'
            elif 'E760' in base_name or '760' in base_name:
                product_name = 'Maleta 4RS E760'
        
        # Accesorios motocentric
        elif brand == 'motocentric':
            if 'BOLSO' in filename_upper and 'ESTANQUE' in filename_upper:
                product_name = 'Bolso Estanque motocentric'
            elif 'MUSLERA' in filename_upper:
                product_name = 'Muslera motocentric'
            elif 'PROTECTO' in filename_upper and 'PATA' in filename_upper:
                product_name = 'Protector Pata motocentric'
            elif 'CUBRE' in filename_upper and 'ESTANQUE' in filename_upper:
                product_name = 'Cubre Estanque Goma motocentric'
        
        # Seguridad KOVIX
        elif brand == 'KOVIX':
            if 'KN1' in base_name.upper() or 'KNN1' in base_name.upper():
                if 'NEGRO' in filename_upper:
                    product_name = 'Candado KOVIX KN1 Negro'
                else:
                    product_name = 'Candado KOVIX KN1 Amarillo'
            elif 'KNX10' in base_name or 'KNX' in base_name:
                product_name = 'Candado KOVIX KNX10 Metal'
            elif 'KT6' in base_name:
                if 'NEGRO' in filename_upper:
                    product_name = 'Candado KOVIX KT6 Negro'
                else:
                    product_name = 'Candado KOVIX KT6 Verde'
            elif 'SOPORTE' in filename_upper:
                product_name = 'Soporte KOVIX'
        
        # Otros accesorios
        if not product_name and not brand:
            if 'ANTIFOG' in filename_upper:
                product_name = 'AntiFOG'
                category = 'Accesorios'
            elif 'ANTILLUVIA' in filename_upper:
                product_name = 'Antilluvia'
                category = 'Accesorios'
            elif 'INTERLUVIN' in filename_upper:
                product_name = 'Interluvin'
                category = 'Accesorios'
            elif 'KITREPLLANT' in filename_upper or ('KIT' in filename_upper and 'REP' in filename_upper and 'LLANT' in filename_upper):
                product_name = 'Kit de Reparación de Llantas'
                category = 'Accesorios'
            elif 'TRENZA' in filename_upper:
                product_name = 'Trenzas'
                category = 'Accesorios'
        
        return product_name, brand, category, False

    def group_images_by_product(self, image_files):
        """
        Agrupa imágenes por producto
        Retorna: dict {product_key: [lista de archivos]}
        """
        products = defaultdict(list)
        global_images = defaultdict(list)
        
        for img_file in image_files:
            if img_file.name.startswith('.'):
                continue
            
            product_name, brand, category, is_global = self.detect_product_info(img_file.name)
            
            if is_global:
                # Imagen global: se asigna a todos los productos de esa marca/categoría
                key = f"{brand}_{category}"
                global_images[key].append(img_file)
            elif product_name:
                # Producto específico
                # Para trenzas, agrupar todas las variantes de color en un solo producto
                if product_name == 'Trenzas':
                    key = f"{product_name}_{brand or 'None'}_{category}"
                else:
                    key = f"{product_name}_{brand}_{category}"
                products[key].append(img_file)
        
        return products, global_images

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
                import os
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
        
        # Resolver ruta del directorio de datos
        # Si es una ruta relativa, resolverla desde BASE_DIR
        data_dir_str = options['data_dir']
        data_dir = Path(data_dir_str)
        
        # Si no es una ruta absoluta, resolverla desde BASE_DIR
        if not data_dir.is_absolute():
            data_dir = Path(settings.BASE_DIR) / data_dir_str
        
        if not data_dir.exists():
            self.stdout.write(
                self.style.ERROR(f'Directorio {data_dir} no existe.')
            )
            self.stdout.write(
                self.style.WARNING(f'BASE_DIR: {settings.BASE_DIR}')
            )
            return

        # Media directory para productos
        media_products_dir = Path(settings.MEDIA_ROOT) / 'products'
        media_products_dir.mkdir(parents=True, exist_ok=True)

        # Obtener todas las imágenes
        image_extensions = [
            '*.webp', '*.WEBP',
            '*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG',
        ]
        image_files = []
        for ext in image_extensions:
            image_files.extend(data_dir.glob(ext))
        
        if not image_files:
            self.stdout.write(
                self.style.WARNING(f'No se encontraron imágenes en {data_dir}')
            )
            return

        # Agrupar imágenes por producto
        products_dict, global_images = self.group_images_by_product(image_files)
        
        self.stdout.write(self.style.SUCCESS(f'Se encontraron {len(products_dict)} productos únicos'))
        self.stdout.write(self.style.SUCCESS(f'Se encontraron {len(global_images)} grupos de imágenes globales'))

        created_count = 0
        updated_count = 0
        error_count = 0

        # Procesar cada producto
        for product_key, image_list in products_dict.items():
            try:
                # Extraer información del key
                parts = product_key.split('_', 2)
                if len(parts) < 3:
                    continue
                
                product_name = parts[0]
                brand_name = parts[1]
                category_name = parts[2]
                
                # Obtener categoría y marca
                try:
                    category = Category.objects.get(name=category_name)
                except Category.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"Categoría '{category_name}' no existe.")
                    )
                    error_count += 1
                    continue

                brand = None
                if brand_name:
                    try:
                        brand = Brand.objects.get(name=brand_name)
                    except Brand.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"Marca '{brand_name}' no existe.")
                        )

                # Ordenar imágenes: la primera sin número o con 1 es la principal
                def sort_key(fname):
                    name_lower = fname.name.lower()
                    # Para trenzas, ordenar por color (Amarilla, Azul, Morada, Roja, Rosa)
                    if product_name == 'Trenzas':
                        color_order = {'amarilla': 1, 'azul': 2, 'morada': 3, 'roja': 4, 'rosa': 5}
                        for color, order in color_order.items():
                            if color in name_lower:
                                return (0, order, fname.name)
                        return (0, 99, fname.name)
                    
                    # Buscar número al final del nombre
                    match = re.search(r'(\d+)(\.(png|jpg|jpeg|webp))?$', name_lower)
                    if match:
                        num = int(match.group(1))
                        return (0 if num == 1 else 1, num, fname.name)
                    return (0, 0, fname.name)
                
                image_list_sorted = sorted(image_list, key=sort_key)

                # Detectar colores para trenzas
                available_colors = None
                if product_name == 'Trenzas':
                    colors = []
                    for img_file in image_list:
                        filename_upper = img_file.name.upper()
                        if 'AMARILL' in filename_upper:
                            colors.append('Amarilla')
                        elif 'AZUL' in filename_upper:
                            colors.append('Azul')
                        elif 'MORAD' in filename_upper:
                            colors.append('Morada')
                        elif 'ROJA' in filename_upper and 'ROS' not in filename_upper:
                            colors.append('Roja')
                        elif 'ROSA' in filename_upper or 'ROS' in filename_upper:
                            colors.append('Rosa')
                    if colors:
                        available_colors = ','.join(sorted(set(colors)))
                
                # Verificar si el producto ya existe
                product_defaults = {
                    'category': category,
                    'brand': brand,
                    'short_description': f'{product_name} - {category_name}',
                    'description': f'{product_name} de alta calidad. {category.description if category.description else ""}',
                    'price': 0,  # Se debe actualizar manualmente
                    'stock': 0,  # Se debe actualizar manualmente
                    'is_active': True,
                }
                
                # Agregar colores disponibles para trenzas
                if available_colors:
                    product_defaults['available_sizes'] = available_colors
                
                product, created = Product.objects.get_or_create(
                    name=product_name,
                    defaults=product_defaults
                )
                
                # Si el producto ya existe y es Trenzas, actualizar colores disponibles
                if not created and product_name == 'Trenzas' and available_colors:
                    product.available_sizes = available_colors
                    product.save()

                if not created and not options['force']:
                    self.stdout.write(
                        self.style.WARNING(f'Producto "{product.name}" ya existe. Usa --force para actualizar.')
                    )
                    continue
                elif not created and options['force']:
                    # Actualizar producto existente
                    product.category = category
                    product.brand = brand
                    product.save()
                    updated_count += 1
                    
                    # Limpiar imágenes existentes de la BD (se recargarán)
                    ProductImage.objects.filter(product=product).delete()
                else:
                    created_count += 1

                # Cargar imágenes del producto
                # Si se usa --force, ya se eliminaron las imágenes arriba
                # Si no se usa --force, verificar duplicados
                for idx, img_file in enumerate(image_list_sorted):
                    try:
                        is_primary = (idx == 0)
                        
                        # Verificar si la imagen ya existe para evitar duplicados (solo si no se usa --force)
                        if not options['force']:
                            existing_image = ProductImage.objects.filter(
                                product=product,
                                image__icontains=img_file.stem
                            ).first()
                            
                            if existing_image:
                                # Si existe, solo actualizar is_primary y order si es necesario
                                if existing_image.is_primary != is_primary or existing_image.order != idx:
                                    existing_image.is_primary = is_primary
                                    existing_image.order = idx
                                    existing_image.save()
                                continue
                        
                        # Leer y guardar la imagen
                        # Convertir Path a string para open()
                        img_path = str(img_file) if isinstance(img_file, Path) else img_file
                        with open(img_path, 'rb') as f:
                            django_file = ImageFile(f, name=img_file.name)
                            product_image = ProductImage(
                                product=product,
                                is_primary=is_primary,
                                order=idx
                            )
                            product_image.image.save(
                                img_file.name,
                                django_file,
                                save=True
                            )
                            django_file.close()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  [OK] Imagen {img_file.name} cargada{" (principal)" if is_primary else ""}'
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error al cargar {img_file.name}: {str(e)}')
                        )

                # Asignar imágenes globales
                global_key = f"{brand_name}_{category_name}"
                if global_key in global_images:
                    for global_img in global_images[global_key]:
                        try:
                            # Convertir Path a string para open()
                            global_img_path = str(global_img) if isinstance(global_img, Path) else global_img
                            with open(global_img_path, 'rb') as f:
                                django_file = ImageFile(f, name=global_img.name)
                                product_image = ProductImage(
                                    product=product,
                                    is_primary=False,
                                    order=999  # Al final
                                )
                                product_image.image.save(
                                    global_img.name,
                                    django_file,
                                    save=True
                                )
                                django_file.close()
                            
                            self.stdout.write(
                                self.style.SUCCESS(f'  [OK] Imagen global {global_img.name} asignada')
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Error al cargar imagen global {global_img.name}: {str(e)}')
                            )

                action = "Creado" if created else "Actualizado"
                self.stdout.write(
                    self.style.SUCCESS(f'{action}: {product.name} ({len(image_list)} imágenes)')
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error al procesar {product_key}: {str(e)}')
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
        
        if created_count > 0 or updated_count > 0:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'IMPORTANTE: Revisa y actualiza manualmente los precios y stock de los productos en el admin de Django.'
            ))

