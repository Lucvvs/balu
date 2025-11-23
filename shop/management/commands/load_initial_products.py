"""
Management command para cargar productos iniciales detectando automáticamente desde imágenes

Uso:
    python manage.py load_initial_products                    # Cargar productos desde imágenes
    python manage.py load_initial_products --force           # Actualizar productos existentes
    python manage.py load_initial_products --data-dir ruta   # Especificar directorio de imágenes

El comando:
1. Escanea el directorio de imágenes (media/productos/ por defecto)
2. Detecta automáticamente productos basándose en los nombres de archivo
3. Asigna categorías y marcas según patrones en los nombres
4. Asigna imágenes globales (AccesoriosShaftGLOB.png, soportemaletaGLOB.png)
5. Crea/actualiza los productos en la base de datos
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files import File
from django.core.files.images import ImageFile
from shop.models import Product, Category, Brand, ProductImage
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
            default='media/productos',
            help='Directorio con imágenes de productos (default: media/productos)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización de productos existentes',
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
                if 'NEGRIS' in filename_upper or 'NEGRO' in filename_upper:
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
            if 'KN1' in base_name:
                product_name = 'Candado KOVIX KN1 Amarillo'
            elif 'KNX10' in base_name or 'KNX' in base_name:
                product_name = 'Candado KOVIX KNX10 Metal'
            elif 'KT6' in base_name:
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
                key = f"{product_name}_{brand}_{category}"
                products[key].append(img_file)
        
        return products, global_images

    def handle(self, *args, **options):
        data_dir = Path(options['data_dir'])
        
        if not data_dir.exists():
            self.stdout.write(
                self.style.ERROR(f'Directorio {data_dir} no existe.')
            )
            return

        # Media directory para productos
        media_products_dir = Path(settings.MEDIA_ROOT) / 'products'
        media_products_dir.mkdir(parents=True, exist_ok=True)

        # Obtener todas las imágenes
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']
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
                    # Buscar número al final del nombre
                    match = re.search(r'(\d+)(\.(png|jpg|jpeg))?$', name_lower)
                    if match:
                        num = int(match.group(1))
                        return (0 if num == 1 else 1, num, fname.name)
                    return (0, 0, fname.name)
                
                image_list_sorted = sorted(image_list, key=sort_key)

                # Verificar si el producto ya existe
                product, created = Product.objects.get_or_create(
                    name=product_name,
                    defaults={
                        'category': category,
                        'brand': brand,
                        'short_description': f'{product_name} - {category_name}',
                        'description': f'{product_name} de alta calidad. {category.description if category.description else ""}',
                        'price': 0,  # Se debe actualizar manualmente
                        'stock': 0,  # Se debe actualizar manualmente
                        'is_active': True,
                    }
                )

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
                    # Limpiar imágenes existentes
                    ProductImage.objects.filter(product=product).delete()
                else:
                    created_count += 1

                # Cargar imágenes del producto
                for idx, img_file in enumerate(image_list_sorted):
                    try:
                        is_primary = (idx == 0)
                        
                        # Leer y guardar la imagen
                        with open(img_file, 'rb') as f:
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
                            with open(global_img, 'rb') as f:
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

