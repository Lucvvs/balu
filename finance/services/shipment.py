"""Envío como fuente única del flete. Una fila por pedido."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from finance.models import FinancialAccount, FinancialMovement, OrderShipment
from finance.money import ZERO, allocate_proportional, quantize_clp, to_decimal


class ShipmentError(ValueError):
    pass


def _require_account(account: FinancialAccount) -> FinancialAccount:
    if account is None or not account.is_active:
        raise ShipmentError('Elige una cuenta de tesorería activa para pagar el flete.')
    return account


def _allocate_assumed(order, assumed) -> None:
    items = list(order.items.select_for_update().order_by('pk'))
    if not items:
        raise ShipmentError('El pedido no tiene líneas para prorratear el flete.')
    weights = [item.net_sale for item in items]
    if all(to_decimal(w) == ZERO for w in weights):
        weights = [item.quantity for item in items]
    parts = allocate_proportional(assumed, weights)
    for item, part in zip(items, parts):
        item.shipping_assumed_allocated = part
        item.save(update_fields=['shipping_assumed_allocated'])


@transaction.atomic
def upsert_shipment(
    *,
    order,
    actual_cost,
    assumed_cost=None,
    account=None,
    carrier: str = '',
    tracking_code: str = '',
    occurred_on=None,
    notes: str = '',
    user=None,
) -> OrderShipment:
    """
    Crea o actualiza el único envío del pedido.

    El cobrado al cliente sale de Order.shipping_cost.
    El asumido se prorratea a las líneas y entra al margen de contribución.
    Si hay costo real > 0, sale tesorería una sola vez (idempotente).
    """
    if order is None or not order.pk:
        raise ShipmentError('Indica el pedido.')
    from shop.models import Order

    order = Order.objects.select_for_update().get(pk=order.pk)
    actual = quantize_clp(actual_cost)
    if actual < ZERO:
        raise ShipmentError('El costo real no puede ser negativo.')
    assumed = quantize_clp(assumed_cost) if assumed_cost is not None else actual
    if assumed < ZERO:
        raise ShipmentError('El costo asumido no puede ser negativo.')
    charged = quantize_clp(order.shipping_cost or 0)
    occurred = occurred_on or timezone.localdate()
    pay_account = None
    if actual > ZERO:
        pay_account = _require_account(account)

    shipment, created = OrderShipment.objects.select_for_update().get_or_create(
        order=order,
        defaults={
            'account': pay_account,
            'carrier': (carrier or '').strip(),
            'tracking_code': (tracking_code or '').strip(),
            'charged_amount': charged,
            'actual_cost': actual,
            'assumed_cost': assumed,
            'occurred_on': occurred,
            'notes': (notes or '').strip(),
            'created_by': user if getattr(user, 'is_authenticated', False) else None,
        },
    )
    if not created:
        existing_move = shipment.movements.filter(
            status=FinancialMovement.Status.CONFIRMED,
            movement_type=FinancialMovement.MovementType.SHIPMENT,
        ).first()
        if existing_move and existing_move.amount != actual:
            raise ShipmentError(
                'El flete ya se pagó. No se cambia el monto de tesorería; registra un ajuste si hace falta.'
            )
        shipment.carrier = (carrier or '').strip() or shipment.carrier
        shipment.tracking_code = (tracking_code or '').strip() or shipment.tracking_code
        shipment.charged_amount = charged
        shipment.actual_cost = actual
        shipment.assumed_cost = assumed
        shipment.occurred_on = occurred
        if notes:
            shipment.notes = notes.strip()
        if pay_account is not None and shipment.account_id is None:
            shipment.account = pay_account
        shipment.save()

    _allocate_assumed(order, assumed)

    if actual > ZERO and pay_account is not None:
        key = f'shipment:{order.pk}:out'
        if not FinancialMovement.objects.filter(idempotency_key=key).exists():
            FinancialMovement.objects.create(
                account=pay_account,
                direction=FinancialMovement.Direction.OUT,
                amount=actual,
                occurred_on=occurred,
                movement_type=FinancialMovement.MovementType.SHIPMENT,
                status=FinancialMovement.Status.CONFIRMED,
                origin=FinancialMovement.Origin.MANUAL,
                idempotency_key=key,
                notes=f'Flete pedido #{order.order_number or order.pk}. No es gasto operativo.',
                created_by=shipment.created_by,
                order=order,
                shipment=shipment,
            )
    return shipment
