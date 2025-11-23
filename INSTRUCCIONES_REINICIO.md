# Instrucciones para Reiniciar desde Cero

## Proceso Completo de Poblamiento Inicial

### 1. En Localhost (Desarrollo)

#### Paso 1: Limpiar Base de Datos (Opcional)
```bash
# Eliminar base de datos SQLite (si quieres empezar completamente desde cero)
rm db.sqlite3

# O simplemente ejecutar las migraciones
python manage.py migrate
```

#### Paso 2: Cargar Todos los Datos Iniciales
```bash
# Este comando carga todo: categorías, marcas, productos, y configura ofertas/más vendidos
python manage.py load_initial_data --force-products
```

Este comando ejecuta en orden:
1. ✅ Carga categorías (Cascos, Maletas, Seguridad, Accesorios)
2. ✅ Carga marcas (HRO, SHAFT, 4RS, motocentric, KOVIX)
3. ✅ Carga productos desde `static/img/productos/` con sus imágenes
4. ✅ Configura automáticamente 3 productos en oferta y 3 más vendidos

#### Paso 3: Verificar
```bash
# Ver productos cargados
python manage.py shell -c "from shop.models import Product; print(f'Total productos: {Product.objects.count()}')"

# Ver ofertas
python manage.py shell -c "from shop.models import Product; offers = Product.objects.filter(is_offer=True); print(f'Ofertas: {offers.count()}'); [print(f'  - {p.name}') for p in offers]"

# Ver más vendidos
python manage.py shell -c "from shop.models import Product; best = Product.objects.filter(is_best_seller=True); print(f'Más vendidos: {best.count()}'); [print(f'  - {p.name}') for p in best]"
```

### 2. En Render (Producción)

#### Paso 1: Hacer Push de Cambios
```bash
git add .
git commit -m "Actualización de comandos de poblamiento inicial"
git push origin main
```

#### Paso 2: Esperar a que Render Haga Deploy
- Render automáticamente detectará los cambios y hará deploy
- Espera a que el deploy termine

#### Paso 3: Ejecutar Comandos en Render Shell
1. Ve al dashboard de Render
2. Selecciona tu servicio web `motomoto-web`
3. Ve a la pestaña **"Shell"**
4. Ejecuta:

```bash
# Cargar todos los datos iniciales
python manage.py load_initial_data --force-products
```

Este comando:
- ✅ Carga categorías y marcas desde fixtures
- ✅ Carga productos desde `static/img/productos/` (que están en Git)
- ✅ Copia imágenes a `media/products/` (disco persistente)
- ✅ Configura automáticamente 3 ofertas y 3 más vendidos

#### Paso 4: Verificar en Render
```bash
# Verificar productos
python manage.py shell -c "from shop.models import Product; print(f'Total: {Product.objects.count()} productos')"

# Verificar ofertas y más vendidos
python manage.py shell -c "from shop.models import Product; print(f'Ofertas: {Product.objects.filter(is_offer=True).count()}'); print(f'Más vendidos: {Product.objects.filter(is_best_seller=True).count()}')"
```

## Comandos Individuales (Si Necesitas)

### Solo Cargar Productos
```bash
python manage.py load_initial_products --clean
```

### Solo Configurar Ofertas y Más Vendidos
```bash
python manage.py set_featured_products
```

### Solo Ofertas
```bash
python manage.py set_featured_products --offers-only
```

### Solo Más Vendidos
```bash
python manage.py set_featured_products --best-sellers-only
```

## Estructura de Datos

### Categorías (4)
1. **Cascos** - Cascos de alta calidad para tu seguridad
2. **Maletas** - Maletas y sistemas de almacenamiento
3. **Seguridad** - Candados y sistemas de seguridad
4. **Accesorios** - Complementos y accesorios

### Marcas (5)
1. **HRO** - Cascos
2. **SHAFT** - Cascos
3. **4RS** - Maletas
4. **motocentric** - Accesorios
5. **KOVIX** - Seguridad (Candados)

### Productos Destacados
- **3 Ofertas**: Productos con `offer_price` o los 3 más baratos
- **3 Más Vendidos**: Los 3 productos más recientes con stock

## Notas Importantes

1. **Imágenes**: Las imágenes fuente están en `static/img/productos/` y se copian automáticamente a `media/products/` cuando se cargan los productos.

2. **Disco Persistente en Render**: Las imágenes se guardan en `/opt/render/project/src/media/products/` (disco persistente).

3. **Reinicio Completo**: Si necesitas reiniciar todo desde cero:
   ```bash
   python manage.py load_initial_products --clean
   python manage.py set_featured_products
   ```

4. **Actualizar Ofertas/Más Vendidos**: Si cambias productos, puedes reconfigurar:
   ```bash
   python manage.py set_featured_products
   ```

## Solución de Problemas

### Las imágenes no aparecen
- Verifica que las imágenes estén en `static/img/productos/` en Git
- Ejecuta `python manage.py load_initial_products --clean` para recargar

### No hay ofertas o más vendidos
- Ejecuta `python manage.py set_featured_products`
- Verifica que haya productos con stock > 0

### Error al cargar productos
- Verifica que las categorías y marcas estén cargadas primero
- Ejecuta `python manage.py load_initial_data` completo

