# Instrucciones para Cargar Datos Iniciales - MotoMoto

## 📋 Preparación

### 1. Coloca las imágenes de productos

Coloca todas las imágenes de productos en:
```
static/img/productos/
```

**Formato de nombres:**
- Imagen principal: `nombre-producto.png` o `nombre-producto-1.png`
- Imágenes secundarias: `nombre-producto-2.png`, `nombre-producto-3.png`, etc.

**Ejemplo:**
```
static/img/productos/
├── casco-shoei-x-spirit.png      (principal)
├── casco-shoei-x-spirit-2.png    (secundaria)
└── casco-shoei-x-spirit-3.png    (secundaria)
```

### 2. Configura los productos

Edita el archivo `shop/management/commands/load_initial_products.py` y modifica la lista `PRODUCTS_DATA` con tus productos reales:

```python
PRODUCTS_DATA = [
    {
        'name': 'Casco Shoei X-Spirit III',
        'category': 'Equipamiento',  # Debe coincidir con una categoría en fixtures
        'brand': 'Shoei',            # Debe coincidir con una marca en fixtures
        'short_description': 'Casco premium de fibra de carbono',
        'description': 'Descripción completa del producto...',
        'price': 450000,              # Precio en CLP (solo números)
        'offer_price': 399000,        # Precio oferta (opcional, None si no hay oferta)
        'stock': 5,                   # Cantidad en stock
        'available_sizes': 'S,M,L,XL', # Tallas separadas por coma (vacío '' si no aplica)
        'is_offer': True,             # True si tiene oferta
        'is_best_seller': True,       # True si es más vendido
        'is_active': True,            # True para activar el producto
        'image_files': [              # Nombres exactos de archivos en static/img/productos/
            'casco-shoei-x-spirit.png',
            'casco-shoei-x-spirit-2.png',
            'casco-shoei-x-spirit-3.png'
        ]
    },
    # Agrega más productos aquí...
]
```

**Notas importantes:**
- Los nombres de `category` y `brand` deben coincidir exactamente con los que están en las fixtures
- Los nombres de `image_files` deben coincidir exactamente con los archivos en `static/img/productos/`
- La primera imagen en `image_files` será automáticamente la imagen principal (`is_primary=True`)
- Si no especificas `image_files`, el comando intentará buscar imágenes automáticamente por el slug del producto

## 🚀 Ejecutar Carga

### Opción 1: Carga Completa (Recomendado)

Ejecuta un solo comando que carga todo automáticamente:

```bash
python manage.py load_initial_data
```

Este comando carga en orden:
1. ✅ Categorías (Equipamiento, Para la Moto, Accesorios)
2. ✅ Marcas (Shoei, Arai, AGV, etc.)
3. ✅ Productos con imágenes

### Opción 2: Carga Paso a Paso

Si prefieres cargar por separado:

```bash
# 1. Cargar solo categorías
python manage.py loaddata shop/fixtures/initial_categories.json

# 2. Cargar solo marcas
python manage.py loaddata shop/fixtures/initial_brands.json

# 3. Cargar solo productos
python manage.py load_initial_products
```

### Actualizar Productos Existentes

Si necesitas actualizar productos que ya existen (cambiar precio, stock, descripción, etc.):

```bash
python manage.py load_initial_products --force
```

⚠️ **Advertencia**: Esto eliminará las imágenes anteriores y volverá a cargarlas.

## 📁 Estructura de Archivos Después de la Carga

Después de ejecutar el comando, las imágenes se copiarán de `static/img/productos/` a `media/products/`:

```
MotoMotoCR/
├── static/
│   └── img/
│       └── productos/          # Imágenes originales (se mantienen aquí)
│           ├── casco-1.png
│           └── casco-2.png
├── media/                      # Se crea automáticamente
│   └── products/               # Copias de imágenes (para uso del sistema)
│       ├── casco-1.png
│       └── casco-2.png
└── db.sqlite3                  # Base de datos con productos cargados
```

## ✅ Verificar Carga

Después de ejecutar los comandos:

