"""
Comando para limpiar imágenes duplicadas de productos

Uso:
    python manage.py clean_duplicate_images
"""

from django.core.management.base import BaseCommand
from shop.models import Product, ProductImage
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
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS(f'Total de imágenes duplicadas eliminadas: {total_deleted}'))
        self.stdout.write(self.style.SUCCESS('=' * 50))

