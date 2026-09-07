"""
Cálculos monetarios de MotoMoto.

Toda cifra en CLP se representa con Decimal de escala 0 (pesos enteros).
Prohibido usar float en este módulo.
"""
from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Sequence

CLP_QUANT = Decimal('1')
ZERO = Decimal('0')
IVA_RATE = Decimal('0.19')
IVA_DIVISOR = Decimal('1.19')


def to_decimal(value) -> Decimal:
    """Convierte int/str/Decimal a Decimal. Rechaza float."""
    if isinstance(value, float):
        raise TypeError('No se permite float para montos. Use Decimal o int.')
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize_clp(value, rounding=ROUND_HALF_UP) -> Decimal:
    """Redondea a peso chileno (0 decimales)."""
    return to_decimal(value).quantize(CLP_QUANT, rounding=rounding)


def split_gross_vat(gross, *, is_vat_affected: bool) -> tuple[Decimal, Decimal]:
    """
    Separa venta bruta (IVA incluido) en neto e IVA débito.

    venta_neta = venta_bruta / 1.19  (si es afecto)
    iva_debito = venta_bruta - venta_neta

    El IVA se obtiene por diferencia para que neto + IVA == bruto.
    """
    gross_clp = quantize_clp(gross)
    if gross_clp < ZERO:
        raise ValueError('El monto bruto no puede ser negativo.')
    if not is_vat_affected:
        return gross_clp, ZERO
    net = quantize_clp(gross_clp / IVA_DIVISOR)
    vat = gross_clp - net
    return net, vat


def gross_from_net(net, *, is_vat_affected: bool) -> tuple[Decimal, Decimal]:
    """
    Arma el bruto a partir del neto (catálogo / costo vigente).

    IVA = redondeo(neto × 0.19); bruto = neto + IVA.
    Así neto + IVA == bruto al peso. No usar redondeo(neto × 1.19):
    con 35378 eso daría 42101 y no cierra con el desglose de ventas.
    """
    net_clp = quantize_clp(net)
    if net_clp < ZERO:
        raise ValueError('El monto neto no puede ser negativo.')
    if not is_vat_affected:
        return net_clp, ZERO
    vat = quantize_clp(net_clp * IVA_RATE)
    gross = net_clp + vat
    return gross, vat


def allocate_proportional(total, weights: Sequence) -> list[Decimal]:
    """
    Prorratea `total` según `weights` (típicamente venta neta de cada línea).

    Garantiza SUM(asignaciones) == total usando el método del resto mayor
    (pesos enteros). Si todos los pesos son 0, asigna 0 a cada línea.
    """
    total_clp = quantize_clp(total)
    n = len(weights)
    if n == 0:
        return []
    if total_clp < ZERO:
        raise ValueError('El total a prorratear no puede ser negativo.')

    decimal_weights = [to_decimal(w) for w in weights]
    if any(w < ZERO for w in decimal_weights):
        raise ValueError('Los pesos de prorrateo no pueden ser negativos.')

    weight_sum = sum(decimal_weights, ZERO)
    if total_clp == ZERO or weight_sum == ZERO:
        return [ZERO] * n

    raw = [(total_clp * w) / weight_sum for w in decimal_weights]
    floors = [quantize_clp(x, rounding=ROUND_DOWN) for x in raw]
    remainder = total_clp - sum(floors, ZERO)

    ranked = sorted(
        range(n),
        key=lambda i: (raw[i] - floors[i], -i),
        reverse=True,
    )
    result = list(floors)
    peso = Decimal('1')
    idx = 0
    while remainder > ZERO and idx < n:
        result[ranked[idx]] += peso
        remainder -= peso
        idx += 1
    return result
