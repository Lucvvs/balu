"""
Comando para limpiar imágenes duplicadas de productos

Uso:
    python manage.py clean_duplicate_images
"""

from django.core.management.base import BaseCommand
from shop.models import Product, ProductImage
from django.conf import settings
from pathlib import Path
from collections import defaultdict
import os


class Command(BaseCommand):
    help = 'Elimina imágenes duplicadas de productos, manteniendo solo una versión de cada imagen'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Limpiando imágenes duplicadas...'))
        
        total_deleted = 0
        
        # Obtener todos los productos
        products = Product.objects.all()
        
        for product in products:
            images = product.images.all()
            
            # Agrupar imágenes por nombre base (sin sufijos de Django)
            image_groups = defaultdict(list)
            
            for img in images:
                # Obtener el nombre base del archivo (sin sufijos como _y1Ntmcf)
                base_name = img.image.name
                # Remover la ruta y obtener solo el nombre del archivo
                filename = os.path.basename(base_name)
                # Extraer el nombre base sin sufijos de Django (formato: nombre_sufijo.ext)
                # Django agrega sufijos aleatorios cuando hay conflictos
                if '_' in filename and '.' in filename:
                    # Intentar extraer el nombre original
                    parts = filename.rsplit('_', 1)
                    if len(parts) == 2:
                        # Verificar si la segunda parte parece un sufijo (letras/números cortos)
                        suffix_part = parts[1].split('.')[0]
                        if len(suffix_part) <= 10 and suffix_part.isalnum():
                            # Probablemente es un sufijo de Django
                            base_name_clean = parts[0]
                        else:
                            base_name_clean = filename.split('.')[0]
                    else:
                        base_name_clean = filename.split('.')[0]
                else:
                    base_name_clean = filename.split('.')[0]
                
                image_groups[base_name_clean].append(img)
            
            # Para cada grupo, mantener solo una imagen (preferir la principal)
            for base_name, img_list in image_groups.items():
                if len(img_list) > 1:
                    # Ordenar: principal primero, luego por orden, luego por ID
                    img_list_sorted = sorted(
                        img_list,
                        key=lambda x: (not x.is_primary, x.order, x.id)
                    )
                    
                    # Mantener la primera, eliminar las demás
                    to_keep = img_list_sorted[0]
                    to_delete = img_list_sorted[1:]
                    
                    for img in to_delete:
                        # Eliminar el archivo físico si existe
                        if img.image and os.path.exists(img.image.path):
                            try:
                                os.remove(img.image.path)
                            except Exception as e:
                                self.stdout.write(
                                    self.style.WARNING(f'No se pudo eliminar archivo {img.image.path}: {e}')
                                )
                        
                        # Eliminar el registro
                        img.delete()
                        total_deleted += 1
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  Eliminada duplicada: {img.image.name} (Producto: {product.name})'
                            )
                        )
        
        # Limpiar archivos huérfanos (archivos físicos sin registro en BD)
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Limpiando archivos huérfanos...'))
        
        media_products_dir = Path(settings.MEDIA_ROOT) / 'products'
        orphan_files_deleted = 0
        
        if media_products_dir.exists():
            # Obtener todas las rutas de archivos que están registradas en la BD
            registered_paths = set()
            for img in ProductImage.objects.all():
                if img.image:
                    try:
                        # Obtener la ruta completa del archivo
                        full_path = img.image.path
                        registered_paths.add(full_path)
                        # También registrar solo el nombre del archivo
                        registered_paths.add(os.path.basename(full_path))
                    except:
                        try:
                            # Si no se puede obtener el path, usar el name
                            registered_paths.add(os.path.basename(img.image.name))
                        except:
                            pass
            
            # Buscar archivos físicos que no están en la BD
            for file_path in media_products_dir.glob('*'):
                if file_path.is_file() and file_path.name != '.gitkeep':
                    filename = file_path.name
                    full_path = str(file_path.resolve())
                    
                    # Verificar si el archivo está registrado
                    is_registered = False
                    
                    # Verificar ruta completa
                    if full_path in registered_paths:
                        is_registered = True
                    # Verificar nombre del archivo
                    elif filename in registered_paths:
                        is_registered = True
                    else:
                        # Verificar si hay alguna coincidencia parcial (para archivos con sufijos)
                        # Extraer el nombre base sin extensión
                        base_name_without_ext = os.path.splitext(filename)[0]
                        # Si tiene sufijo de Django (formato: nombre_sufijoAleatorio)
                        if '_' in base_name_without_ext:
                            # Intentar extraer el nombre original
                            parts = base_name_without_ext.rsplit('_', 1)
                            if len(parts) == 2 and len(parts[1]) <= 10:
                                # Probablemente es un sufijo de Django
                                original_name = parts[0] + os.path.splitext(filename)[1]
                                if original_name in registered_paths:
                                    is_registered = True
                    
                    if not is_registered:
                        try:
                            file_path.unlink()
                            orphan_files_deleted += 1
                            if orphan_files_deleted <= 20:  # Mostrar solo los primeros 20
                                self.stdout.write(
                                    self.style.SUCCESS(f'  Eliminado archivo huérfano: {filename}')
                                )
                        except Exception as e:
                            self.stdout.write(
                                self.style.WARNING(f'  No se pudo eliminar {filename}: {str(e)}')
                            )
            
            if orphan_files_deleted > 20:
                self.stdout.write(
                    self.style.SUCCESS(f'  ... y {orphan_files_deleted - 20} archivos huérfanos más eliminados')
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS(f'Total de imágenes duplicadas eliminadas: {total_deleted}'))
        if orphan_files_deleted > 0:
            self.stdout.write(self.style.SUCCESS(f'Total de archivos huérfanos eliminados: {orphan_files_deleted}'))
        self.stdout.write(self.style.SUCCESS('=' * 50))

