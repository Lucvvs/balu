# Carga de Datos Iniciales - MotoMoto

Este documento explica cómo cargar los datos iniciales (categorías, marcas y productos) al desplegar el proyecto.

## Estructura de Archivos

```
MotoMotoCR/
├── shop/
│   ├── fixtures/
│   │   ├── initial_categories.json  # Categorías básicas
│   │   └── initial_brands.json      # Marcas básicas
│   └── management/
│       └── commands/
│           ├── load_initial_data.py      # Comando completo
│           └── load_initial_products.py  # Comando para productos
├── static/
│   └── img/
│       └── productos/  # Aquí van las imágenes de productos
│           ├── producto-nombre.png       # Imagen principal
│           ├── producto-nombre-2.png     # Imagen secundaria
│           └── producto-nombre-3.png     # Imagen secundaria
└── media/
    └── products/  # Se crea automáticamente al cargar productos
```

## Proceso de Carga

### 1. Preparar las Imágenes

Coloca las imágenes de tus productos en `static/img/productos/` con el siguiente formato:

- **Imagen principal**: `nombre-producto.png` o `nombre-producto-1.png`
- **Imágenes secundarias**: `nombre-producto-2.png`, `nombre-producto-3.png`, etc.

Ejemplo:
```
static/img/productos/
├── casco-shoei-x-spirit.png      # Imagen principal
├── casco-shoei-x-spirit-2.png    # Imagen secundaria
└── casco-shoei-x-spirit-3.png    # Imagen secundaria
```

### 2. Editar Datos de Productos

Edita el archivo `shop/management/commands/load_initial_products.py` y modifica la lista `PRODUCTS_DATA` con tus productos:

```python
PRODUCTS_DATA = [
    {
        'name': 'Casco Shoei X-Spirit III',
        'category': 'Equipamiento',
        'brand': 'Shoei',
        'short_description': 'Casco premium de fibra de carbono',
        'description': 'Descripción completa...',
        'price': 450000,
        'offer_price': 399000,
        'stock': 5,
        'available_sizes': 'S,M,L,XL',  # Dejar vacío '' si no aplica
        'is_offer': True,
        'is_best_seller': True,
        'is_active': True,
        'image_files': [
            'casco-shoei-x-spirit.png',
            'casco-shoei-x-spirit-2.png',
            'casco-shoei-x-spirit-3.png'
        ]
    },
    # Agrega más productos aquí
]
```

**Nota**: Los nombres de las imágenes en `image_files` deben coincidir exactamente con los archivos en `static/img/productos/`.

### 3. Ejecutar Carga de Datos

#### Opción A: Carga Completa (Recomendado)

Ejecuta un solo comando que carga todo:

```bash
python manage.py load_initial_data
```

Este comando carga:
1. Categorías
2. Marcas
3. Productos (con imágenes)

#### Opción B: Carga Paso a Paso

Si prefieres cargar por separado:

```bash
# 1. Cargar categorías
python manage.py loaddata shop/fixtures/initial_categories.json

# 2. Cargar marcas
python manage.py loaddata shop/fixtures/initial_brands.json

# 3. Cargar productos
python manage.py load_initial_products
```

### 4. Actualizar Productos Existentes

Si necesitas actualizar productos que ya existen:

```bash
python manage.py load_initial_products --force
```

Esto actualizará los datos de los productos (precio, stock, descripción, etc.) y volverá a cargar las imágenes.

## Lógica de Imágenes

El sistema maneja las imágenes de la siguiente manera:

1. **Imagen Principal**: La primera imagen en `image_files` se marca automáticamente como `is_primary=True`
2. **Imágenes Secundarias**: Las siguientes imágenes se marcan como `is_primary=False` con un `order` incremental
3. **Orden**: Las imágenes se ordenan por: `is_primary` (desc), `order` (asc), `id` (asc)

### En las Vistas

- **Lista de productos**: Muestra la imagen principal (`is_primary=True`), o la primera si no hay principal
- **Detalle de producto**: Muestra todas las imágenes con la principal destacada
- **Los más vendidos**: Muestra todas las imágenes en carrusel

## Verificar la Carga

Después de ejecutar los comandos, puedes verificar:

1. **Panel Admin**: Ve a `/admin/shop/product/` y verifica que los productos se crearon correctamente
2. **Stock**: Verifica que el stock esté correcto
3. **Imágenes**: Verifica que las imágenes se muestren correctamente en el sitio

## Notas Importantes

- Las imágenes se copian de `static/img/productos/` a `media/products/`
- Los archivos originales en `static/` permanecen intactos
- Solo se puede tener una imagen principal por producto
- Si actualizas un producto con `--force`, las imágenes anteriores se eliminan y se vuelven a cargar

## Mantenimiento Futuro

Después de la carga inicial, todos los productos nuevos o modificados se manejan desde el Panel de Admin de Django en `/admin/`.

Para agregar más productos inicialmente, simplemente:
1. Agrega las imágenes a `static/img/productos/`
2. Edita `PRODUCTS_DATA` en `load_initial_products.py`
3. Ejecuta `python manage.py load_initial_products`

