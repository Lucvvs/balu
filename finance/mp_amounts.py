"""Montos reales de una respuesta de pago Mercado Pago. Sin float."""
from __future__ import annotations

from datetime import date, datetime

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .money import ZERO, quantize_clp, to_decimal


def extract_mp_settlement_amounts(payload: dict) -> tuple:
    """
    Retorna (bruto, comisión real, neto liquidado) en CLP entero.

    Prioriza net_received_amount y fee_details de la API.
    Si falta el neto, se deriva bruto - comisión.
    """
    payload = payload or {}
    gross = quantize_clp(payload.get('transaction_amount') or 0)
    details = payload.get('transaction_details') or {}
    raw_net = details.get('net_received_amount')
    fee_details = payload.get('fee_details') or []
    fee = ZERO
    for row in fee_details:
        if isinstance(row, dict):
            fee += to_decimal(row.get('amount') or 0)
    fee = quantize_clp(fee)

    if raw_net is None or raw_net == '':
        net = gross - fee
        if net < ZERO:
            net = ZERO
    else:
        net = quantize_clp(raw_net)
        if fee == ZERO and gross > net:
            fee = gross - net
    return gross, fee, net


def parse_mp_release_date(payload: dict):
    payload = payload or {}
    raw = payload.get('money_release_date')
    if not raw:
        details = payload.get('transaction_details') or {}
        raw = details.get('payable_release_date') or details.get('release_date')
    if not raw:
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    parsed = parse_datetime(str(raw))
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
        except ValueError:
            return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return timezone.localtime(parsed).date()


def mp_funds_are_released(payload: dict, *, today=None) -> bool:
    """Sin fecha de liberación, un pago approved se trata como disponible."""
    release = parse_mp_release_date(payload)
    if release is None:
        return True
    if today is None:
        today = timezone.localdate()
    return release <= today
