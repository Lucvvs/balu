"""Liquidación de pasarela: comisión real + movimiento de tesorería idempotente."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from finance.models import FinancialAccount, FinancialMovement, PaymentSettlement
from finance.money import allocate_proportional, quantize_clp
from finance.mp_amounts import extract_mp_settlement_amounts, mp_funds_are_released, parse_mp_release_date


def _allocate_commission(order, fee_amount) -> None:
    items = list(order.items.select_for_update().order_by('pk'))
    if not items:
        return
    weights = [item.net_sale for item in items]
    parts = allocate_proportional(fee_amount, weights)
    for item, part in zip(items, parts):
        item.commission_allocated = part
        item.save(update_fields=['commission_allocated'])


def _ensure_settlement_movement(settlement: PaymentSettlement) -> FinancialMovement | None:
    if settlement.status != PaymentSettlement.Status.SETTLED:
        return None
    if settlement.account_id is None:
        return None
    key = f'settlement:mp:{settlement.mp_payment_id}'
    existing = FinancialMovement.objects.filter(idempotency_key=key).first()
    if existing:
        return existing
    occurred = settlement.settled_on or timezone.localdate()
    return FinancialMovement.objects.create(
        account=settlement.account,
        direction=FinancialMovement.Direction.IN,
        amount=quantize_clp(settlement.net_amount),
        occurred_on=occurred,
        movement_type=FinancialMovement.MovementType.SALE_SETTLEMENT,
        status=FinancialMovement.Status.CONFIRMED,
        origin=FinancialMovement.Origin.AUTOMATIC,
        idempotency_key=key,
        payment=settlement.payment,
        settlement=settlement,
        order=settlement.order,
        notes='Liquidación Mercado Pago (neto acreditado).',
    )


@transaction.atomic
def upsert_mp_settlement(payment, mp_payload: dict | None = None, *, account=None) -> PaymentSettlement:
    """
    Crea o actualiza la liquidación del pago MP.

    El banco/digital solo se incrementa cuando el estado es liquidado.
    La comisión se guarda en monto real y se prorratea a las líneas (una sola vez lógica).
    """
    mp_payload = mp_payload or {}
    mp_id = str(payment.mp_payment_id or mp_payload.get('id') or '')
    if not mp_id:
        raise ValueError('Se requiere mp_payment_id para liquidar.')

    payment = type(payment).objects.select_for_update().get(pk=payment.pk)
    gross, fee, net = extract_mp_settlement_amounts(mp_payload)
    if gross == 0:
        from finance.money import to_decimal
        gross = quantize_clp(payment.amount)
        if fee == 0:
            net = gross
    released = mp_funds_are_released(mp_payload)
    release_date = parse_mp_release_date(mp_payload)
    if account is None:
        account = FinancialAccount.get_by_role('mp')

    settlement, _created = PaymentSettlement.objects.select_for_update().get_or_create(
        mp_payment_id=mp_id,
        defaults={
            'payment': payment,
            'order': payment.order,
            'account': account,
            'gross_amount': gross,
            'fee_amount': fee,
            'net_amount': net,
            'status': PaymentSettlement.Status.SETTLED if released else PaymentSettlement.Status.PENDING,
            'settled_on': timezone.localdate() if released else None,
            'money_release_date': release_date,
        },
    )
    settlement.payment = payment
    settlement.order = payment.order
    if account is not None:
        settlement.account = account
    settlement.gross_amount = gross
    settlement.fee_amount = fee
    settlement.net_amount = net
    settlement.money_release_date = release_date
    if released and settlement.status != PaymentSettlement.Status.VOIDED:
        settlement.status = PaymentSettlement.Status.SETTLED
        if settlement.settled_on is None:
            settlement.settled_on = timezone.localdate()
    settlement.save()

    _allocate_commission(payment.order, fee)
    _ensure_settlement_movement(settlement)

    order = payment.order
    if settlement.status == PaymentSettlement.Status.SETTLED:
        if order.financial_status != 'settled':
            order.financial_status = 'settled'
            order.save(update_fields=['financial_status'])
    elif order.financial_status == 'open':
        order.financial_status = 'paid'
        order.save(update_fields=['financial_status'])

    return settlement