1. **Panel Admin**: Ve a `http://localhost:8000/admin/shop/product/`
   - Verifica que los productos se hayan creado
   - Verifica stock, precios, categorías

2. **Verificar Imágenes**:
   - Ve a la página de inicio: `http://localhost:8000/`
   - Verifica que las imágenes se muestren en ofertas y más vendidos
   - Ve a un producto y verifica que todas las imágenes se vean correctamente

3. **Verificar Imagen Principal**:
   - En la lista de productos, debe mostrarse la primera imagen de cada producto
   - En el detalle, la imagen principal debe estar destacada

## 🔧 Lógica de Imágenes Principales y Secundarias

El sistema funciona así:

1. **Imagen Principal** (`is_primary=True`):
   - La primera imagen en `image_files` se marca automáticamente como principal
   - Se muestra en listas de productos, cards, etc.
   - Solo puede haber una imagen principal por producto

2. **Imágenes Secundarias** (`is_primary=False`):
   - Las siguientes imágenes en `image_files` son secundarias
   - Se muestran en el detalle del producto en el carrusel
   - Se ordenan por el campo `order`

3. **En las Vistas**:
   - **Lista de productos**: Muestra la imagen principal, o la primera si no hay principal
   - **Detalle de producto**: Muestra todas las imágenes en carrusel con la principal destacada
   - **Los más vendidos**: Muestra todas las imágenes en carrusel

## 📝 Ejemplo Completo

```python
PRODUCTS_DATA = [
    {
        'name': 'Casco Shoei X-Spirit III Rojo',
        'category': 'Equipamiento',
        'brand': 'Shoei',
        'short_description': 'Casco premium de fibra de carbono',
        'description': 'Casco de alta gama con tecnología avanzada. Certificado DOT y ECE. Visera anti-empañante incluida. Disponible en varios colores.',
        'price': 450000,
        'offer_price': 399000,
        'stock': 5,
        'available_sizes': 'S,M,L,XL',
        'is_offer': True,
        'is_best_seller': True,
        'is_active': True,
        'image_files': [
            'casco-shoei-rojo.png',        # Principal
            'casco-shoei-rojo-lado.png',   # Secundaria
            'casco-shoei-rojo-detalle.png' # Secundaria
        ]
    },
    {
        'name': 'Guantes Alpinestars GP Pro',
        'category': 'Equipamiento',
        'brand': 'Alpinestars',
        'short_description': 'Guantes de competición',
        'description': 'Guantes de alta calidad para uso en carretera y track.',
        'price': 89000,
        'offer_price': None,  # Sin oferta
        'stock': 10,
        'available_sizes': 'M,L,XL',
        'is_offer': False,
        'is_best_seller': False,
        'is_active': True,
        'image_files': [
            'guantes-alpinestars.png',
            'guantes-alpinestars-2.png'
        ]
    },
]
```

## ❓ Solución de Problemas

### Error: "Categoría 'X' no existe"
→ Ejecuta primero: `python manage.py loaddata shop/fixtures/initial_categories.json`

### Error: "Marca 'X' no existe"
→ Ejecuta primero: `python manage.py loaddata shop/fixtures/initial_brands.json`

### Error: "Imagen X no encontrada"
→ Verifica que el nombre del archivo en `image_files` coincida exactamente con el archivo en `static/img/productos/`
→ Verifica mayúsculas/minúsculas del nombre del archivo

### Los productos no aparecen
→ Verifica que `is_active=True` en PRODUCTS_DATA
→ Verifica en el admin que los productos se crearon: `/admin/shop/product/`

### Las imágenes no se muestran
→ Verifica que las imágenes se copiaron a `media/products/`
→ Verifica los permisos del directorio `media/`
→ Verifica que `MEDIA_URL` y `MEDIA_ROOT` estén configurados correctamente en `settings.py`

## 🎯 Siguiente Paso

Una vez cargados los productos iniciales:

1. ✅ Verifica todo en el panel admin
2. ✅ Revisa que las imágenes se vean correctamente
3. ✅ Verifica stock y precios
4. ✅ A partir de ahora, usa el admin para agregar/editar productos normalmente

¡Listo! 🚀

