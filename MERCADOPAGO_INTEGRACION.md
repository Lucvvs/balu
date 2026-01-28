# Integración Mercado Pago (Checkout Pro) — MotoMoto (Django)

Este documento deja la integración **paso a paso** y reusable para futuros proyectos.

## Qué pasarela integrar (la más fácil y funcional)

Para permitir pagos con **tarjeta de débito/crédito** con el menor esfuerzo y buena confiabilidad, integra **Mercado Pago — Checkout Pro**:

- Mercado Pago aloja el formulario de pago (PCI compliance, antifraude, validaciones).
- Tú solo creas una **Preferencia** (server-side) y rediriges al usuario a pagar.
- Confirmas el pago por **Webhook** (source of truth), no por el “return”.

## Flujo implementado en este repo

- **Checkout (Django)**:
  - Si el usuario elige el método de pago “Mercado Pago”, el sistema:
    - Crea `Order` con estado `pending_payment`
    - Crea la preferencia Checkout Pro y redirige al `init_point`
- **Return URL**:
  - Solo muestra mensaje al usuario (NO confirma pago).
- **Webhook**:
  - Recibe notificación, consulta el pago por API y:
    - Si `approved`: marca el pedido `confirmed` y **descuenta stock** (idempotente)
    - Si `rejected/cancelled/...`: marca el pedido `cancelled`

## Archivos clave

- Backend MP client: `shop/mercadopago_client.py`
- Webhook + retorno + checkout MP: `shop/views.py`
- Rutas: `shop/urls.py`
- Config: `motomoto/settings.py`
- Modelo: `shop/models.py` (campos `mp_*` y `stock_committed`)
- UI: `templates/shop/order_confirmation.html`

## Paso a paso (setup)

### 1) Crear credenciales en Mercado Pago

En tu cuenta de Mercado Pago:

- Obtén **Access Token** (privado) y **Public Key** (pública).
- Usa credenciales de **test** para desarrollo y **producción** para go-live.

### 2) Configurar variables de entorno

En tu `.env` (o variables del hosting):

```env
MP_ACCESS_TOKEN=TEST-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MP_PUBLIC_KEY=TEST-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# URL pública base de tu sitio (IMPORTANTE)
MP_BASE_URL=https://tu-dominio.com

# Opcional: si quieres fijar el webhook explícitamente
# MP_WEBHOOK_URL=https://tu-dominio.com/mercadopago/webhook/

# Debe coincidir con el nombre del PaymentMethod en la BD
MP_PAYMENT_METHOD_NAME=Mercado Pago
```

Notas:
- **Nunca** expongas `MP_ACCESS_TOKEN` en frontend.
- `MP_BASE_URL` debe ser accesible públicamente para que Mercado Pago pueda pegarle al webhook y para los `back_urls`.

### 3) Crear el método de pago “Mercado Pago” en Admin

En Django Admin:

- Tabla `PaymentMethod`
  - `name`: **Mercado Pago** (debe coincidir con `MP_PAYMENT_METHOD_NAME`)
  - `is_active`: true

### 4) Configurar Webhook en Mercado Pago

En Mercado Pago (panel / webhooks):

- URL: `https://tu-dominio.com/mercadopago/webhook/`
- Eventos: **Pagos**

### 5) Probar flujo en local (recomendado)

Como Mercado Pago necesita pegarle a una URL pública:

- Usa un túnel (ej: `ngrok`) y configura `MP_BASE_URL` con esa URL.
- Asegúrate que el endpoint `/mercadopago/webhook/` sea accesible.

### 6) Probar con tarjetas de test

Mercado Pago provee tarjetas de prueba por país (depende de tu cuenta/país).

Checklist de prueba:

- Pago aprobado → `Order.status = confirmed`, `mp_payment_status = approved`, `stock_committed = true`
- Pago rechazado/cancelado → `Order.status = cancelled`
- Pago pendiente → `Order.status = pending_payment`

## Detalles de implementación importantes

### “Return” NO confirma pago

El usuario vuelve por:

- `.../mercadopago/return/success/<order_id>/`
- `.../mercadopago/return/pending/<order_id>/`
- `.../mercadopago/return/failure/<order_id>/`

Eso solo muestra mensajes. La confirmación real viene por webhook.

### Stock e idempotencia

El webhook:

- Descuenta stock solo una vez con `stock_committed`.
- Usa transacciones + `select_for_update()` para evitar carreras.

### Item único por total

Para evitar complejidad con cupón/envío, la preferencia se crea con **1 item**:

- `title`: Pedido X
- `unit_price`: `order.total`

Si en el futuro quieres desglosar, se puede:
- Mandar 1 item por producto
- Agregar “Envío” como item
- Ajustar descuentos (ojo: MP no acepta items con precio negativo; suele resolverse prorrateando)

## Go-live (producción)

- Cambia a credenciales de **producción** (ACCESS_TOKEN / PUBLIC_KEY).
- Configura `MP_BASE_URL` con el dominio real.
- Configura webhook en Mercado Pago al dominio real.
- Revisa `ALLOWED_HOSTS` si aplica (en tu `settings.py` hoy se permite `*` en prod).

## Troubleshooting rápido

- **Te redirige pero no confirma**: webhook no llega (URL no pública / firewall / mal `MP_BASE_URL`).
- **Webhook llega pero no actualiza**: revisa logs y que `external_reference` sea el `order.id`.
- **Stock no descuenta**: revisa `stock_committed` y que `status` del pago sea `approved`.

