# ✅ Checklist de Despliegue en Render

## Antes de Desplegar

- [ ] Código subido a Git (GitHub, GitLab o Bitbucket)
- [ ] `requirements.txt` actualizado con todas las dependencias
- [ ] `build.sh` creado y verificado
- [ ] `render.yaml` configurado (si usas despliegue automático)
- [ ] Variables de entorno identificadas

## Configuración en Render Dashboard

### 1. Base de Datos PostgreSQL
- [ ] Crear servicio PostgreSQL en Render
- [ ] Guardar credenciales de conexión
- [ ] Anotar `Internal Database URL`

### 2. Servicio Web Django
- [ ] Conectar repositorio Git a Render
- [ ] Configurar Build Command: `./build.sh`
- [ ] Configurar Start Command: `gunicorn motomoto.wsgi:application`
- [ ] Configurar Python Version: `3.11.0`

### 3. Variables de Entorno
Configurar las siguientes variables en el servicio web:

- [ ] **SECRET_KEY**: Generar nueva clave secreta
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- [ ] **DEBUG**: `False`
- [ ] **ALLOWED_HOSTS**: (Opcional) Ya configurado automáticamente. Solo configura si necesitas restringir a un dominio específico
- [ ] **DATABASE_URL**: Copiar desde PostgreSQL → "Internal Database URL" (o se configura automáticamente con render.yaml)
- [ ] **PYTHON_VERSION**: `3.11.0` (opcional, ya está en build.sh)

## Post-Despliegue

### 1. Verificar Despliegue
- [ ] Servicio web iniciado correctamente
- [ ] Sin errores en los logs
- [ ] Base de datos conectada

### 2. Ejecutar Migraciones
- [ ] Conectar al shell de Render
- [ ] Ejecutar: `python manage.py migrate`
- [ ] Verificar que las migraciones se ejecutaron

### 3. Crear Superusuario
- [ ] Ejecutar: `python manage.py createsuperuser`
- [ ] Configurar usuario y contraseña
- [ ] Verificar acceso a `/admin/`

### 4. Cargar Datos Iniciales
- [ ] Ejecutar: `python manage.py load_initial_data`
- [ ] Verificar categorías cargadas
- [ ] Verificar marcas cargadas
- [ ] Verificar productos cargados (si aplica)

### 5. Verificar Funcionalidad
- [ ] Acceder a la página principal
- [ ] Verificar que los static files se cargan (CSS, imágenes)
- [ ] Verificar que los productos se muestran
- [ ] Verificar que el carrito funciona
- [ ] Probar login/logout

## Configuración Adicional (Opcional)

### Archivos Media Persistentes
- [ ] Configurar Render Disk (volúmenes persistentes) si necesitas que los archivos subidos persistan
- [ ] O configurar servicio de almacenamiento externo (AWS S3, Cloudinary)

### Dominio Personalizado
- [ ] Agregar dominio personalizado en Render
- [ ] Configurar registros DNS
- [ ] Actualizar `ALLOWED_HOSTS` con el nuevo dominio
- [ ] Verificar certificado SSL

## Troubleshooting

Si encuentras problemas, revisa:

1. **Logs del servicio**: Render Dashboard → Tu servicio → Logs
2. **Variables de entorno**: Verificar que todas estén configuradas
3. **Base de datos**: Verificar conexión en el panel de PostgreSQL
4. **Static files**: Verificar que `collectstatic` se ejecutó en el build

## Comandos Útiles en Render Shell

```bash
# Verificar variables de entorno
env | grep DJANGO

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Cargar datos iniciales
python manage.py load_initial_data

# Verificar configuración
python manage.py check --deploy
```

## Recursos

- 📖 [README_DEPLOY.md](README_DEPLOY.md) - Guía completa de despliegue
- 🌐 [Render Dashboard](https://dashboard.render.com/)
- 📚 [Documentación de Render](https://render.com/docs)

¡Despliegue exitoso! 🚀

