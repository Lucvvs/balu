# Configuración de Email con Gmail

## Pasos para configurar Gmail

### 1. Habilitar "Contraseña de aplicación" en Gmail

1. Ve a tu cuenta de Google: https://myaccount.google.com/
2. Ve a **Seguridad**
3. Activa la **Verificación en 2 pasos** (si no la tienes activada)
4. Busca **Contraseñas de aplicaciones** (o "App passwords")
5. Selecciona **Correo** y **Otro (nombre personalizado)**
6. Escribe "MotoMoto Django" y haz clic en **Generar**
7. **Copia la contraseña de 16 caracteres** que te muestra (la necesitarás)

### 2. Configurar variables de entorno en Render

En el dashboard de Render, ve a tu servicio web y agrega estas **Environment Variables**:

```
EMAIL_HOST = smtp.gmail.com
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = tu-email@gmail.com
EMAIL_HOST_PASSWORD = [La contraseña de 16 caracteres que copiaste]
DEFAULT_FROM_EMAIL = tu-email@gmail.com
ADMIN_EMAIL = admin@motomoto.cl
```

**Importante:**
- `EMAIL_HOST_USER`: Tu email de Gmail completo
- `EMAIL_HOST_PASSWORD`: La contraseña de aplicación de 16 caracteres (NO tu contraseña normal de Gmail)
- `ADMIN_EMAIL`: El email donde quieres recibir notificaciones de nuevos pedidos

### 3. Probar en desarrollo local

En desarrollo local (con `DEBUG=True`), los emails se mostrarán en la consola del terminal, no se enviarán realmente. Esto es útil para probar sin configurar Gmail.

Para probar el envío real en local, puedes:
1. Temporalmente cambiar `EMAIL_BACKEND` a `'django.core.mail.backends.smtp.EmailBackend'` en `settings.py`
2. O crear un archivo `.env` con las credenciales

### 4. Verificar que funciona

1. Crea un pedido de prueba en el sitio
2. Verifica que el cliente recibe el email de confirmación
3. Verifica que el admin recibe la notificación

## Solución de problemas

### Error: "SMTPAuthenticationError"
- Verifica que la contraseña de aplicación sea correcta (16 caracteres, sin espacios)
- Asegúrate de que la verificación en 2 pasos esté activada

### Error: "Connection refused"
- Verifica que `EMAIL_HOST` sea `smtp.gmail.com`
- Verifica que `EMAIL_PORT` sea `587`
- Verifica que `EMAIL_USE_TLS` sea `True`

### Los emails no llegan
- Revisa la carpeta de spam
- Verifica que las variables de entorno estén correctamente configuradas en Render
- Revisa los logs de Render para ver errores

## Límites de Gmail

- **Gratis**: 500 emails por día
- Si necesitas más, considera usar SendGrid o Mailgun (planes gratuitos disponibles)

