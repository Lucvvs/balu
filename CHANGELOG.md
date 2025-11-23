# Changelog - MotoMoto

## [Última Actualización] - 2025-11-23

### ✨ Nuevas Funcionalidades

#### 🖼️ Sistema de Imágenes Mejorado
- **Detección automática de productos**: El comando `load_initial_products` detecta automáticamente productos, marcas y categorías desde nombres de archivos
- **Imágenes globales**: Soporte para imágenes compartidas (ej: `AccesoriosShaftGLOB.png` para todos los cascos SHAFT)
- **Efecto hover en tarjetas**: Las imágenes cambian automáticamente cada 2.5s al pasar el mouse sobre una tarjeta de producto (simula pasar página)
- **Corrección automática**: Comando `fix_primary_images` para asegurar que cada producto tenga una imagen principal
- **Verificación de imágenes**: Comando `verify_images` para diagnosticar problemas de carga
- **Prevención de duplicados**: Sistema mejorado para evitar imágenes duplicadas en la base de datos

#### 👤 Perfil de Usuario
- Nueva sección de perfil (`/perfil/`) en el menú de usuario
- Edición de información básica con confirmación
- Visualización de historial de pedidos con estados
- Acceso desde el dropdown del navbar

#### 📧 Sistema de Email
- **Confirmación de pedido**: Email automático al cliente cuando se crea un pedido
- **Notificación al admin**: Email automático al administrador con detalles del nuevo pedido
- **Integración Gmail**: Configuración SMTP con Gmail
- Templates HTML responsivos para emails

#### 🎨 Mejoras de UI/UX
- **Navbar sticky**: Se achica y se vuelve ligeramente transparente al hacer scroll
- **Alertas de stock**: Muestra "¡Pocas unidades disponibles!" cuando stock <= 2 (sin mostrar cantidad exacta)
- **Botón "Continuar comprando"**: Movido junto al título del carrito, más prominente
- **Separación visual**: Mejor espaciado entre secciones en el carrito
- **Tamaño de imágenes de marcas**: Aumentado 25% (excepto 4RS que mantiene tamaño original)
- **Centrado de marca motocentric**: Corregido alineamiento en el banner

#### 🛒 Mejoras en Checkout
- **Validación inteligente**: Campos de envío solo se validan si el método de envío tiene costo (no para retiro)
- **Números de pedido personalizados**: Formato `{ID}{InicialUsuario}{InicialEmail}{Año-Día-Mes}`
- **Mensaje de éxito mejorado**: Más visual y con instrucciones de contacto
- **Manejo de errores**: Mejor manejo cuando se intenta agregar productos sin stock

### 🔧 Mejoras Técnicas

#### Base de Datos
- **Detección automática de entorno**: SQLite en desarrollo, PostgreSQL en producción (Render)
- **Comandos locales**: Fuerzan SQLite para desarrollo (`runserver`, `load_initial_data`, etc.)
- **Persistencia en Render**: Configuración de disco persistente para archivos media

#### Comandos de Gestión
- `load_initial_data`: Carga completa automatizada (categorías, marcas, productos, precios, ofertas)
- `set_product_prices`: Asigna precios y stock realistas automáticamente
- `set_featured_products`: Configura ofertas y más vendidos automáticamente
- `fix_primary_images`: Corrige imágenes principales
- `verify_images`: Verifica estado de imágenes con logs detallados
- `clean_duplicate_images`: Limpia imágenes duplicadas y archivos huérfanos

#### Templates
- **Consistencia de imágenes**: Todos los templates (home, products_list, product_detail) usan el mismo patrón
- **Contenedor de imágenes**: Uso de `product-card-image-container` para efectos CSS
- **Manejo de errores**: Mejor `onerror` para imágenes faltantes

#### Logging
- Sistema de logging configurado para vistas
- Logs detallados de carga de imágenes en consola
- Información de rutas, URLs y existencia de archivos

### 🐛 Correcciones

- **404 en placeholder.jpg**: Creado archivo placeholder y mejorado manejo de errores
- **Imágenes no persistentes en Render**: Configurado disco persistente y rutas correctas
- **Imágenes no visibles en ofertas/productos relacionados**: Corregido uso de contenedores CSS
- **Validación de checkout**: Campos de envío solo para métodos con costo
- **Duplicación de imágenes**: Sistema de prevención y limpieza
- **Imágenes principales**: Todas las imágenes ahora tienen `is_primary` correctamente marcado
- **Error 404 al agregar producto sin stock**: Mejor manejo de errores con mensajes claros

### 📦 Nuevos Productos Soportados

- **Kit de Reparación de Llantas**: Detección automática desde `kitrepllant*.png`
- **Trenzas**: Detección automática con selección de colores (Amarilla, Azul, Morada, Roja, Rosa)
- **Casco SHAFT 502 SP Azul**: Detección automática
- **Candado KOVIX KT6 Negro**: Detección automática
- **Candado KOVIX KN1 Negro**: Detección automática

### 🔄 Cambios en Configuración

- **settings.py**: 
  - Detección automática de entorno (local vs Render)
  - Configuración de email (console en desarrollo, SMTP en producción)
  - Logging configurado
  - Lista de comandos locales para forzar SQLite

- **render.yaml**: 
  - Configuración de disco persistente
  - Variable de entorno `RENDER=True`

- **urls.py**: 
  - Servicio de archivos media en producción usando `django.views.static.serve`

### 📝 Documentación

- README.md actualizado con nuevas funcionalidades
- INSTRUCCIONES_CARGA.md actualizado con detección automática
- CHANGELOG.md creado (este archivo)

---

## Versiones Anteriores

### Funcionalidades Base
- Sistema de productos con categorías y marcas
- Carrito de compras (usuarios y anónimos)
- Sistema de pedidos con estados
- Cupones de descuento
- Métodos de envío y pago
- Autenticación de usuarios
- Panel de administración
- Diseño responsive

