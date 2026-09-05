"""Alertas operativas del Resumen. Enlazan a la pantalla donde se corrige."""
from __future__ import annotations

from django.urls import reverse
from django.utils import timezone

from finance.balances import tax_snapshot
from finance.kpis import account_balance_on, sales_lines_qs
from finance.models import FinancialAccount, Financing, PaymentSettlement
from finance.money import ZERO
from shop.models import Product


def _clp(amount) -> str:
    return f'${int(amount):,}'.replace(',', '.')


def _qs(date_from, date_to, channel: str, extra: str = '') -> str:
    parts = [f'date_from={date_from.isoformat()}', f'date_to={date_to.isoformat()}']
    if channel:
        parts.append(f'channel={channel}')
    if extra:
        parts.append(extra)
    return '&'.join(parts)


def finance_alerts(date_from=None, date_to=None, channel: str = '') -> list[dict]:
    today = timezone.localdate()
    date_from = date_from or today.replace(day=1)
    date_to = date_to or today
    query = _qs(date_from, date_to, channel)
    items = []

    negative = 0
    for account in FinancialAccount.objects.filter(is_active=True):
        if account_balance_on(account, today) < ZERO:
            negative += 1
    if negative:
        items.append({
            'text': f'{negative} cuenta{"s" if negative != 1 else ""} con saldo negativo',
            'tone': 'danger',
            'href': f"{reverse('finance:balances')}?{query}&panel=caja",
        })

    missing_cost = sales_lines_qs(date_from, date_to, channel).filter(cost_missing=True).count()
    if missing_cost:
        items.append({
            'text': f'{missing_cost} venta{"s" if missing_cost != 1 else ""} sin costo histórico',
            'tone': 'warn',
            'href': f"{reverse('finance:sales_lines')}?{query}&missing_cost=1",
        })

    out_of_stock = Product.objects.filter(is_active=True, stock=0).count()
    if out_of_stock:
        items.append({
            'text': f'{out_of_stock} producto{"s" if out_of_stock != 1 else ""} activo{"s" if out_of_stock != 1 else ""} sin stock',
            'tone': 'warn',
            'href': f"{reverse('finance:inventory')}?{query}&stock=out",
        })

    tax = tax_snapshot(date_from, date_to, channel)
    if tax['vat_net'] > ZERO:
        items.append({
            'text': f'IVA estimado a pagar {_clp(tax["vat_net"])}',
            'tone': 'warn',
            'href': f"{reverse('finance:balances')}?{query}&panel=impuestos",
        })

    pending = PaymentSettlement.objects.filter(status=PaymentSettlement.Status.PENDING).count()
    if pending:
        items.append({
            'text': f'{pending} liquidación{"es" if pending != 1 else ""} pendiente{"s" if pending != 1 else ""}',
            'tone': 'warn',
            'href': f"{reverse('finance:sales_lines')}?{query}",
        })

    open_loans = 0
    for loan in Financing.objects.filter(kind=Financing.Kind.LOAN):
        if loan.outstanding() > ZERO:
            open_loans += 1
    if open_loans:
        items.append({
            'text': f'{open_loans} préstamo{"s" if open_loans != 1 else ""} con saldo pendiente',
            'tone': 'warn',
            'href': f"{reverse('finance:financing')}?{query}",
        })
    return items
