"""Evolución de ventas netas del período. Barras CSS; no Chart.js."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from django.utils import timezone

from finance.kpis import sales_lines_qs
from finance.models import OrderRefundItem
from finance.money import ZERO, to_decimal

_MONTHS = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            return timezone.localtime(value).date()
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _grain(date_from: date, date_to: date) -> str:
    span = (date_to - date_from).days + 1
    if span <= 21:
        return 'day'
    if span <= 120:
        return 'week'
    return 'month'


def _bucket_key(value: date, grain: str) -> date:
    if grain == 'week':
        return value - timedelta(days=value.weekday())
    if grain == 'month':
        return value.replace(day=1)
    return value


def _buckets(date_from: date, date_to: date, grain: str) -> list[tuple[date, str]]:
    rows = []
    if grain == 'day':
        cursor = date_from
        while cursor <= date_to:
            rows.append((cursor, cursor.strftime('%d/%m')))
            cursor += timedelta(days=1)
        return rows
    if grain == 'week':
        cursor = date_from - timedelta(days=date_from.weekday())
        while cursor <= date_to:
            rows.append((cursor, cursor.strftime('%d/%m')))
            cursor += timedelta(days=7)
        return rows
    cursor = date_from.replace(day=1)
    while cursor <= date_to:
        label = _MONTHS[cursor.month - 1]
        if date_from.year != date_to.year:
            label = f'{label} {cursor.year}'
        rows.append((cursor, label))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return rows


def _add(keyed: dict, key: date, amount) -> None:
    keyed[key] = to_decimal(keyed.get(key)) + to_decimal(amount)


def sales_evolution(date_from: date, date_to: date, channel: str = '') -> dict:
    """Agrupa en Python. SQLite revienta con TruncDate sobre DateField."""
    grain = _grain(date_from, date_to)
    sales: dict[date, object] = {}
    for created_at, net in sales_lines_qs(date_from, date_to, channel).values_list(
        'order__created_at', 'net_sale'
    ):
        day = _as_date(created_at)
        if day is None:
            continue
        _add(sales, _bucket_key(day, grain), net)

    refunds_qs = OrderRefundItem.objects.filter(
        refund__occurred_on__gte=date_from,
        refund__occurred_on__lte=date_to,
    )
    if channel in ('web', 'pos'):
        refunds_qs = refunds_qs.filter(refund__order__sales_channel=channel)
    refunds: dict[date, object] = {}
    for occurred_on, net in refunds_qs.values_list('refund__occurred_on', 'net_amount'):
        day = _as_date(occurred_on)
        if day is None:
            continue
        _add(refunds, _bucket_key(day, grain), net)

    points = []
    max_abs = ZERO
    for key, label in _buckets(date_from, date_to, grain):
        net = to_decimal(sales.get(key)) - to_decimal(refunds.get(key))
        abs_net = abs(net)
        if abs_net > max_abs:
            max_abs = abs_net
        points.append({'key': key, 'label': label, 'net': net, 'bar': 0, 'negative': net < ZERO})
    for point in points:
        if max_abs > ZERO and point['net'] != ZERO:
            point['bar'] = int((abs(point['net']) / max_abs) * 100)
            if point['bar'] < 2:
                point['bar'] = 2
    return {
        'grain': grain,
        'points': points,
        'max': max_abs,
        'has_values': max_abs > ZERO,
    }
