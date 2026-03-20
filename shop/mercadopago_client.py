from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from django.conf import settings


@dataclass(frozen=True)
class MercadoPagoPreferenceResult:
    preference_id: str
    init_point: str


def _get_sdk():
    """
    Crea cliente Mercado Pago (SDK oficial).
    Requiere settings.MP_ACCESS_TOKEN.
    """
    import mercadopago  # type: ignore

    if not getattr(settings, "MP_ACCESS_TOKEN", ""):
        raise RuntimeError("Falta configurar MP_ACCESS_TOKEN en variables de entorno.")
    return mercadopago.SDK(settings.MP_ACCESS_TOKEN)


def create_checkout_pro_preference(
    *,
    order_id: int,
    order_number: str,
    total_amount_clp: int,
    buyer_email: Optional[str],
    success_url: str,
    pending_url: str,
    failure_url: str,
    notification_url: str,
    item_id: Optional[str] = None,
    item_category_id: Optional[str] = None,
    item_description: Optional[str] = None,
) -> MercadoPagoPreferenceResult:
    """
    Crea una preferencia para Checkout Pro.
    Para evitar problemas con cupones/envío, se crea 1 solo item por el total del pedido.
    """
    sdk = _get_sdk()

    preference_data: dict[str, Any] = {
        "items": [
            {
                "title": f"Pedido {order_number}",
                "quantity": 1,
                "currency_id": "CLP",
                "unit_price": int(total_amount_clp),
                # Recomendaciones Mercado Pago para mejorar tasa de aprobación.
                "id": str(item_id) if item_id else str(order_id),
                "category_id": str(item_category_id) if item_category_id else "",
                "description": item_description if item_description else f"Pedido {order_number}",
            }
        ],
        "external_reference": str(order_id),
        "back_urls": {
            "success": success_url,
            "pending": pending_url,
            "failure": failure_url,
        },
        "auto_return": "approved",
        "notification_url": notification_url,
        # "statement_descriptor": "MotoMoto",  # opcional (según país/cuenta)
    }

    if buyer_email:
        preference_data["payer"] = {"email": buyer_email}

    response = sdk.preference().create(preference_data)
    data = (response or {}).get("response") or {}

    preference_id = data.get("id")
    init_point = data.get("init_point")
    if not preference_id or not init_point:
        raise RuntimeError(f"Error creando preferencia Mercado Pago: {data}")

    return MercadoPagoPreferenceResult(preference_id=str(preference_id), init_point=str(init_point))


def get_payment(payment_id: str) -> dict[str, Any]:
    """Obtiene un pago por ID (para webhooks)."""
    sdk = _get_sdk()
    response = sdk.payment().get(payment_id)
    return (response or {}).get("response") or {}

