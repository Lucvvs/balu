"""Backfill de snapshots de venta. No mueve tesorería."""
from __future__ import annotations

from shop.models import Order

from finance.services.sale_sync import sync_sale_from_order


def unsynced_orders_qs():
    """Pedidos con al menos una línea sin snapshot. No incluye cancelados ni anulados."""
    return (
        Order.objects.filter(items__finance_synced_at__isnull=True)
        .exclude(status='cancelled')
        .exclude(financial_status='voided')
        .distinct()
        .order_by('created_at', 'pk')
    )


def backfill_unsynced_sales(*, dry_run: bool = False, limit: int | None = None) -> dict:
    """
    Congela el snapshot de pedidos históricos que nunca pasaron por el checkout nuevo.

    Idempotente: las líneas ya sincronizadas no cambian de costo.
    No crea movimientos de tesorería.
    """
    qs = unsynced_orders_qs()
    found = qs.count()
    if limit:
        qs = qs[:limit]
        found = min(found, limit)
    synced = 0
    if not dry_run:
        for order in qs:
            sync_sale_from_order(order)
            synced += 1
    return {
        'found': found,
        'synced': synced,
        'dry_run': dry_run,
    }
