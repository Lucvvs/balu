"""Asocia el payment_id de Mercado Pago al Payment creado en checkout (sin duplicar)."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from shop.models import Payment


@transaction.atomic
def attach_mercadopago_payment(order, mp_payment_id: str, *, defaults: dict) -> Payment:
    """
    Reutiliza el Payment pendiente del checkout. Solo crea uno nuevo si no hay
    ninguno que coincida o que aún no tenga mp_payment_id.
    """
    mp_payment_id = str(mp_payment_id)
    locked = Payment.objects.select_for_update().filter(order=order).order_by('id')
    existing = locked.filter(mp_payment_id=mp_payment_id).first()
    if existing:
        return existing
    pending = locked.filter(Q(mp_payment_id__isnull=True) | Q(mp_payment_id='')).first()
    if pending:
        pending.mp_payment_id = mp_payment_id
        pending.save(update_fields=['mp_payment_id'])
        return pending
    return Payment.objects.create(order=order, mp_payment_id=mp_payment_id, **defaults)
