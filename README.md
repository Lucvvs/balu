# MotoMoto - E-commerce de Accesorios para Motocicletas

Aplicación web Django para tienda de accesorios y equipamiento para motocicletas, desarrollada con Django 5.2+, Bootstrap 5 y diseño responsive.

## 🚀 Características Principales

- **Catálogo de Productos**: Sistema completo de productos con categorías, marcas, imágenes y gestión de stock
- **Carrito de Compras**: Carrito funcional para usuarios registrados y anónimos (basado en sesión)
- **Sistema de Pedidos**: Gestión completa de pedidos con múltiples estados
- **Cupones de Descuento**: Sistema de cupones con validación y límites
- **Métodos de Envío y Pago**: Configuración flexible de métodos de entrega y pago
- **Autenticación de Usuarios**: Registro, login y logout con Django Auth
- **Panel de Administración**: Admin completo con todas las funcionalidades de gestión
- **Responsive Design**: Diseño mobile-first completamente responsive
- **Formato de Moneda CLP**: Formateo personalizado para pesos chilenos

## 📋 Requisitos

- Python 3.11+
- Django 5.0+
- Pillow (para manejo de imágenes)

## 🛠️ Instalación

1. **Clonar el repositorio** (o descargar el proyecto)

2. **Crear entorno virtual**:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

4. **Realizar migraciones**:
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Crear superusuario**:
```bash
python manage.py createsuperuser
```

6. **Ejecutar servidor de desarrollo**:
```bash
python manage.py runserver
```

7. **Acceder a la aplicación**:
   - Frontend: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

## 📁 Estructura del Proyecto

```
MotoMotoCR/
├── motomoto/              # Configuración del proyecto Django
│   ├── settings.py        # Configuración (idioma español Chile)
│   ├── urls.py            # URLs principales
│   └── ...
├── shop/                  # Aplicación principal
│   ├── models.py          # Modelos de datos (Product, Order, Cart, etc.)
│   ├── views.py           # Vistas de la aplicación
│   ├── forms.py           # Formularios
│   ├── admin.py           # Configuración del admin
│   ├── urls.py            # URLs de la app
│   ├── templatetags/      # Filtros personalizados (currency_clp)
│   └── context_processors.py  # Context processors (carrito)
├── templates/             # Plantillas HTML
│   ├── base.html          # Template base
│   ├── partials/          # Componentes reutilizables
│   │   ├── _navbar.html
│   │   ├── _footer.html
│   │   └── _como_comprar_y_canales.html
│   └── shop/              # Templates de la app
│       ├── home.html
│       ├── products_list.html
│       ├── product_detail.html
│       ├── cart.html
│       ├── register.html
│       └── ...
├── static/                # Archivos estáticos
│   └── css/
│       └── theme.css      # Tema CSS personalizado
└── media/                 # Archivos de medios (imágenes subidas)

```

## 🗄️ Modelos de Datos

### Principales

- **Product**: Productos con precios, stock, ofertas, categorías y marcas
- **Category**: Categorías de productos (Cascos, Maletas, Seguridad, Accesorios)
- **Brand**: Marcas de productos
- **ProductImage**: Imágenes de productos con soporte para imagen principal y galería
- **Cart / CartItem**: Carrito de compras (soporta usuarios y sesiones anónimas)
- **Order / OrderItem**: Pedidos con estados (pending, confirmed, preparing, shipped, delivered, cancelled)
- **Coupon**: Cupones de descuento con validación de fechas y límites
- **ShippingMethod**: Métodos de envío (retiro en tienda, envío a domicilio)
- **PaymentMethod**: Métodos de pago (tarjeta, transferencia, efectivo)
- **ContactMessage**: Mensajes de contacto
- **MetricEvent**: Eventos de analytics básico

## 🎨 Características de Diseño

- **Bootstrap 5** via CDN para componentes base
- **CSS Personalizado** (`static/css/theme.css`) con:
  - Variables CSS para colores y estilos
  - Animaciones suaves
  - Banner de marcas con scroll infinito
  - Cards de productos responsivos
  - Carousel de productos destacados
  - Diseño mobile-first

## 🔧 Funcionalidades Implementadas

### Páginas

