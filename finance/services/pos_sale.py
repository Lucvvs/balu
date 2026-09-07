"""Venta física (POS): crea un Order de canal pos sin alterar el precio de catálogo."""
from __future__ import annotations

from collections import defaultdict

from django.db import transaction
from django.utils import timezone

from finance.services.sale_sync import sync_sale_from_order
from shop.models import (
    Order,
    OrderItem,
    Payment,
    PaymentMethod,
    Product,
    ProductVariant,
    ShippingMethod,
    is_cash_payment_method,
)


class PosSaleError(ValueError):
    """Error de negocio al registrar una venta en tienda."""


def pos_shipping_method() -> ShippingMethod:
    methods = list(ShippingMethod.objects.filter(is_active=True).order_by('base_price', 'id'))
    for method in methods:
        name = (method.name or '').lower()
        if method.base_price == 0 or 'retiro' in name or 'bodega' in name or 'pickup' in name:
            return method
    if methods:
        return methods[0]
    raise PosSaleError('No hay un método de envío activo para retiro en tienda.')


def pos_payment_methods():
    qs = PaymentMethod.objects.filter(is_active=True).order_by('name')
    allowed = []
    for method in qs:
        name = (method.name or '').lower()
        if 'mercado' in name or 'tarjeta' in name:
            continue
        allowed.append(method.pk)
    if allowed:
        return PaymentMethod.objects.filter(pk__in=allowed).order_by('name')
    return qs


def _payment_type(method: PaymentMethod) -> str:
    name = (method.name or '').lower()
    if is_cash_payment_method(method):
        return 'cash'
    if 'transfer' in name:
        return 'transfer'
    return 'other'


def _published_unit_price(product: Product) -> int:
    return int(product.current_price or 0)


def _merge_lines(lines: list[dict]) -> list[dict]:
    buckets: dict[tuple[int, int | None], int] = defaultdict(int)
    for row in lines:
        product_id = int(row['product_id'])
        variant_id = row.get('variant_id')
        variant_id = int(variant_id) if variant_id else None
        quantity = int(row['quantity'])
        if quantity < 1:
            raise PosSaleError('La cantidad debe ser al menos 1.')
        buckets[(product_id, variant_id)] += quantity
    return [
        {'product_id': product_id, 'variant_id': variant_id, 'quantity': qty}
        for (product_id, variant_id), qty in buckets.items()
    ]


