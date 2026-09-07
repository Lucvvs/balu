"""Saldos derivados. No se editan; salen del libro, las ventas y el IVA guardado."""
from __future__ import annotations

from datetime import timedelta

from django.db.models import Sum

from finance.kpis import account_balance_on, compute_sales_kpis
from finance.models import FinancialAccount, FinancialMovement, MerchandisePurchase, OperationalExpense
from finance.money import ZERO, to_decimal


def ledger_rows(date_from, date_to, *, account_types=None, account_id=None):
    accounts = FinancialAccount.objects.filter(is_active=True).order_by('account_type', 'name')
    if account_types:
        accounts = accounts.filter(account_type__in=account_types)
    if account_id:
        accounts = accounts.filter(pk=account_id)
    opening_as_of = date_from - timedelta(days=1)
    rows = []
    total_opening = ZERO
    total_in = ZERO
    total_out = ZERO
    total_closing = ZERO
    for account in accounts:
        opening = account_balance_on(account, opening_as_of)
        period = account.movements.filter(
            status='confirmed',
            occurred_on__gte=date_from,
            occurred_on__lte=date_to,
        )
        inflow = to_decimal(period.filter(direction='in').aggregate(total=Sum('amount'))['total'])
        outflow = to_decimal(period.filter(direction='out').aggregate(total=Sum('amount'))['total'])
        closing = account_balance_on(account, date_to)
        rows.append({
            'account': account,
            'opening': opening,
            'inflow': inflow,
            'outflow': outflow,
            'closing': closing,
        })
        total_opening += opening
        total_in += inflow
        total_out += outflow
        total_closing += closing
    return {
        'rows': rows,
        'opening': total_opening,
        'inflow': total_in,
        'outflow': total_out,
        'closing': total_closing,
    }


def period_movements(date_from, date_to, *, account_types=None, account_id=None, limit=40):
    qs = (
        FinancialMovement.objects.filter(
            status='confirmed',
            occurred_on__gte=date_from,
            occurred_on__lte=date_to,
        )
        .select_related('account', 'order')
        .order_by('-occurred_on', '-id')
    )
    if account_id:
        qs = qs.filter(account_id=account_id)
    elif account_types:
        qs = qs.filter(account__account_type__in=account_types)
    return list(qs[:limit])


def tax_snapshot(date_from, date_to, channel: str = '') -> dict:
    """IVA estimado del período. Control interno, no declaración SII."""
    sales = compute_sales_kpis(date_from, date_to, channel)
    purchase_credit = to_decimal(
        MerchandisePurchase.objects.filter(
            occurred_on__gte=date_from,
            occurred_on__lte=date_to,
        ).aggregate(total=Sum('vat_credit'))['total']
    )
    expense_credit = to_decimal(
        OperationalExpense.objects.filter(
            occurred_on__gte=date_from,
            occurred_on__lte=date_to,
        ).aggregate(total=Sum('vat_credit'))['total']
    )
    credit = purchase_credit + expense_credit
    net = sales.vat_debit - credit
    return {
        'vat_debit': sales.vat_debit,
        'purchase_credit': purchase_credit,
        'expense_credit': expense_credit,
        'vat_credit': credit,
        'vat_net': net,
    }


def profitability_steps(kpis) -> list[dict]:
    """Escalera visual: de venta neta al resultado operativo."""
    steps = [
        ('Ventas netas', kpis.net_sales, False),
        ('Costo mercadería', kpis.cogs, True),
        ('Comisión', kpis.commission, True),
        ('Flete asumido', kpis.shipping_assumed, True),
        ('Gastos operativos', kpis.opex, True),
        ('Resultado operativo', kpis.operating_result, False),
    ]
    max_val = max((abs(value) for _label, value, _sub in steps), default=ZERO)
    rows = []
    for label, value, subtracts in steps:
        bar = 0
        if max_val > ZERO and value != ZERO:
            bar = int((abs(value) / max_val) * 100)
        rows.append({
            'label': label,
            'value': value,
            'subtracts': subtracts,
            'bar': bar,
        })
    return rows