1. **Home (`/`)**: 
   - Hero section
   - Banner de categorías
   - Banner de seguridad y certificaciones
   - Banner de marcas con scroll infinito
   - Sección de ofertas (con imágenes automáticas)
   - Banner de servicios (envío, retiro, pago)
   - Productos más vendidos con carousel
   - Sección "Cómo comprar" y canales oficiales
   - Navbar sticky que se achica al hacer scroll

2. **Lista de Productos (`/productos/`)**: 
   - Filtros por categoría
   - Búsqueda por nombre/marca
   - Ordenamiento (precio, nombre, fecha)
   - Paginación
   - Grid responsive
   - Efecto hover: cambio automático de imágenes cada 2.5s (simula pasar página)
   - Alertas de stock bajo ("Pocas unidades disponibles")

3. **Detalle de Producto (`/productos/<slug>/`)**: 
   - Galería de imágenes con navegación
   - Información completa del producto
   - Agregar al carrito
   - Productos relacionados (con imágenes automáticas)
   - Selección de colores/tallas cuando aplica

4. **Carrito (`/carrito/`)**: 
   - Lista de productos
   - Actualizar cantidades
   - Eliminar productos
   - Aplicar cupones
   - Selección de método de envío (validación condicional)
   - Selección de método de pago
   - Formulario para usuarios anónimos
   - Botón "Continuar comprando" prominente

5. **Checkout**: 
   - Creación de pedido
   - Actualización de stock
   - Aplicación de cupones
   - Cálculo de totales
   - Validación inteligente: campos de envío solo si es necesario
   - Números de pedido personalizados (ID + iniciales + año-día-mes)

6. **Autenticación**: 
   - Registro (`/registro/`)
   - Login (`/iniciar-sesion/`)
   - Logout (`/cerrar-sesion/`)

7. **Perfil de Usuario (`/perfil/`)**: 
   - Edición de información básica (con confirmación)
   - Visualización de pedidos pasados con estado
   - Historial completo de compras

8. **Confirmación de Pedido**: 
   - Resumen del pedido con número personalizado
   - Detalles de productos
   - Información de envío y pago
   - Mensaje de éxito mejorado con instrucciones de contacto
   - Email de confirmación automático

9. **Contacto**: 
   - Formulario de contacto

## 🔐 Seguridad

- CSRF protection habilitado en todos los formularios
- Autenticación de usuarios con Django Auth
- Validación de permisos en carritos y pedidos
- Sanitización de inputs en formularios

## 📱 Responsive Design

El diseño es completamente responsive con:
- Breakpoints de Bootstrap 5
- Mobile-first approach
- Navegación hamburger en móviles
- Grid adaptativo para productos
- Cards y formularios optimizados para móviles

## 🌍 Internacionalización

- Idioma configurado: Español Chile (`es-cl`)
- Zona horaria: `America/Santiago`
- Formato de moneda: CLP con separador de miles (punto)
- Todos los textos en español

## 🔄 Próximos Pasos / Integraciones Pendientes

### Prioridad Alta

1. **Integración de Gateway de Pago**:
   - Integrar Webpay Plus de Transbank (Chile)
   - O integración con Mercado Pago u otro gateway
   - Crear modelo `Payment` para rastrear transacciones
   - Implementar callbacks de confirmación de pago
   - Actualizar estado de pedido según resultado del pago

2. **ReCAPTCHA en Registro**:
   - Integrar Google reCAPTCHA v3 o v2
   - Validación en el formulario de registro
   - Ya existe placeholder en el template

3. **Gestión de Imágenes**:
   - Crear imágenes placeholder para categorías
   - Optimización de imágenes subidas
   - Soporte para múltiples formatos

### Prioridad Media

4. **Notificaciones por Email**: ✅ **IMPLEMENTADO**
   - ✅ Envío de confirmación de pedido al cliente
   - ✅ Notificación al administrador de nuevos pedidos
   - ✅ Integración con Gmail SMTP
   - ⏳ Notificación de cambio de estado (pendiente)
   - ⏳ Recuperación de contraseña (pendiente)

