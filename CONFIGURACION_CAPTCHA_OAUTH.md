# Configuración de CAPTCHA y OAuth con Google

Este documento contiene las instrucciones para completar la configuración de CAPTCHA y OAuth con Google.

## Cambios Implementados

### 1. Modelo de Usuario Personalizado
- ✅ Se creó `CustomUser` que usa email como username
- ✅ Se eliminó el campo `username` de todo el sistema
- ✅ Los mensajes ahora usan `first_name` en lugar de `username`

### 2. CAPTCHA (reCAPTCHA v3)
- ✅ Se integró django-recaptcha en el formulario de registro
- ✅ Se configuró reCAPTCHA v3 (invisible)

### 3. Login con Google OAuth
- ✅ Se configuró django-allauth
- ✅ Se agregaron botones de "Continuar con Google" en login y registro

## Pasos para Completar la Configuración

### 1. Instalar Dependencias

Ejecuta el siguiente comando para instalar las nuevas dependencias:

```bash
pip install -r requirements.txt
```

### 2. Configurar reCAPTCHA

1. Ve a [Google reCAPTCHA Admin Console](https://www.google.com/recaptcha/admin)
2. Crea un nuevo sitio:
   - **Etiqueta**: MotoMoto
   - **Tipo de reCAPTCHA**: reCAPTCHA v3
   - **Dominios**: Agrega tu dominio (ej: `localhost` para desarrollo, `tu-dominio.com` para producción)
3. Copia las claves:
   - **Site Key** (clave pública)
   - **Secret Key** (clave privada)

4. Agrega las claves a tus variables de entorno (`.env` o en Render):

```env
RECAPTCHA_PUBLIC_KEY=tu_site_key_aqui
RECAPTCHA_PRIVATE_KEY=tu_secret_key_aqui
```

### 3. Configurar Google OAuth

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la API de Google+:
   - Ve a "APIs & Services" > "Library"
   - Busca "Google+ API" y habilítala
4. Crea credenciales OAuth 2.0:
   - Ve a "APIs & Services" > "Credentials"
   - Haz clic en "Create Credentials" > "OAuth client ID"
   - Tipo de aplicación: "Web application"
   - **Authorized JavaScript origins**:
     - `http://localhost:8000` (para desarrollo)
     - `https://tu-dominio.com` (para producción)
   - **Authorized redirect URIs**:
     - `http://localhost:8000/accounts/google/login/callback/` (para desarrollo)
     - `https://tu-dominio.com/accounts/google/login/callback/` (para producción)
5. Copia las credenciales:
   - **Client ID**
   - **Client Secret**

6. Agrega las credenciales a tus variables de entorno:

```env
GOOGLE_OAUTH2_CLIENT_ID=tu_client_id_aqui
GOOGLE_OAUTH2_CLIENT_SECRET=tu_client_secret_aqui
```

### 4. Actualizar settings.py

Asegúrate de que `settings.py` tenga las siguientes configuraciones (ya están implementadas):

```python
# En INSTALLED_APPS
'allauth',
'allauth.account',
'allauth.socialaccount',
'allauth.socialaccount.providers.google',
'captcha',

# Modelo de usuario personalizado
AUTH_USER_MODEL = 'shop.CustomUser'

# Django Allauth
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
```

### 5. Crear y Aplicar Migraciones

**IMPORTANTE**: Antes de crear las migraciones, asegúrate de hacer un backup de tu base de datos.

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate
```

**Nota**: Si ya tienes usuarios en la base de datos, necesitarás crear un script de migración de datos para convertir los usuarios existentes del modelo `User` al modelo `CustomUser`. Esto es un proceso complejo que requiere:

1. Exportar datos de usuarios existentes
2. Crear nuevos usuarios con `CustomUser`
3. Actualizar todas las relaciones (pedidos, carritos, etc.)

### 6. Crear Superusuario

Después de aplicar las migraciones, crea un nuevo superusuario:

```bash
python manage.py createsuperuser
```

Usa tu email como "username" (el sistema ahora usa email).

### 7. Configurar Social Account en Admin

1. Ve al admin de Django: `/admin/`
2. Ve a "Social applications" > "Social applications"
3. Agrega una nueva aplicación:
   - **Provider**: Google
   - **Name**: Google
   - **Client id**: Tu Client ID de Google
   - **Secret key**: Tu Client Secret de Google
   - **Sites**: Selecciona tu sitio

### 8. Probar la Configuración

1. **Registro con CAPTCHA**:
   - Ve a `/registro/`
   - Completa el formulario
   - El CAPTCHA debería validarse automáticamente (v3 es invisible)

2. **Login con Email**:
   - Ve a `/iniciar-sesion/`
   - Usa tu email y contraseña

3. **Login con Google**:
   - Haz clic en "Continuar con Google"
   - Deberías ser redirigido a Google para autenticación
   - Después de autenticarte, serás redirigido de vuelta a tu sitio

## Solución de Problemas

### Error: "No module named 'captcha'"
- Asegúrate de haber instalado las dependencias: `pip install -r requirements.txt`

### Error: "No module named 'allauth'"
- Asegúrate de haber instalado las dependencias: `pip install -r requirements.txt`

### Error: "AUTH_USER_MODEL refers to model 'shop.CustomUser' that has not been installed"
- Asegúrate de que `'shop'` esté en `INSTALLED_APPS`
- Ejecuta `python manage.py migrate`

### Error de reCAPTCHA: "Invalid site key"
- Verifica que `RECAPTCHA_PUBLIC_KEY` y `RECAPTCHA_PRIVATE_KEY` estén correctamente configurados
- Asegúrate de que el dominio esté registrado en Google reCAPTCHA

### Error de Google OAuth: "redirect_uri_mismatch"
- Verifica que las URLs de redirección en Google Cloud Console coincidan exactamente con las de tu aplicación
- Asegúrate de incluir tanto `http://` como `https://` según corresponda

### Los usuarios existentes no pueden iniciar sesión
- Necesitarás migrar los datos de usuarios existentes al nuevo modelo `CustomUser`
- Esto requiere un script de migración personalizado

## Notas Importantes

1. **Migración de Usuarios Existentes**: Si ya tienes usuarios en producción, necesitarás crear un script de migración para convertir los usuarios del modelo `User` al modelo `CustomUser`. Esto es crítico y debe hacerse con cuidado.

2. **Backup**: Siempre haz un backup de tu base de datos antes de aplicar migraciones en producción.

3. **Variables de Entorno**: No commitees las claves de reCAPTCHA o Google OAuth en el código. Úsalas siempre como variables de entorno.

4. **Dominios**: Asegúrate de registrar todos los dominios necesarios en Google reCAPTCHA y Google Cloud Console (incluyendo variantes con/sin www, http/https, etc.).

## Próximos Pasos

1. ✅ Instalar dependencias
2. ✅ Configurar reCAPTCHA
3. ✅ Configurar Google OAuth
4. ✅ Crear y aplicar migraciones
5. ✅ Crear superusuario
6. ✅ Configurar Social Account en Admin
7. ✅ Probar funcionalidad
