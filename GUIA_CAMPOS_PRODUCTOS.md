# 📝 Guía de Campos para Productos - JSON

Esta guía explica cada campo del archivo `shop/fixtures/initial_products.json` para que puedas personalizar completamente tus productos.

## 📋 Estructura General

Cada producto en el JSON es un objeto con los siguientes campos:

```json
{
  "name": "...",
  "short_description": "...",
  "description": "...",
  "category": "...",
  "brand": "...",
  "price": 0,
  "offer_price": null,
  "stock": 0,
  "available_sizes": "...",
  "is_active": true,
  "is_offer": false,
  "is_best_seller": false,
  "images": [...]
}
```

---

## 🔤 Campos de Texto

### `name` (Requerido)
- **Qué es**: Nombre completo del producto que aparecerá en la tienda
- **Ejemplo**: `"Casco HRO 514 Negro-Rojo"`
- **Dónde se muestra**: 
  - Lista de productos
  - Página de detalle
  - Carrito de compras
  - Pedidos

### `short_description` (Requerido)
- **Qué es**: Descripción corta visible en listados y cards de productos
- **Ejemplo**: `"Casco HRO 514 en color Negro-Rojo, certificado DOT y ECE"`
- **Dónde se muestra**: 
  - Cards de productos en la home
  - Lista de productos
  - Meta descripción (SEO)

### `description` (Requerido)
- **Qué es**: Descripción completa visible en la página de detalle del producto
- **Ejemplo**: `"Casco de alta calidad HRO 514 en combinación Negro-Rojo. Certificado DOT y ECE. Visera anti-empañante incluida..."`
- **Dónde se muestra**: 
  - Página de detalle del producto (sección completa)
  - Búsquedas internas

---

## 🏷️ Campos de Clasificación

### `category` (Requerido)
- **Qué es**: Nombre exacto de la categoría
- **Valores permitidos**: 
  - `"Cascos"`
  - `"Maletas"`
  - `"Seguridad"`
  - `"Accesorios"`
- **Importante**: El nombre debe coincidir exactamente con las categorías en `initial_categories.json`
- **Dónde se usa**: Filtrado, navegación, organización

### `brand` (Opcional)
- **Qué es**: Nombre exacto de la marca
- **Valores permitidos**: 
  - `"HRO"`
  - `"SHAFT"`
  - `"4RS"`
  - `"motocentric"`
  - `"KOVIX"`
  - `null` (si el producto no tiene marca)
- **Importante**: El nombre debe coincidir exactamente con las marcas en `initial_brands.json`
- **Ejemplo sin marca**: `"AntiFOG"` tiene `"brand": null`

---

## 💰 Campos de Precio

### `price` (Requerido)
- **Qué es**: Precio original en CLP (pesos chilenos)
- **Tipo**: Número entero (sin decimales)
- **Ejemplo**: `55000` (representa $55.000 CLP)
- **Importante**: Siempre debe ser un número mayor a 0
- **Dónde se muestra**: 
  - Como precio principal si no hay oferta
  - Tachado si hay precio de oferta

### `offer_price` (Opcional)
- **Qué es**: Precio de oferta en CLP (pesos chilenos)
- **Tipo**: Número entero o `null`
- **Ejemplo**: 
  - Con oferta: `49900` (representa $49.900 CLP)
  - Sin oferta: `null`
- **Regla**: Debe ser menor que `price` para que funcione correctamente
- **Dónde se muestra**: 
  - Como precio destacado (en rojo)
  - En la sección de ofertas si `is_offer` es `true`

---

## 📦 Campos de Inventario

### `stock` (Requerido)
- **Qué es**: Cantidad disponible en inventario
- **Tipo**: Número entero (0 o mayor)
- **Ejemplo**: `5` (5 unidades disponibles)
- **Comportamiento**: 
  - Si stock = 0, el producto puede no mostrarse o mostrarse como "Sin stock"
  - Se reduce automáticamente al realizar pedidos

### `available_sizes` (Opcional)
- **Qué es**: Tallas disponibles separadas por coma
- **Tipo**: String o cadena vacía `""`
- **Ejemplos**: 
  - Con tallas: `"S,M,L,XL"`
  - Sin tallas: `""` (cadena vacía para productos como candados, accesorios)
  - Colores (para Trenzas): `"Amarilla,Azul,Morada,Roja,Rosa"`
- **Dónde se muestra**: 
  - Selector de tallas en la página de detalle
  - Información del producto en el carrito

---

## ✅ Campos de Estado

### `is_active` (Requerido)
- **Qué es**: Controla si el producto es visible en la tienda
- **Tipo**: Boolean (`true` o `false`)
- **Ejemplo**: `true`
- **Comportamiento**: 
  - `true` = Producto visible y disponible para compra
  - `false` = Producto oculto (no aparece en búsquedas ni listados)

### `is_offer` (Requerido)
- **Qué es**: Indica si el producto aparece en la sección de ofertas
- **Tipo**: Boolean (`true` o `false`)
- **Ejemplo**: `true`
- **Comportamiento**: 
  - `true` = Aparece en la sección "Ofertas" de la home
  - `false` = No aparece en ofertas (pero puede tener `offer_price`)