5. **Dashboard de Usuario**: ✅ **PARCIALMENTE IMPLEMENTADO**
   - ✅ Historial de pedidos
   - ✅ Edición de perfil
   - ⏳ Direcciones guardadas (pendiente)

6. **Búsqueda Avanzada**:
   - Filtros múltiples (precio, marca, categoría)
   - Búsqueda con autocompletado

7. **Wishlist/Favoritos**:
   - Guardar productos favoritos
   - Comparación de productos

### Prioridad Baja

8. **Sistema de Reviews**:
   - Comentarios y calificaciones de productos

9. **Programa de Afiliados**:
   - Cupones de referencia
   - Códigos de descuento personalizados

10. **Analytics Mejorado**:
    - Integración con Google Analytics
    - Dashboard de métricas

## 🗃️ Base de Datos

- **Desarrollo**: SQLite (automático cuando `DEBUG=True`)
- **Producción (Render)**: PostgreSQL (automático cuando `DEBUG=False` o `RENDER=True`)

El sistema detecta automáticamente el entorno y configura la base de datos apropiada.

### Configuración Automática

- **Local**: Usa SQLite en `db.sqlite3`
- **Render**: Usa PostgreSQL desde `DATABASE_URL` (variable de entorno)
- **Comandos locales**: Fuerzan SQLite para desarrollo (`runserver`, `load_initial_data`, etc.)

### Persistencia de Archivos

- **Local**: `media/` en el proyecto
- **Render**: `/opt/render/project/src/media` (disco persistente)
- Las imágenes subidas desde el admin persisten entre despliegues

## 📝 Notas de Desarrollo

### Formato de Precios

Los precios se almacenan como enteros (sin decimales) representando CLP.
El filtro `currency_clp` formatea correctamente:
- `66990` → `$66.990`
- `10000000` → `$10.000.000`

### Carrito Anónimo

Los carritos de usuarios no registrados se almacenan usando `session_key`.
Al iniciar sesión, se puede migrar el carrito de la sesión al usuario.

### Stock Management

El stock se actualiza automáticamente al crear un pedido.
Se valida el stock disponible antes de agregar al carrito y antes de crear el pedido.
- Los usuarios no ven el stock exacto, solo alertas cuando hay pocas unidades (< 3)
- Mensaje: "¡Pocas unidades disponibles!" cuando `stock <= 2`

### Gestión de Imágenes

- **Detección automática**: El comando `load_initial_products` detecta automáticamente productos, marcas y categorías desde nombres de archivos
- **Imágenes globales**: Soporte para imágenes compartidas (ej: `AccesoriosShaftGLOB.png` para todos los cascos SHAFT)
- **Imágenes principales**: Primera imagen se marca automáticamente como `is_primary=True`
- **Efecto hover**: En lista de productos, las imágenes cambian automáticamente cada 2.5s al pasar el mouse
- **Persistencia**: En Render, las imágenes se guardan en disco persistente (`/opt/render/project/src/media`)

### Números de Pedido Personalizados

Formato: `{ID}{InicialUsuario}{InicialEmail}{Año-Día-Mes}`

Ejemplo: `15LM2025` (ID=15, Usuario="Lucas", Email="lucas@mail.com", Año=2025, Día+Mes=23+11=34, 2025-34=1991)

### Comandos de Gestión

```bash
# Carga completa de datos iniciales
python manage.py load_initial_data

# Cargar solo productos (con detección automática)
python manage.py load_initial_products --data-dir static/img/productos

# Asignar precios y stock automáticamente
python manage.py set_product_prices

# Configurar ofertas y más vendidos
python manage.py set_featured_products

# Corregir imágenes principales
python manage.py fix_primary_images

# Verificar estado de imágenes
python manage.py verify_images

# Limpiar imágenes duplicadas
python manage.py clean_duplicate_images
```

## 🧪 Testing

Para ejecutar tests (cuando se implementen):
```bash
python manage.py test
```

## 📄 Licencia

Todos los derechos reservados MotoMoto 2025

## 👥 Contacto

- WhatsApp: +569 8211 7748 | +569 8881 5568
- Instagram: @motomotocl
- Web: www.motomoto.cl

---

**Desarrollado con Django 5.2+ | Bootstrap 5 | Python 3.11+**

