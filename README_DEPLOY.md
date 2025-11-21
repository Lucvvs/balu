# Guía de Despliegue en Render - MotoMoto

Esta guía explica cómo desplegar la aplicación Django MotoMoto en Render.

## 📋 Requisitos Previos

1. Cuenta en [Render.com](https://render.com)
2. Repositorio Git (GitHub, GitLab o Bitbucket) con el código
3. Cliente Git configurado

## 🚀 Pasos para Desplegar

### Opción 1: Despliegue Automático con render.yaml (Recomendado)

Render puede usar el archivo `render.yaml` para configurar todo automáticamente.

1. **Conecta tu repositorio a Render:**
   - Ve a [Render Dashboard](https://dashboard.render.com/)
   - Haz clic en "New +" → "Blueprint"
   - Conecta tu repositorio Git
   - Render detectará automáticamente el archivo `render.yaml`

2. **Ajusta las configuraciones:**
   - Edita `render.yaml` y cambia `ALLOWED_HOSTS` por tu dominio de Render
   - El dominio será algo como: `motomoto-xxxx.onrender.com`

3. **Render creará automáticamente:**
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

   **Basic Settings:**
   - **Name**: `motomoto-web`
   - **Region**: Elige el más cercano a tus usuarios
   - **Branch**: `main` o `master`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn motomoto.wsgi:application`

   **Environment Variables:**
   Agrega las siguientes variables de entorno:

   ```
   PYTHON_VERSION=3.11.0
   SECRET_KEY=<genera-una-secret-key-segura>
   DEBUG=False
   ALLOWED_HOSTS=<tu-dominio>.onrender.com
   DATABASE_URL=<copiar-desde-postgres-internal-database-url>
   ```

   **Para generar SECRET_KEY:**
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

4. Haz clic en "Create Web Service"

#### Paso 3: Cargar Datos Iniciales

Una vez desplegado, necesitas cargar las categorías, marcas y productos iniciales.

**Opción A: Desde el Shell de Render**
1. Ve a tu servicio web en Render
2. Haz clic en "Shell" (o usa SSH)
3. Ejecuta:
   ```bash
   python manage.py load_initial_data
   ```

**Opción B: Usando Render Shell desde terminal local**
```bash
# Instalar render-cli (opcional)
npm install -g render-cli

# Conectar al servicio
render shell

# Ejecutar comandos
python manage.py load_initial_data
python manage.py createsuperuser
```

## 📝 Configuración de Variables de Entorno

En el panel de Render, ve a tu servicio web → "Environment" y configura:

### Variables Requeridas:

- **SECRET_KEY**: Clave secreta de Django (genera una nueva, nunca uses la del código)
- **DEBUG**: `False` (en producción)
- **ALLOWED_HOSTS**: Tu dominio de Render (ej: `motomoto-xxxx.onrender.com`)
- **DATABASE_URL**: Se configura automáticamente si conectas la base de datos

### Generar SECRET_KEY:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 🔧 Configuración de Static Files

Los archivos estáticos se recopilan automáticamente durante el build gracias a WhiteNoise.

Los archivos en `static/` se servirán automáticamente.
Los archivos de `media/` (imágenes de productos subidos) se almacenan en el sistema de archivos del servidor.

**⚠️ Nota**: Para producción, considera usar un servicio de almacenamiento como:
- AWS S3
- Cloudinary
- Render Disk (para archivos persistentes)

## 📦 Estructura de Archivos para Render

Los siguientes archivos son importantes para el despliegue:

- `render.yaml` - Configuración automática de servicios
- `build.sh` - Script de build que ejecuta migraciones y collectstatic
- `requirements.txt` - Dependencias de Python
- `.env.example` - Ejemplo de variables de entorno (no se sube a producción)

## 🗄️ Base de Datos

### En Desarrollo (Local):
- SQLite (`db.sqlite3`)

### En Producción (Render):
- PostgreSQL (configurado automáticamente)

El código detecta automáticamente `DATABASE_URL` y usa PostgreSQL si está disponible.

## 🚨 Solución de Problemas

### Error: "No module named 'psycopg2'"
**Solución**: Verifica que `psycopg2-binary` esté en `requirements.txt`

### Error: "Static files not found"
**Solución**: 
1. Verifica que `build.sh` ejecute `collectstatic`
2. Verifica que `STATIC_ROOT` esté configurado en `settings.py`
3. Verifica que WhiteNoise esté en `MIDDLEWARE`

### Error: "DisallowedHost"
**Solución**: Agrega tu dominio de Render a `ALLOWED_HOSTS` en las variables de entorno

### Error: "Database connection failed"
**Solución**: 
1. Verifica que la base de datos PostgreSQL esté creada
2. Verifica que `DATABASE_URL` esté configurada correctamente
3. En Render, conecta la base de datos al servicio web desde la configuración

### Archivos de Media no persisten
**Solución**: En Render, los archivos en `media/` se eliminan en cada deploy. Para producción:
1. Usa Render Disk (volúmenes persistentes)
2. O mejor: usa un servicio de almacenamiento externo (S3, Cloudinary)

## 📊 Monitoreo y Logs

- **Logs**: Ve a tu servicio web → "Logs" para ver logs en tiempo real
- **Métricas**: Render proporciona métricas básicas en el dashboard

## 🔄 Actualizar el Despliegue

Cada vez que hagas `git push` a tu rama principal, Render:
1. Detecta el cambio
2. Ejecuta `build.sh`
3. Reinicia el servicio automáticamente

Para ejecutar migraciones manualmente:
1. Usa el Shell de Render
2. Ejecuta: `python manage.py migrate`

## ✅ Checklist Pre-Despliegue

- [ ] `requirements.txt` incluye todas las dependencias
- [ ] `DEBUG=False` en producción
- [ ] `SECRET_KEY` generada y configurada
- [ ] `ALLOWED_HOSTS` configurado con tu dominio
- [ ] Base de datos PostgreSQL creada
- [ ] `DATABASE_URL` configurada
- [ ] Archivo `build.sh` tiene permisos de ejecución
- [ ] Imágenes iniciales en `static/img/productos/` (si usas carga inicial)
- [ ] Superusuario creado (para acceder al admin)

## 🌐 Dominio Personalizado

Para usar un dominio personalizado:

1. Ve a tu servicio web → "Settings" → "Custom Domains"
2. Agrega tu dominio
3. Configura los registros DNS según las instrucciones de Render
4. Actualiza `ALLOWED_HOSTS` para incluir tu dominio personalizado

## 📞 Soporte

- [Documentación de Render](https://render.com/docs)
- [Render Community Forum](https://community.render.com/)

¡Listo para desplegar! 🚀