- **Recomendación**: Si `offer_price` no es `null`, poner `true` aquí

### `is_best_seller` (Requerido)
- **Qué es**: Indica si el producto aparece en la sección de más vendidos
- **Tipo**: Boolean (`true` o `false`)
- **Ejemplo**: `false`
- **Comportamiento**: 
  - `true` = Aparece en la sección "Los Más Vendidos" de la home
  - `false` = No aparece en más vendidos

---

## 🖼️ Campo de Imágenes

### `images` (Opcional pero recomendado)
- **Qué es**: Array (lista) de objetos de imagen
- **Tipo**: Array de objetos
- **Estructura de cada imagen**:
```json
{
  "file": "nombre-archivo.png",
  "is_primary": true,
  "order": 0
}
```

#### Campos de cada imagen:

##### `file` (Requerido)
- **Qué es**: Nombre exacto del archivo de imagen en `static/img/productos/`
- **Ejemplo**: `"Hro514Negro-Rojo1.png"`
- **Importante**: 
  - El nombre debe coincidir exactamente con el archivo (incluyendo mayúsculas/minúsculas)
  - El archivo debe existir en `static/img/productos/`

##### `is_primary` (Requerido)
- **Qué es**: Indica si esta es la imagen principal del producto
- **Tipo**: Boolean (`true` o `false`)
- **Regla**: Solo UNA imagen por producto debe tener `is_primary: true`
- **Dónde se muestra**:
  - `true` = Se muestra en listados, cards, y como primera imagen en el detalle
  - `false` = Se muestra en el carrusel de imágenes del detalle

##### `order` (Requerido)
- **Qué es**: Orden de visualización de las imágenes
- **Tipo**: Número entero
- **Ejemplo**: `0`, `1`, `2`, `3`...
- **Comportamiento**: 
  - Las imágenes se ordenan de menor a mayor número
  - La primera imagen (order: 0) normalmente es la principal
  - Las imágenes globales (como `AccesoriosShaftGLOB.png`) pueden tener order alto (ej: 10)

---

## 📝 Ejemplo Completo

```json
{
  "name": "Casco HRO 514 Negro-Rojo",
  "short_description": "Casco HRO 514 en color Negro-Rojo, certificado DOT y ECE",
  "description": "Casco de alta calidad HRO 514 en combinación Negro-Rojo. Certificado DOT y ECE. Visera anti-empañante incluida. Diseño deportivo y seguro.",
  "category": "Cascos",
  "brand": "HRO",
  "price": 55000,
  "offer_price": null,
  "stock": 6,
  "available_sizes": "S,M,L,XL",
  "is_active": true,
  "is_offer": false,
  "is_best_seller": true,
  "images": [
    {
      "file": "Hro514Negro-Rojo1.png",
      "is_primary": true,
      "order": 0
    },
    {
      "file": "Hro514Negro-Rojo2.png",
      "is_primary": false,
      "order": 1
    },
    {
      "file": "Hro514Negro-Rojo3.png",
      "is_primary": false,
      "order": 2
    }
  ]
}
```

---

## 🚀 Cómo Cargar Productos

### Carga desde JSON (Recomendado)
```bash
# Carga todo (categorías, marcas, productos desde JSON)
python manage.py load_initial_data

# Solo productos desde JSON
python manage.py load_products_from_json

# Forzar actualización de productos existentes
python manage.py load_products_from_json --force

# Limpiar todos los productos y cargar desde cero
python manage.py load_products_from_json --clean
```

### Carga con Detección Automática (Método anterior)
```bash
# Usar detección automática desde imágenes
python manage.py load_initial_data --auto-detect
```

---

## ✅ Checklist para Agregar un Nuevo Producto

- [ ] Agregar imágenes del producto en `static/img/productos/`
- [ ] Agregar objeto del producto en `initial_products.json`
- [ ] Verificar que `category` existe en `initial_categories.json`
- [ ] Verificar que `brand` existe en `initial_brands.json` (o usar `null`)
- [ ] Especificar al menos una imagen con `is_primary: true`
- [ ] Verificar que los nombres de archivos de imagen coincidan exactamente
- [ ] Ejecutar `python manage.py load_products_from_json --force`

---

## 💡 Tips y Mejores Prácticas

1. **Imagen Principal**: Siempre elige la mejor foto como principal (la primera que verán los clientes)

2. **Orden de Imágenes**: Organiza las imágenes para mostrar diferentes ángulos del producto
   - order: 0 = Vista frontal/principal
   - order: 1 = Vista lateral
   - order: 2 = Vista trasera
   - order: 3+ = Detalles específicos

3. **Precios**: 
   - Redondea a múltiplos de 1000 para precios más "limpios"
   - El descuento típico es entre 10-25% del precio original

4. **Stock Inicial**: 
   - Cascos: 3-6 unidades
   - Maletas: 2-4 unidades
   - Seguridad: 5-10 unidades
   - Accesorios: 8-20 unidades

5. **Ofertas y Más Vendidos**: 
   - Limita a 3-5 productos en cada sección
   - Los productos más populares o con mejor precio deben ser destacados

---

¡Listo! 🎉 Ahora tienes control completo sobre todos los campos de tus productos.

