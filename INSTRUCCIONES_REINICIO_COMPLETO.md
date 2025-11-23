# Instrucciones Completas para Reiniciar desde Cero

## 🎯 Proceso Automatizado Completo

El comando `load_initial_data --force-products` ahora hace TODO automáticamente:
1. ✅ Carga categorías (4)
2. ✅ Carga marcas (5)
3. ✅ Carga productos con imágenes (27 productos)
4. ✅ Asigna precios y stock realistas automáticamente
5. ✅ Configura 3 ofertas y 3 más vendidos automáticamente

## 📋 Comandos para Reiniciar

### En Localhost (Desarrollo)

```bash
# Opción 1: Comando completo (recomendado)
python manage.py load_initial_data --force-products

# Opción 2: Paso a paso
python manage.py load_initial_products --clean
python manage.py set_product_prices
python manage.py set_featured_products
```

### En Render (Producción)

1. **Hacer push de cambios a GitHub**
2. **Esperar a que Render haga deploy**
3. **Ir al Shell de Render** y ejecutar:

```bash
python manage.py load_initial_data --force-products
```

## 🔧 Comandos Individuales

### Limpiar y Recargar Productos
```bash
python manage.py load_initial_products --clean
```

### Asignar Precios y Stock
```bash
python manage.py set_product_prices
# O forzar actualización:
python manage.py set_product_prices --force
```

### Configurar Ofertas y Más Vendidos
```bash
python manage.py set_featured_products
```

### Limpiar Imágenes Duplicadas
```bash
python manage.py clean_duplicate_images
```

## 📊 Datos que se Configuran Automáticamente

### Precios por Categoría
- **Cascos HRO**: $45,000 - $65,000
- **Cascos SHAFT**: $55,000 - $85,000
- **Maletas 4RS**: $80,000 - $150,000
- **Seguridad KOVIX**: $25,000 - $45,000
- **Accesorios motocentric**: $15,000 - $35,000

### Stock por Categoría
- **Cascos**: 2-8 unidades
- **Maletas**: 1-5 unidades
- **Seguridad**: 3-10 unidades
- **Accesorios**: 5-15 unidades

### Ofertas
- 30% de productos tendrán oferta automáticamente
- Descuento: 10-25% del precio base

### Más Vendidos
- Los 3 productos más recientes con stock > 0

## ✅ Verificación

Después de ejecutar el comando, verifica:

```bash
# Ver resumen
python manage.py shell -c "from shop.models import Product; print(f'Total: {Product.objects.count()}'); print(f'Con stock: {Product.objects.filter(stock__gt=0).count()}'); print(f'Ofertas: {Product.objects.filter(is_offer=True).count()}'); print(f'Más vendidos: {Product.objects.filter(is_best_seller=True).count()}')"

# Ver productos en oferta
python manage.py shell -c "from shop.models import Product; [print(f'{p.name}: ${p.price:,} -> ${p.offer_price:,}') for p in Product.objects.filter(is_offer=True)]"

# Ver más vendidos
python manage.py shell -c "from shop.models import Product; [print(f'{p.name}: Stock={p.stock}') for p in Product.objects.filter(is_best_seller=True)]"
```

## 🐛 Solución de Problemas

### Imágenes Duplicadas
```bash
python manage.py clean_duplicate_images
python manage.py load_initial_products --clean
```

### Productos sin Precios/Stock
```bash
python manage.py set_product_prices --force
```

### Sin Ofertas o Más Vendidos
```bash
python manage.py set_featured_products
```

### Imágenes no se Muestran
- Verifica que las imágenes estén en `static/img/productos/` en Git
- Ejecuta `python manage.py load_initial_products --clean` para recargar

## 📝 Notas Importantes

1. **Imágenes**: Las imágenes fuente están en `static/img/productos/` (en Git) y se copian a `media/products/` (disco persistente en Render)

2. **Precios y Stock**: Se asignan automáticamente con valores realistas según categoría y marca

3. **Ofertas**: Se asignan automáticamente al 30% de los productos

4. **Más Vendidos**: Se asignan automáticamente a los 3 productos más recientes con stock

5. **Sin Duplicados**: El comando verifica y evita duplicar imágenes

