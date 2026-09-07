"""
Fórmulas financieras de dominio. Única fuente: no duplicar en templates/JS.
"""
from __future__ import annotations

from decimal import Decimal

from .money import ZERO, quantize_clp, split_gross_vat, to_decimal


def line_gross_margin(net_sale, cost_net) -> Decimal:
    """margen_bruto = venta_neta - costo_neto_historico"""
    return quantize_clp(to_decimal(net_sale) - to_decimal(cost_net))


def margin_percentage(margin, net_sale) -> Decimal:
    """
    margen_bruto_porcentaje = margen_bruto / venta_neta * 100
    Si venta_neta es 0, retorna 0 (evita división por cero).
    """
    net = to_decimal(net_sale)
    if net == ZERO:
        return ZERO
    return (to_decimal(margin) / net) * Decimal('100')


def contribution_margin(
    net_sale,
    cost_net,
    commission=ZERO,
    shipping_assumed=ZERO,
    other_variable=ZERO,
) -> Decimal:
    """
    margen_contribucion = venta_neta
        - costo_neto_historico
        - comision_medio_pago
        - costo_envio_asumido
        - otros_costos_variables
    """
    return quantize_clp(
        to_decimal(net_sale)
        - to_decimal(cost_net)
        - to_decimal(commission)
        - to_decimal(shipping_assumed)
        - to_decimal(other_variable)
    )


def sale_components(gross_sale, cost_net, *, is_vat_affected: bool) -> dict[str, Decimal]:
    """Desglose de una línea de venta a partir del bruto cobrado y el costo histórico."""
    net, vat = split_gross_vat(gross_sale, is_vat_affected=is_vat_affected)
    cost = quantize_clp(cost_net)
    gross_m = line_gross_margin(net, cost)
    return {
        'gross_sale': quantize_clp(gross_sale),
        'net_sale': net,
        'vat_debit': vat,
        'cost_net': cost,
        'gross_margin': gross_m,
        'gross_margin_pct': margin_percentage(gross_m, net),
    }
