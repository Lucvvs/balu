"""Compra de mercadería: tesorería, costo vigente y stock opcional."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from finance.models import FinancialAccount, FinancialMovement, MerchandisePurchase, PurchaseLine
from finance.money import ZERO, quantize_clp, split_gross_vat
from shop.models import Product, ProductVariant


class PurchaseError(ValueError):
    pass


def _require_account(account: FinancialAccount) -> FinancialAccount:
    if account is None or not account.is_active:
        raise PurchaseError('Elige una cuenta de tesorería activa.')
    return account


def _merge_lines(lines: list[dict]) -> list[dict]:
    buckets: dict[tuple, dict] = {}
    for row in lines:
        product_id = int(row['product_id'])
        variant_id = int(row['variant_id']) if row.get('variant_id') else None
        quantity = int(row['quantity'])
        unit_gross = quantize_clp(row['unit_cost_gross'])
        if quantity < 1:
            raise PurchaseError('La cantidad debe ser al menos 1.')
        if unit_gross <= ZERO:
            raise PurchaseError('El costo unitario debe ser mayor a 0.')
        key = (product_id, variant_id)
        if key in buckets:
            buckets[key]['quantity'] += quantity
            buckets[key]['unit_cost_gross'] = unit_gross
        else:
            buckets[key] = {
                'product_id': product_id,
                'variant_id': variant_id,
                'quantity': quantity,
                'unit_cost_gross': unit_gross,
            }
    return list(buckets.values())


@transaction.atomic
def register_purchase(
    *,
    account,
    supplier: str,
    lines: list[dict],
    occurred_on=None,
    updates_stock: bool = True,
    updates_catalog_cost: bool = True,
    is_vat_affected: bool = True,
    notes: str = '',
    user=None,
) -> MerchandisePurchase:
    """
    Paga mercadería. Opcionalmente suma stock y actualiza el costo vigente.

    Nunca escribe Product.price. No crea ventas ni gastos operativos.
    El costo histórico de pedidos ya sincronizados no se recalcula.
    """
    account = _require_account(account)
    name = (supplier or '').strip()
    if not name:
        raise PurchaseError('Indica el proveedor.')
    merged = _merge_lines(lines)
    if not merged:
        raise PurchaseError('Agrega al menos un producto.')

    product_ids = sorted({row['product_id'] for row in merged})
    locked_products = {
        p.id: p for p in Product.objects.select_for_update().filter(pk__in=product_ids)
    }
    if len(locked_products) != len(product_ids):
        raise PurchaseError('Uno o más productos ya no existen.')
    catalog_prices = {pk: product.price for pk, product in locked_products.items()}

    variant_ids = sorted({row['variant_id'] for row in merged if row['variant_id']})
    locked_variants = {
        v.id: v for v in ProductVariant.objects.select_for_update().filter(pk__in=variant_ids)
    }
    if len(locked_variants) != len(variant_ids):
        raise PurchaseError('Una o más variantes ya no existen.')

    prepared = []
    gross_total = ZERO
    net_total = ZERO
    vat_total = ZERO
    for row in merged:
        product = locked_products[row['product_id']]
        variant = locked_variants.get(row['variant_id']) if row['variant_id'] else None
        if variant and variant.product_id != product.id:
            raise PurchaseError(f'La opción no corresponde a {product.name}.')
        if updates_stock and not variant and product.variants.exists():
            raise PurchaseError(f'{product.name} requiere talla/color para sumar stock.')
        unit_gross = row['unit_cost_gross']
        unit_net, unit_vat = split_gross_vat(unit_gross, is_vat_affected=is_vat_affected)
        qty = row['quantity']
        line_gross = unit_gross * qty
        line_net = unit_net * qty
        line_vat = unit_vat * qty
        gross_total += line_gross
        net_total += line_net
        vat_total += line_vat
        prepared.append({
            'product': product,
            'variant': variant,
            'quantity': qty,
            'unit_net': unit_net,
            'unit_gross': unit_gross,
            'line_net': line_net,
            'line_gross': line_gross,
            'line_vat': line_vat,
        })

    purchase = MerchandisePurchase.objects.create(
        supplier=name,
        account=account,
        occurred_on=occurred_on or timezone.localdate(),
        updates_stock=updates_stock,
        updates_catalog_cost=updates_catalog_cost,
        is_vat_affected=is_vat_affected,
        gross_total=gross_total,
        net_total=net_total,
        vat_credit=vat_total,
        notes=(notes or '').strip(),
        created_by=user if getattr(user, 'is_authenticated', False) else None,
    )

    for item in prepared:
        product = item['product']
        variant = item['variant']
        PurchaseLine.objects.create(
            purchase=purchase,
            product=product,
            product_variant=variant,
            product_name=product.name,
            variant_label=variant.name if variant else '',
            sku_snapshot=(product.sku or '').strip() or f'MM-{product.pk}',
            quantity=item['quantity'],
            unit_cost_net=item['unit_net'],
            unit_cost_gross=item['unit_gross'],
            line_net=item['line_net'],
            line_gross=item['line_gross'],
            line_vat=item['line_vat'],
        )
        if updates_stock:
            if variant:
                variant.stock += item['quantity']
                variant.save(update_fields=['stock'])
                ProductVariant.sync_parent_product_stock(product.id)
            else:
                product.stock += item['quantity']
                product.save(update_fields=['stock', 'updated_at'])
        if updates_catalog_cost:
            product.cost_net = item['unit_net']
            product.cost_gross = item['unit_gross']
            product.save(update_fields=['cost_net', 'cost_gross', 'updated_at'])

    for product_id, original_price in catalog_prices.items():
        current = Product.objects.filter(pk=product_id).values_list('price', flat=True).first()
        if current != original_price:
            raise PurchaseError('La compra no debe alterar el precio de venta del catálogo.')

    FinancialMovement.objects.create(
        account=account,
        direction=FinancialMovement.Direction.OUT,
        amount=gross_total,
        occurred_on=purchase.occurred_on,
        movement_type=FinancialMovement.MovementType.PURCHASE,
        status=FinancialMovement.Status.CONFIRMED,
        origin=FinancialMovement.Origin.MANUAL,
        idempotency_key=f'purchase:{purchase.pk}:out',
        notes=f'Compra a {name}. No es gasto operativo ni venta.',
        created_by=purchase.created_by,
        purchase=purchase,
    )
    return purchase
