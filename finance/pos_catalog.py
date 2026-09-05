"""Catálogo para el buscador de venta física."""
from __future__ import annotations

from decimal import Decimal

from django.db.models import Q

from finance.money import IVA_RATE, quantize_clp
from shop.models import Product


def default_unit_cost_gross(product) -> int:
    gross = int(product.cost_gross or 0)
    if gross > 0:
        return gross
    net = int(product.cost_net or 0)
    if net <= 0:
        return 0
    if getattr(product, 'is_vat_affected', True):
        return int(quantize_clp(Decimal(net) * (Decimal('1') + IVA_RATE)))
    return net


def pos_catalog_qs(q='', category_id=None, brand_id=None, active_only=True):
    qs = (
        Product.objects.select_related('category', 'brand')
        .prefetch_related('variants')
        .order_by('name', 'id')
    )
    if active_only:
        qs = qs.filter(is_active=True)
    text = (q or '').strip()
    if text:
        qs = qs.filter(
            Q(name__icontains=text)
            | Q(sku__icontains=text)
            | Q(brand__name__icontains=text)
            | Q(category__name__icontains=text)
        )
    if category_id:
        qs = qs.filter(category_id=category_id)
    if brand_id:
        qs = qs.filter(brand_id=brand_id)
    return qs


def product_to_pos_dict(product) -> dict:
    variants = [
        {'id': variant.id, 'name': variant.name, 'stock': int(variant.stock)}
        for variant in product.variants.all()
    ]
    return {
        'id': product.id,
        'name': product.name,
        'sku': product.sku or '',
        'price': int(product.current_price or 0),
        'stock': int(product.stock or 0),
        'brand': product.brand.name if product.brand_id else '',
        'brand_id': product.brand_id,
        'category': product.category.name if product.category_id else '',
        'category_id': product.category_id,
        'cost_gross': int(product.cost_gross or 0),
        'cost_net': int(product.cost_net or 0),
        'unit_cost': default_unit_cost_gross(product),
        'variants': variants,
    }


def pos_catalog_payload(products) -> list[dict]:
    return [product_to_pos_dict(product) for product in products]
