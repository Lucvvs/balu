"""
Sincroniza el snapshot financiero de cada línea de un pedido.

No crea ventas paralelas: opera sobre OrderItem.
No mueve tesorería. El costo histórico se captura una sola vez.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from finance.money import ZERO, allocate_proportional, quantize_clp, split_gross_vat, to_decimal
from shop.models import Order, OrderItem

ALLOCATION_NET_PROPORTIONAL = 'net_proportional'

_LINE_UPDATE_FIELDS = (
    'sku_snapshot',
    'list_unit_price',
    'discount_allocated',
    'gross_sale',
    'net_sale',
    'vat_debit',
    'unit_cost_gross_snapshot',
    'unit_cost_net_snapshot',
    'line_cost_net',
    'shipping_charged_allocated',
    'allocation_method',
    'is_vat_affected',
    'cost_missing',
    'finance_synced_at',
)


def _line_is_vat_affected(order: Order, item: OrderItem) -> bool:
    product_affected = bool(getattr(item.product, 'is_vat_affected', True))
    return bool(order.is_vat_affected) and product_affected


def _pre_discount_net(order: Order, item: OrderItem):
    affected = _line_is_vat_affected(order, item)
    net, _vat = split_gross_vat(item.line_total, is_vat_affected=affected)
    return net


@transaction.atomic
def sync_sale_from_order(order: Order) -> list[OrderItem]:
    """
    Completa SKU, precios, IVA, descuento prorrateado y costo histórico por línea.

    Idempotente respecto al costo: la primera ejecución congela el snapshot;
    las siguientes recalculan descuento/IVA/envío cobrado sin cambiar el costo.
    """
    if not order.pk:
        raise ValueError('El pedido debe estar guardado antes de sincronizar finanzas.')

    items = list(
        order.items.select_related('product').select_for_update().order_by('pk')
    )
    if not items:
        return []

    weights = [_pre_discount_net(order, item) for item in items]
    discounts = allocate_proportional(order.discount_total or 0, weights)
    shipping_charged = allocate_proportional(order.shipping_cost or 0, weights)
    now = timezone.now()

    for item, discount, charged_shipping in zip(items, discounts, shipping_charged):
        product = item.product
        capture_cost = item.finance_synced_at is None
        if capture_cost:
            item.sku_snapshot = (product.sku or '').strip() or f'MM-{product.pk}'
            item.list_unit_price = quantize_clp(product.price)
            item.unit_cost_net_snapshot = quantize_clp(product.cost_net)
            item.unit_cost_gross_snapshot = quantize_clp(product.cost_gross)
            item.cost_missing = item.unit_cost_net_snapshot <= ZERO
            item.finance_synced_at = now

        gross = quantize_clp(item.line_total) - to_decimal(discount)
        if gross < ZERO:
            gross = ZERO

        item.discount_allocated = discount
        item.shipping_charged_allocated = charged_shipping
        item.gross_sale = gross
        item.is_vat_affected = _line_is_vat_affected(order, item)
        net, vat = split_gross_vat(gross, is_vat_affected=item.is_vat_affected)
        item.net_sale = net
        item.vat_debit = vat
        item.line_cost_net = quantize_clp(item.unit_cost_net_snapshot * item.quantity)
        item.allocation_method = ALLOCATION_NET_PROPORTIONAL
        item.save(update_fields=list(_LINE_UPDATE_FIELDS))

    return items