@transaction.atomic
def create_pos_sale(
    *,
    processed_by,
    payment_method: PaymentMethod,
    lines: list[dict],
    customer_name: str = '',
    customer_phone: str = '',
    discount_total: int = 0,
    shipping_cost: int = 0,
    shipping_method: ShippingMethod | None = None,
    notes: str = '',
) -> Order:
    """
    Crea pedido canal pos, descuenta stock y sincroniza finanzas.

    El precio cobrado es el publicado (oferta o lista). Nunca escribe
    Product.price ni Product.offer_price.
    El envío cobrado entra al total del pedido; el flete real al courier
    se registra después en Envíos.
    """
    allowed = pos_payment_methods()
    if not allowed.filter(pk=getattr(payment_method, 'pk', None)).exists():
        raise PosSaleError('La venta física no usa Mercado Pago. Elige efectivo o transferencia.')
    if discount_total < 0:
        raise PosSaleError('El descuento no puede ser negativo.')
    if shipping_cost < 0:
        raise PosSaleError('El envío cobrado no puede ser negativo.')
    shipping_cost = int(shipping_cost or 0)

    merged = _merge_lines(lines)
    if not merged:
        raise PosSaleError('Agrega al menos un producto.')

    if shipping_method is not None:
        if not shipping_method.is_active:
            raise PosSaleError('Elige un método de entrega activo.')
        shipping = shipping_method
    else:
        shipping = pos_shipping_method()
    product_ids = sorted({row['product_id'] for row in merged})
    locked_products = {
        p.id: p
        for p in Product.objects.select_for_update().filter(pk__in=product_ids)
    }
    if len(locked_products) != len(product_ids):
        raise PosSaleError('Uno o más productos ya no están disponibles.')

    variant_ids = sorted({row['variant_id'] for row in merged if row['variant_id']})
    locked_variants = {
        v.id: v
        for v in ProductVariant.objects.select_for_update().filter(pk__in=variant_ids)
    }
    if len(locked_variants) != len(variant_ids):
        raise PosSaleError('Una o más variantes ya no están disponibles.')

    prepared = []
    catalog_prices = {}
    for row in merged:
        product = locked_products[row['product_id']]
        catalog_prices[product.id] = product.price
        variant = locked_variants.get(row['variant_id']) if row['variant_id'] else None
        qty = row['quantity']
        if not product.is_active:
            raise PosSaleError(f'{product.name} no está activo.')
        if variant:
            if variant.product_id != product.id:
                raise PosSaleError(f'La opción no corresponde a {product.name}.')
            if qty > variant.stock:
                raise PosSaleError(
                    f'No hay suficiente stock para {product.name} ({variant.name}). Disponible: {variant.stock}'
                )
        else:
            if product.variants.exists():
                raise PosSaleError(f'{product.name} requiere elegir talla/color.')
            if qty > product.stock:
                raise PosSaleError(
                    f'No hay suficiente stock para {product.name}. Disponible: {product.stock}'
                )
        unit_price = _published_unit_price(product)
        prepared.append({
            'product': product,
            'variant': variant,
            'quantity': qty,
            'unit_price': unit_price,
            'line_total': unit_price * qty,
        })

    subtotal = sum(item['line_total'] for item in prepared)
    if discount_total > subtotal:
        raise PosSaleError('El descuento no puede superar el subtotal.')
    total = subtotal - discount_total + shipping_cost

    order = Order.objects.create(
        user=None,
        shipping_method=shipping,
        shipping_cost=shipping_cost,
        payment_method=payment_method,
        subtotal=subtotal,
        discount_total=discount_total,
        total=total,
        customer_name=(customer_name or '').strip() or 'Cliente tienda',
        customer_phone=(customer_phone or '').strip() or None,
        shipping_notes=(notes or '').strip() or None,
        status='confirmed',
        sales_channel='pos',
        financial_status='paid',
        is_vat_affected=True,
    )

    for item in prepared:
        product = item['product']
        variant = item['variant']
        if variant:
            variant.stock -= item['quantity']
            variant.save(update_fields=['stock'])
            ProductVariant.sync_parent_product_stock(product.id)
            OrderItem.objects.create(
                order=order,
                product=product,
                product_variant=variant,
                product_name=f'{product.name} — {variant.name}',
                variant_label=variant.name,
                unit_price=item['unit_price'],
                quantity=item['quantity'],
                line_total=item['line_total'],
            )
        else:
            product.stock -= item['quantity']
            product.save(update_fields=['stock'])
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                variant_label='',
                unit_price=item['unit_price'],
                quantity=item['quantity'],
                line_total=item['line_total'],
            )

    order.stock_committed = True
    order.save(update_fields=['stock_committed'])
    sync_sale_from_order(order)

    for product_id, original_price in catalog_prices.items():
        current = Product.objects.filter(pk=product_id).values_list('price', flat=True).first()
        if current != original_price:
            raise PosSaleError('La venta física no debe alterar el precio de catálogo.')

    Payment.objects.create(
        order=order,
        payment_method=payment_method,
        amount=total,
        status='approved',
        payment_type=_payment_type(payment_method),
        paid_at=timezone.now(),
        processed_by=processed_by if getattr(processed_by, 'is_authenticated', False) else None,
        notes='Venta física (POS). El pago no mueve tesorería; la caja se actualiza al liquidar.',
    )
    return order
