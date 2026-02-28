# MotoMoto - E-commerce de Accesorios para Motocicletas

Aplicación web Django para tienda de accesorios y equipamiento para motocicletas, desarrollada con Django 5.2+, Bootstrap 5 y diseño responsive.

---

## 📋 Tabla de Contenidos

1. [Descripción del Proyecto](#-descripción-del-proyecto)
2. [Características Principales](#-características-principales)
3. [Requisitos e Instalación](#-requisitos-e-instalación)
4. [Estructura del Proyecto](#-estructura-del-proyecto)
5. [Comandos para Poblar Datos](#-comandos-para-poblar-datos)
6. [Configuración](#-configuración)
7. [Despliegue en Render](#-despliegue-en-render)
8. [Configuración de Servicios](#-configuración-de-servicios)
9. [Solución de Problemas](#-solución-de-problemas)
10. [Changelog](#-changelog)

---

## 🎯 Descripción del Proyecto

MotoMoto es una plataforma de e-commerce completa para la venta de accesorios y equipamiento para motocicletas. Incluye sistema de productos, carrito de compras, gestión de pedidos, cupones de descuento, integración con Mercado Pago, y sistema de notificaciones por email.

---

## 🚀 Características Principales

- **Catálogo de Productos**: Sistema completo de productos con categorías, marcas, imágenes y gestión de stock
- **Carrito de Compras**: Carrito funcional para usuarios registrados y anónimos (basado en sesión)
- **Sistema de Pedidos**: Gestión completa de pedidos con múltiples estados
- **Cupones de Descuento**: Sistema de cupones con validación y límites
- **Métodos de Envío y Pago**: Configuración flexible de métodos de entrega y pago
- **Integración Mercado Pago**: Checkout Pro con webhooks para confirmación de pagos
- **Autenticación de Usuarios**: Registro, login y logout con Django Auth + Google OAuth
- **reCAPTCHA v3**: Protección contra spam en formularios
- **Panel de Administración**: Admin completo con todas las funcionalidades de gestión
- **Sistema de Email**: Notificaciones automáticas al cliente y administrador
- **Responsive Design**: Diseño mobile-first completamente responsive
- **Formato de Moneda CLP**: Formateo personalizado para pesos chilenos

---

## 📋 Requisitos e Instalación

### Requisitos

- Python 3.11+
- Django 5.0+
- Pillow (para manejo de imágenes)
- PostgreSQL (para producción) o SQLite (para desarrollo)

### Instalación Local

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

---

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
│   ├── context_processors.py  # Context processors (carrito)
│   ├── fixtures/          # Datos iniciales (categorías, marcas)
│   ├── management/commands/  # Comandos personalizados
│   └── data/              # Datos JSON (regiones y comunas)
├── templates/             # Plantillas HTML
│   ├── base.html          # Template base
│   ├── partials/          # Componentes reutilizables
│   └── shop/              # Templates de la app
├── static/                # Archivos estáticos
│   ├── css/
│   │   └── theme.css      # Tema CSS personalizado
│   └── img/               # Imágenes estáticas
│       └── productos/     # Imágenes de productos (fuente)
└── media/                 # Archivos de medios (imágenes subidas)
    └── products/          # Imágenes de productos (copiadas)
```

---

## 🗄️ Comandos para Poblar Datos

### Carga Completa Automática (Recomendado)

Ejecuta un solo comando que carga todo automáticamente:

```bash
python manage.py load_initial_data
```

Este comando carga en orden:
1. ✅ Categorías (Maletas, Cascos, Seguridad, Accesorios)
2. ✅ Marcas (HRO, SHAFT, 4RS, motocentric, KOVIX)
3. ✅ Productos con imágenes (detección automática desde `static/img/productos/`)
4. ✅ Asignación de precios y stock (automático)
5. ✅ Corrección de imágenes principales
6. ✅ Configuración de ofertas y más vendidos (3 de cada uno)

### Carga con Forzado de Productos

Si necesitas recargar productos desde cero:

```bash
python manage.py load_initial_data --force-products
```

### Comandos Individuales

```bash
# Cargar solo categorías
python manage.py loaddata shop/fixtures/initial_categories.json

# Cargar solo marcas
python manage.py loaddata shop/fixtures/initial_brands.json

# Cargar solo productos (con detección automática)
python manage.py load_initial_products --data-dir static/img/productos

# Actualizar productos existentes
python manage.py load_initial_products --force

# Limpiar todos los productos y cargar desde cero
python manage.py load_initial_products --clean

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

### Preparación de Imágenes

Coloca todas las imágenes de productos en:
```
static/img/productos/
```

**Formato de nombres (Detección Automática):**
- `Hro514Negro-Rojo1.png` → Producto: "Casco HRO 514 Negro-Rojo", Marca: "HRO", Categoría: "Cascos"
- `kovixKT6negro.png` → Producto: "Candado KOVIX KT6 Negro", Marca: "KOVIX", Categoría: "Seguridad"
- `maletaE7601.png` → Producto: "Maleta 4RS E760", Marca: "4RS", Categoría: "Maletas"

**Imágenes globales:**
- `AccesoriosShaftGLOB.png` → Se asigna a todos los cascos SHAFT
- `soportemaletaGLOB.png` → Se asigna a todas las maletas 4RS

### Carga desde JSON (Alternativa)

Si prefieres usar archivos JSON para productos:

```bash
# Cargar productos desde JSON
python manage.py load_products_from_json

# Forzar actualización
python manage.py load_products_from_json --force

# Limpiar y cargar desde cero
python manage.py load_products_from_json --clean
```

El archivo JSON debe estar en `shop/fixtures/initial_products.json` con la siguiente estructura:

```json
{
  "name": "Casco HRO 514 Negro-Rojo",
  "short_description": "Casco HRO 514 en color Negro-Rojo, certificado DOT y ECE",
  "description": "Descripción completa del producto...",
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
    }
  ]
}
```

---

## ⚙️ Configuración

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto o configura variables de entorno en Render:

#### Variables Requeridas

```env
# Django
SECRET_KEY=tu-secret-key-generada
DEBUG=True  # False en producción
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de Datos (se configura automáticamente en Render)
DATABASE_URL=postgresql://...  # Solo en producción

# Email (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=contraseña-de-aplicacion-16-caracteres
DEFAULT_FROM_EMAIL=tu-email@gmail.com
ADMIN_EMAIL=admin@motomoto.cl

# Mercado Pago
MP_ACCESS_TOKEN=TEST-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MP_PUBLIC_KEY=TEST-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MP_BASE_URL=https://tu-dominio.com
MP_PAYMENT_METHOD_NAME=Mercado Pago

# reCAPTCHA (Opcional)
RECAPTCHA_PUBLIC_KEY=tu_site_key
RECAPTCHA_PRIVATE_KEY=tu_secret_key

# Google OAuth (Opcional)
GOOGLE_OAUTH2_CLIENT_ID=tu_client_id
GOOGLE_OAUTH2_CLIENT_SECRET=tu_client_secret
```

### Generar SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 🚀 Despliegue en Render

### Checklist Pre-Despliegue

- [ ] Código subido a Git (GitHub, GitLab o Bitbucket)
- [ ] `requirements.txt` actualizado con todas las dependencias
- [ ] `build.sh` creado y verificado
- [ ] `render.yaml` configurado (si usas despliegue automático)
- [ ] Variables de entorno identificadas
- [ ] **⚠️ IMPORTANTE: Verificar que `ALLOWED_HOSTS` NO incluya dominios de ngrok en producción**

### Opción 1: Despliegue Automático con render.yaml (Recomendado)

1. **Conecta tu repositorio a Render:**
   - Ve a [Render Dashboard](https://dashboard.render.com/)
   - Haz clic en "New +" → "Blueprint"
   - Conecta tu repositorio Git
   - Render detectará automáticamente el archivo `render.yaml`

2. **Render creará automáticamente:**
   - Servicio Web (Django)
   - Base de datos PostgreSQL
   - Conectará ambos servicios

### Opción 2: Despliegue Manual

#### Paso 1: Crear Base de Datos PostgreSQL

1. En Render Dashboard, haz clic en "New +" → "PostgreSQL"
2. Configura:
   - **Name**: `motomoto-db`
   - **Database**: `motomoto`
   - **User**: `motomoto_user`
   - **Plan**: `Free` (para empezar)
3. Guarda las credenciales (aparecerán en "Internal Database URL")

#### Paso 2: Crear Servicio Web

1. En Render Dashboard, haz clic en "New +" → "Web Service"
2. Conecta tu repositorio Git
3. Configura:
   - **Name**: `motomoto-web`
   - **Region**: Elige el más cercano a tus usuarios
   - **Branch**: `main` o `master`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn motomoto.wsgi:application`

#### Paso 3: Configurar Variables de Entorno

En el panel de Render, ve a tu servicio web → "Environment" y configura todas las variables de entorno necesarias (ver sección de Configuración).

#### Paso 4: Cargar Datos Iniciales

Una vez desplegado, usa el Shell de Render y ejecuta en este orden:

```bash
# 1. Ejecutar migraciones (crear tablas)
python manage.py migrate

# 2. Crear superusuario (para acceder al admin)
python manage.py createsuperuser

# 3. Cargar métodos de envío y pago
python manage.py load_payment_shipping_methods

# 4. Cargar datos iniciales (categorías, marcas y productos)
python manage.py load_initial_data

# 5. Copiar imágenes de marcas a media/brands/
python manage.py copy_brand_images
```

**Nota:** El comando `load_initial_data` carga automáticamente:
- ✅ Categorías (desde `shop/fixtures/initial_categories.json`)
- ✅ Marcas (desde `shop/fixtures/initial_brands.json`)
- ✅ Productos (desde `shop/fixtures/initial_products.json` o detección automática)

### Comandos Útiles en Render Shell

```bash
# Verificar variables de entorno
env | grep DJANGO

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Cargar métodos de envío y pago
python manage.py load_payment_shipping_methods

# Cargar datos iniciales (categorías, marcas y productos)
python manage.py load_initial_data

# Copiar imágenes de marcas
python manage.py copy_brand_images

# Verificar configuración
python manage.py check --deploy
```

---

## 🔧 Configuración de Servicios

### 📧 Configuración de Email con Gmail

#### 1. Habilitar "Contraseña de aplicación" en Gmail

1. Ve a tu cuenta de Google: https://myaccount.google.com/
2. Ve a **Seguridad**
3. Activa la **Verificación en 2 pasos** (si no la tienes activada)
4. Busca **Contraseñas de aplicaciones** (o "App passwords")
5. Selecciona **Correo** y **Otro (nombre personalizado)**
6. Escribe "MotoMoto Django" y haz clic en **Generar**
7. **Copia la contraseña de 16 caracteres** que te muestra

#### 2. Configurar variables de entorno en Render

```
EMAIL_HOST = smtp.gmail.com
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = tu-email@gmail.com
EMAIL_HOST_PASSWORD = [La contraseña de 16 caracteres]
DEFAULT_FROM_EMAIL = tu-email@gmail.com
ADMIN_EMAIL = admin@motomoto.cl
```

**Importante:**
- `EMAIL_HOST_PASSWORD`: La contraseña de aplicación de 16 caracteres (NO tu contraseña normal de Gmail)
- `ADMIN_EMAIL`: El email donde quieres recibir notificaciones de nuevos pedidos

#### 3. Límites de Gmail

- **Gratis**: 500 emails por día
- Si necesitas más, considera usar SendGrid o Mailgun (planes gratuitos disponibles)

### 💳 Integración Mercado Pago (Checkout Pro)

#### 1. Crear credenciales en Mercado Pago

En tu cuenta de Mercado Pago:
- Obtén **Access Token** (privado) y **Public Key** (pública)
- Usa credenciales de **test** para desarrollo y **producción** para go-live

#### 2. Configurar variables de entorno

```env
MP_ACCESS_TOKEN=TEST-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MP_PUBLIC_KEY=TEST-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MP_BASE_URL=https://tu-dominio.com
MP_PAYMENT_METHOD_NAME=Mercado Pago
```

#### 3. Crear el método de pago "Mercado Pago" en Admin

En Django Admin:
- Tabla `PaymentMethod`
  - `name`: **Mercado Pago** (debe coincidir con `MP_PAYMENT_METHOD_NAME`)
  - `is_active`: true

#### 4. Configurar Webhook en Mercado Pago

En Mercado Pago (panel / webhooks):
- URL: `https://tu-dominio.com/mercadopago/webhook/`
- Eventos: **Pagos**

#### 5. Flujo de Pago

- **Checkout**: Si el usuario elige "Mercado Pago", se crea `Order` con estado `pending_payment` y se redirige al `init_point`
- **Return URL**: Solo muestra mensaje al usuario (NO confirma pago)
- **Webhook**: Recibe notificación, consulta el pago por API y:
  - Si `approved`: marca el pedido `confirmed` y descuenta stock
  - Si `rejected/cancelled`: marca el pedido `cancelled`

### 🔐 Configuración de reCAPTCHA y Google OAuth

#### 1. Configurar reCAPTCHA

1. Ve a [Google reCAPTCHA Admin Console](https://www.google.com/recaptcha/admin)
2. Crea un nuevo sitio:
   - **Etiqueta**: MotoMoto
   - **Tipo de reCAPTCHA**: reCAPTCHA v3
   - **Dominios**: Agrega tu dominio
3. Copia las claves y agrega a variables de entorno:
   ```
   RECAPTCHA_PUBLIC_KEY=tu_site_key
   RECAPTCHA_PRIVATE_KEY=tu_secret_key
   ```

#### 2. Configurar Google OAuth

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la API de Google+
4. Crea credenciales OAuth 2.0:
   - Tipo: "Web application"
   - **Authorized JavaScript origins**: `http://localhost:8000` (desarrollo), `https://tu-dominio.com` (producción)
   - **Authorized redirect URIs**: `http://localhost:8000/accounts/google/login/callback/` (desarrollo), `https://tu-dominio.com/accounts/google/login/callback/` (producción)
5. Agrega a variables de entorno:
   ```
   GOOGLE_OAUTH2_CLIENT_ID=tu_client_id
   GOOGLE_OAUTH2_CLIENT_SECRET=tu_client_secret
   ```

#### 3. Configurar Social Account en Admin

1. Ve al admin de Django: `/admin/`
2. Ve a "Social applications" > "Social applications"
3. Agrega una nueva aplicación:
   - **Provider**: Google
   - **Name**: Google
   - **Client id**: Tu Client ID de Google
   - **Secret key**: Tu Client Secret de Google
   - **Sites**: Selecciona tu sitio

---

## 🐛 Solución de Problemas

### Error: "No module named 'psycopg2'"
**Solución**: Verifica que `psycopg2-binary` esté en `requirements.txt`

### Error: "Static files not found"
**Solución**: 
1. Verifica que `build.sh` ejecute `collectstatic`
2. Verifica que `STATIC_ROOT` esté configurado en `settings.py`
3. Verifica que WhiteNoise esté en `MIDDLEWARE`

### Error: "DisallowedHost"
**Solución**: 
- En desarrollo: El código acepta automáticamente `localhost` y `.ngrok-free.dev`
- En producción: El código acepta automáticamente `.onrender.com`
- Si necesitas un dominio específico, configura `ALLOWED_HOSTS` en variables de entorno

### Error: "Database connection failed"
**Solución**: 
1. Verifica que la base de datos PostgreSQL esté creada
2. Verifica que `DATABASE_URL` esté configurada correctamente
3. En Render, conecta la base de datos al servicio web desde la configuración

### Error: "SMTPAuthenticationError" (Email)
**Solución**:
- Verifica que la contraseña de aplicación sea correcta (16 caracteres, sin espacios)
- Asegúrate de que la verificación en 2 pasos esté activada

### Error: "redirect_uri_mismatch" (Google OAuth)
**Solución**:
- Verifica que las URLs de redirección en Google Cloud Console coincidan exactamente con las de tu aplicación
- Asegúrate de incluir tanto `http://` como `https://` según corresponda

### Archivos de Media no persisten
**Solución**: En Render, los archivos en `media/` se eliminan en cada deploy. Para producción:
1. Usa Render Disk (volúmenes persistentes) - ya configurado en `/opt/render/project/src/media`
2. O mejor: usa un servicio de almacenamiento externo (S3, Cloudinary)

### Las imágenes no aparecen
**Solución**:
- Verifica que las imágenes estén en `static/img/productos/` en Git
- Ejecuta `python manage.py load_initial_products --clean` para recargar
- Verifica que las imágenes se copiaron a `media/products/`

### Productos sin Precios/Stock
**Solución**:
```bash
python manage.py set_product_prices --force
```

### Sin Ofertas o Más Vendidos
**Solución**:
```bash
python manage.py set_featured_products
```

---

## 📝 Changelog

### [Última Actualización] - 2025-11-23

#### ✨ Nuevas Funcionalidades

- **Sistema de Imágenes Mejorado**: Detección automática de productos, marcas y categorías desde nombres de archivos
- **Imágenes globales**: Soporte para imágenes compartidas
- **Efecto hover en tarjetas**: Las imágenes cambian automáticamente cada 2.5s
- **Perfil de Usuario**: Nueva sección de perfil con edición de información e historial de pedidos
- **Sistema de Email**: Confirmación de pedido al cliente y notificación al administrador
- **Integración Mercado Pago**: Checkout Pro con webhooks para confirmación de pagos
- **Google OAuth**: Login con Google
- **reCAPTCHA v3**: Protección contra spam

#### 🔧 Mejoras Técnicas

- Detección automática de entorno (SQLite en desarrollo, PostgreSQL en producción)
- Comandos de gestión automatizados para carga de datos
- Sistema de logging configurado
- Persistencia de archivos en Render con disco persistente

#### 🐛 Correcciones

- 404 en placeholder.jpg
- Imágenes no persistentes en Render
- Validación de checkout mejorada
- Prevención de duplicación de imágenes
- Manejo de errores mejorado

---

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
- **CustomUser**: Usuario personalizado que usa email como username

---

## 📱 Responsive Design

El diseño es completamente responsive con:
- Breakpoints de Bootstrap 5
- Mobile-first approach
- Navegación hamburger en móviles
- Grid adaptativo para productos
- Cards y formularios optimizados para móviles

---

## 🌍 Internacionalización

- Idioma configurado: Español Chile (`es-cl`)
- Zona horaria: `America/Santiago`
- Formato de moneda: CLP con separador de miles (punto)
- Todos los textos en español

---

## 📄 Licencia

Todos los derechos reservados MotoMoto 2025

---

## 👥 Contacto

- WhatsApp: +569 8211 7748 | +569 8881 5568
- Instagram: @motomotocl
- Web: www.motomoto.cl

---

**Desarrollado con Django 5.2+ | Bootstrap 5 | Python 3.11+**


# ============================================
# 1. EJECUTAR MIGRACIONES (crear tablas)
# ============================================
python manage.py migrate

# ============================================
# 2. CREAR SUPERUSUARIO (para acceder al admin)
# ============================================
python manage.py createsuperuser
# Te pedirá: email, password, password (confirmación)

# ============================================
# 3. CARGAR MÉTODOS DE ENVÍO Y PAGO
# ============================================
python manage.py load_payment_shipping_methods

# ============================================
# 4. CARGAR DATOS INICIALES
# (Categorías, Marcas y Productos)
# ============================================
python manage.py load_initial_data

# ============================================
# 5. COPIAR IMÁGENES DE MARCAS
# ============================================
python manage.py copy_brand_images