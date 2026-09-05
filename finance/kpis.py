"""Agregados de KPIs en base de datos. No cargar miles de líneas en Python."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from finance.calculations import contribution_margin, margin_percentage
from finance.models import FinancialAccount, FinancialMovement, OperationalExpense, OrderRefundItem
from finance.money import ZERO, to_decimal
from shop.models import OrderItem


def parse_date(value, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return fallback


def default_period() -> tuple[date, date]:
    today = timezone.localdate()
    return today.replace(day=1), today


def previous_period(date_from: date, date_to: date) -> tuple[date, date]:
    span = (date_to - date_from).days + 1
    prev_to = date_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=span - 1)
    return prev_from, prev_to


def _aware_range(date_from: date, date_to: date):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(date_from, time.min), tz)
    end = timezone.make_aware(datetime.combine(date_to, time.max), tz)
    return start, end


def sales_lines_qs(date_from: date, date_to: date, channel: str = ''):
    start, end = _aware_range(date_from, date_to)
    qs = (
        OrderItem.objects.filter(
            finance_synced_at__isnull=False,
            order__created_at__gte=start,
            order__created_at__lte=end,
        )
        .exclude(order__status='cancelled')
        .exclude(order__financial_status='voided')
    )
    if channel in ('web', 'pos'):
        qs = qs.filter(order__sales_channel=channel)
    return qs


def _sum(qs, field) -> Decimal:
    return to_decimal(qs.aggregate(total=Sum(field))['total'])


@dataclass
class SalesKpis:
    net_sales: Decimal
    gross_sales: Decimal
    vat_debit: Decimal
    cogs: Decimal
    gross_margin: Decimal
    contribution: Decimal
    commission: Decimal
    shipping_assumed: Decimal
    other_variable: Decimal
    opex: Decimal
    operating_result: Decimal
    units: int
    orders: int


def compute_sales_kpis(date_from: date, date_to: date, channel: str = '') -> SalesKpis:
    qs = sales_lines_qs(date_from, date_to, channel)
    agg = qs.aggregate(
        net=Sum('net_sale'),
        gross=Sum('gross_sale'),
        vat=Sum('vat_debit'),
        cogs=Sum('line_cost_net'),
        commission=Sum('commission_allocated'),
        shipping=Sum('shipping_assumed_allocated'),
        other=Sum('other_variable_allocated'),
        units=Sum('quantity'),
        orders=Count('order', distinct=True),
    )
    net = to_decimal(agg['net'])
    cogs = to_decimal(agg['cogs'])
    commission = to_decimal(agg['commission'])
    shipping = to_decimal(agg['shipping'])
    other = to_decimal(agg['other'])
    units = int(agg['units'] or 0)
    refunds = period_refunds(date_from, date_to, channel)
    net -= refunds['net']
    cogs -= refunds['cogs']
    commission -= refunds['commission']
    shipping -= refunds['shipping']
    vat = to_decimal(agg['vat']) - refunds['vat']
    gross = to_decimal(agg['gross']) - refunds['gross']
    units -= refunds['units']
    if units < 0:
        units = 0
    opex = period_opex(date_from, date_to)
    contrib = contribution_margin(net, cogs, commission, shipping, other)
    operating = contrib - opex
    return SalesKpis(
        net_sales=net,
        gross_sales=gross,
        vat_debit=vat,
        cogs=cogs,
        gross_margin=net - cogs,
        contribution=contrib,
        commission=commission,
        shipping_assumed=shipping,
        other_variable=other,
        opex=opex,
        operating_result=operating,
        units=units,
        orders=int(agg['orders'] or 0),
    )


def period_opex(date_from: date, date_to: date) -> Decimal:
    """Opex del período. Independiente del canal de venta; no incluye compras."""
    return to_decimal(
        OperationalExpense.objects.filter(
            occurred_on__gte=date_from,
            occurred_on__lte=date_to,
        ).aggregate(total=Sum('net_amount'))['total']
    )


def period_refunds(date_from: date, date_to: date, channel: str = '') -> dict:
    """Devoluciones del período. No reescribe las líneas originales."""
    qs = OrderRefundItem.objects.filter(
        refund__occurred_on__gte=date_from,
        refund__occurred_on__lte=date_to,
    )
    if channel in ('web', 'pos'):
        qs = qs.filter(refund__order__sales_channel=channel)
    agg = qs.aggregate(
        net=Sum('net_amount'),
        gross=Sum('gross_amount'),
        vat=Sum('vat_amount'),
        cogs=Sum('cogs_amount'),
        commission=Sum('commission_amount'),
        shipping=Sum('shipping_assumed_amount'),
        units=Sum('quantity'),
    )
    return {
        'net': to_decimal(agg['net']),
        'gross': to_decimal(agg['gross']),
        'vat': to_decimal(agg['vat']),
        'cogs': to_decimal(agg['cogs']),
        'commission': to_decimal(agg['commission']),
        'shipping': to_decimal(agg['shipping']),
        'units': int(agg['units'] or 0),
    }


def percent_delta(current, previous) -> Decimal | None:
    current = to_decimal(current)
    previous = to_decimal(previous)
    if previous == ZERO:
        return None
    value = ((current - previous) / abs(previous)) * Decimal('100')
    return value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def format_delta(delta: Decimal | None) -> str:
    if delta is None:
        return ''
    sign = '+' if delta >= 0 else ''
    text = f'{sign}{delta}'.replace('.', ',')
    return f'{text}%'


def contribution_ranking(date_from: date, date_to: date, channel: str = '', limit: int = 8):
    qs = (
        sales_lines_qs(date_from, date_to, channel)
        .values('product_id', 'product_name', 'sku_snapshot')
        .annotate(
            net=Sum('net_sale'),
            cogs=Sum('line_cost_net'),
            commission=Sum('commission_allocated'),
            shipping=Sum('shipping_assumed_allocated'),
            other=Sum('other_variable_allocated'),
        )
    )
    rows = []
    for row in qs:
        contrib = contribution_margin(
            row['net'], row['cogs'], row['commission'], row['shipping'], row['other']
        )
        rows.append({
            'product_id': row['product_id'],
            'name': row['product_name'],
            'sku': row['sku_snapshot'],
            'contribution': contrib,
            'net': to_decimal(row['net']),
            'share': ZERO,
            'bar': 0,
        })
    rows.sort(key=lambda r: r['contribution'], reverse=True)
    rows = rows[:limit]
    total = sum((r['contribution'] for r in rows), ZERO)
    max_val = max((r['contribution'] for r in rows), default=ZERO)
    for row in rows:
        row['share'] = margin_percentage(row['contribution'], total) if total else ZERO
        if max_val > ZERO and row['contribution'] > ZERO:
            row['bar'] = int((row['contribution'] / max_val) * Decimal('100'))
        else:
            row['bar'] = 0
    return rows


def account_balance_on(account: FinancialAccount, as_of: date) -> Decimal:
    confirmed = account.movements.filter(status='confirmed', occurred_on__lte=as_of)
    inflows = to_decimal(confirmed.filter(direction='in').aggregate(total=Sum('amount'))['total'])
    outflows = to_decimal(confirmed.filter(direction='out').aggregate(total=Sum('amount'))['total'])
    return to_decimal(account.opening_balance) + inflows - outflows


def treasury_snapshot(date_from: date, date_to: date, account_id=None):
    accounts = FinancialAccount.objects.filter(is_active=True)
    if account_id:
        accounts = accounts.filter(pk=account_id)
    accounts = list(accounts)
    movements = FinancialMovement.objects.filter(
        status='confirmed',
        occurred_on__gte=date_from,
        occurred_on__lte=date_to,
    )
    if account_id:
        movements = movements.filter(account_id=account_id)
    inflow = to_decimal(movements.filter(direction='in').aggregate(total=Sum('amount'))['total'])
    outflow = to_decimal(movements.filter(direction='out').aggregate(total=Sum('amount'))['total'])
    cash = ZERO
    banks = ZERO
    for acc in accounts:
        bal = account_balance_on(acc, date_to)
        if acc.account_type == FinancialAccount.AccountType.CASH:
            cash += bal
        else:
            banks += bal
    timeline = list(
        movements.select_related('account', 'order')
        .order_by('-occurred_on', '-id')[:12]
    )
    return {
        'inflow': inflow,
        'outflow': outflow,
        'remaining': cash + banks,
        'cash': cash,
        'banks': banks,
        'timeline': timeline,
        'accounts': accounts,
    }


def filters_from_request(request) -> dict:
    date_from, date_to = default_period()
    date_from = parse_date(request.GET.get('date_from'), date_from)
    date_to = parse_date(request.GET.get('date_to'), date_to)
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    channel = (request.GET.get('channel') or '').strip()
    account = request.GET.get('account') or ''
    account_id = None
    if account.isdigit():
        account_id = int(account)
    return {
        'date_from': date_from,
        'date_to': date_to,
        'channel': channel if channel in ('web', 'pos') else '',
        'account_id': account_id,
    }
