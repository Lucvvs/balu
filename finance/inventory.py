"""Proyección de catálogo: si se vende el stock actual al precio publicado."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from finance.calculations import line_gross_margin
from finance.money import ZERO, quantize_clp, split_gross_vat


@dataclass
class ProductPotential:
    units: int
    published_price: Decimal
    list_price: Decimal
    gross: Decimal
    net: Decimal
    vat: Decimal
    cogs: Decimal
    margin: Decimal
    cost_missing: bool
    has_variants: bool


def product_has_variants(product) -> bool:
    cache = getattr(product, '_prefetched_objects_cache', None)
    if cache and 'variants' in cache:
        return bool(cache['variants'])
    return product.variants.exists()


def sellable_units(product) -> int:
    return max(int(product.stock or 0), 0)


def _potential_amounts(product) -> tuple[int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, bool]:
    units = sellable_units(product)
    published = quantize_clp(product.current_price)
    list_price = quantize_clp(product.price)
    cost = quantize_clp(product.cost_net)
    gross = published * units
    net, vat = split_gross_vat(gross, is_vat_affected=bool(product.is_vat_affected))
    cogs = cost * units
    cost_missing = cost <= ZERO and units > 0
    return units, published, list_price, gross, net, vat, cogs, cost_missing


def product_potential(product) -> ProductPotential:
    units, published, list_price, gross, net, vat, cogs, cost_missing = _potential_amounts(product)
    return ProductPotential(
        units=units,
        published_price=published,
        list_price=list_price,
        gross=gross,
        net=net,
        vat=vat,
        cogs=cogs,
        margin=line_gross_margin(net, cogs),
        cost_missing=cost_missing,
        has_variants=product_has_variants(product),
    )


def catalog_potential_totals(products) -> dict:
    """Suma de proyección. No crea ventas ni movimientos."""
    gross = ZERO
    net = ZERO
    vat = ZERO
    cogs = ZERO
    margin = ZERO
    units = 0
    missing_cost = 0
    sku_count = 0
    for product in products:
        row_units, _, _, row_gross, row_net, row_vat, row_cogs, cost_missing = _potential_amounts(product)
        sku_count += 1
        units += row_units
        gross += row_gross
        net += row_net
        vat += row_vat
        cogs += row_cogs
        margin += line_gross_margin(row_net, row_cogs)
        if cost_missing:
            missing_cost += 1
    return {
        'units': units,
        'skus': sku_count,
        'gross': gross,
        'net': net,
        'vat': vat,
        'cogs': cogs,
        'margin': margin,
        'missing_cost': missing_cost,
    }
