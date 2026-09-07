"""Devoluciones. La venta original permanece intacta."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from finance.models import FinancialAccount, FinancialMovement, OrderRefund, OrderRefundItem
from finance.money import ZERO, quantize_clp, to_decimal
from shop.models import Order, OrderItem, Product, ProductVariant


class RefundError(ValueError):
    pass


def _require_account(account: FinancialAccount) -> FinancialAccount:
    if account is None or not account.is_active:
        raise RefundError('Elige una cuenta de tesorería activa para devolver el dinero.')
    return account


def qty_already_refunded(order_item: OrderItem) -> int:
    return int(
        order_item.refund_lines.aggregate(total=Sum('quantity'))['total'] or 0
    )


def _sum_refunded(order_item: OrderItem, field: str):
    return to_decimal(order_item.refund_lines.aggregate(total=Sum(field))['total'])


def _slice_line(item: OrderItem, quantity: int) -> dict:
    remaining_qty = item.quantity - qty_already_refunded(item)
    if quantity < 1:
        raise RefundError('La cantidad a devolver debe ser al menos 1.')
    if quantity > remaining_qty:
        raise RefundError(
            f'{item.product_name} solo admite devolver {remaining_qty} unidad(es).'
        )
    remaining = {
        'gross': quantize_clp(item.gross_sale) - _sum_refunded(item, 'gross_amount'),
        'net': quantize_clp(item.net_sale) - _sum_refunded(item, 'net_amount'),
        'vat': quantize_clp(item.vat_debit) - _sum_refunded(item, 'vat_amount'),
        'cogs': quantize_clp(item.line_cost_net) - _sum_refunded(item, 'cogs_amount'),
        'commission': quantize_clp(item.commission_allocated) - _sum_refunded(item, 'commission_amount'),
        'shipping': quantize_clp(item.shipping_assumed_allocated) - _sum_refunded(item, 'shipping_assumed_amount'),
    }
    if quantity == remaining_qty:
        sliced = {key: max(value, ZERO) for key, value in remaining.items()}
        sliced['quantity'] = quantity
        return sliced
    ratio = Decimal(quantity) / Decimal(remaining_qty)
    sliced = {key: quantize_clp(value * ratio) for key, value in remaining.items()}
    sliced['quantity'] = quantity
    return sliced


def _restore_qty(item: OrderItem, quantity: int) -> None:
    if item.product_variant_id:
        ProductVariant.objects.filter(pk=item.product_variant_id).update(stock=F('stock') + quantity)
        ProductVariant.sync_parent_product_stock(item.product_id)
    else:
        Product.objects.filter(pk=item.product_id).update(stock=F('stock') + quantity)


def _refresh_financial_status(order: Order) -> None:
    items = list(order.items.all())
    if not items:
        return
    fully = all(qty_already_refunded(item) >= item.quantity for item in items)
    order.financial_status = 'refunded' if fully else 'partially_refunded'
    order.save(update_fields=['financial_status'])


@transaction.atomic
def record_refund(
    *,
    order,
    lines: list[dict],
    occurred_on=None,
    account=None,
    restores_stock: bool = True,
    notes: str = '',
    user=None,
) -> OrderRefund:
    """
    Registra una devolución. No borra OrderItem ni pisa snapshots.

    lines: [{'order_item_id': int, 'quantity': int}, ...]
    Si hay cuenta, el bruto sale de tesorería (plata que vuelve al cliente).
    """
    if order is None or not order.pk:
        raise RefundError('Indica el pedido.')
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status == 'cancelled' or order.financial_status == 'voided':
        raise RefundError('No se devuelve un pedido anulado.')
    prepared = []
    for row in lines:
        item_id = int(row['order_item_id'])
        qty = int(row['quantity'])
        item = (
            OrderItem.objects.select_for_update()
            .filter(pk=item_id, order=order)
            .first()
        )
        if not item:
            raise RefundError('Una línea no pertenece a este pedido.')
        prepared.append((item, _slice_line(item, qty)))
    if not prepared:
        raise RefundError('Indica qué unidades se devuelven.')

    pay_account = _require_account(account) if account is not None else None
    refund = OrderRefund.objects.create(
        order=order,
        account=pay_account,
        occurred_on=occurred_on or timezone.localdate(),
        restores_stock=restores_stock,
        notes=(notes or '').strip(),
        created_by=user if getattr(user, 'is_authenticated', False) else None,
    )
    gross_total = ZERO
    net_total = ZERO
    vat_total = ZERO
    cogs_total = ZERO
    for item, sliced in prepared:
        OrderRefundItem.objects.create(
            refund=refund,
            order_item=item,
            quantity=sliced['quantity'],
            gross_amount=sliced['gross'],
            net_amount=sliced['net'],
            vat_amount=sliced['vat'],
            cogs_amount=sliced['cogs'],
            commission_amount=sliced['commission'],
            shipping_assumed_amount=sliced['shipping'],
        )
        gross_total += sliced['gross']
        net_total += sliced['net']
        vat_total += sliced['vat']
        cogs_total += sliced['cogs']
        if restores_stock:
            _restore_qty(item, sliced['quantity'])

    refund.gross_amount = gross_total
    refund.net_amount = net_total
    refund.vat_amount = vat_total
    refund.cogs_amount = cogs_total
    refund.save(update_fields=['gross_amount', 'net_amount', 'vat_amount', 'cogs_amount'])
    _refresh_financial_status(order)

    if pay_account is not None and gross_total > ZERO:
        FinancialMovement.objects.create(
            account=pay_account,
            direction=FinancialMovement.Direction.OUT,
            amount=gross_total,
            occurred_on=refund.occurred_on,
            movement_type=FinancialMovement.MovementType.REFUND,
            status=FinancialMovement.Status.CONFIRMED,
            origin=FinancialMovement.Origin.MANUAL,
            idempotency_key=f'refund:{refund.pk}:out',
            notes=f'Devolución pedido #{order.order_number or order.pk}. La venta original no se borra.',
            created_by=refund.created_by,
            order=order,
            refund=refund,
        )
    return refund
