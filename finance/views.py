from decimal import Decimal
from urllib.parse import quote

from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, render

from finance.balances import ledger_rows, period_movements, profitability_steps, tax_snapshot
from finance.alerts import finance_alerts
from finance.decorators import finance_view_required
from finance.kpis import (
    compute_sales_kpis,
    contribution_ranking,
    filters_from_request,
    format_delta,
    percent_delta,
    previous_period,
    sales_lines_qs,
    treasury_snapshot,
)
from finance.models import FinancialAccount
from finance.page_context import filter_context, sales_querystring
from finance.series import sales_evolution
from shop.models import OrderItem

BALANCE_PANELS = ('caja', 'bancos', 'ventas', 'rentabilidad', 'impuestos')


@finance_view_required
def resumen(request):
    filters = filters_from_request(request)
    current = compute_sales_kpis(filters['date_from'], filters['date_to'], filters['channel'])
    prev_from, prev_to = previous_period(filters['date_from'], filters['date_to'])
    previous = compute_sales_kpis(prev_from, prev_to, filters['channel'])
    treasury = treasury_snapshot(filters['date_from'], filters['date_to'], filters['account_id'])
    ranking = contribution_ranking(filters['date_from'], filters['date_to'], filters['channel'])

    def kpi_pack(current_value, previous_value):
        delta = percent_delta(current_value, previous_value)
        return {
            'value': current_value,
            'delta': format_delta(delta),
            'up': delta is not None and delta >= 0,
            'has_delta': delta is not None,
        }

    context = {
        'finance_section': 'resumen',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'operating': kpi_pack(current.operating_result, previous.operating_result),
        'net_sales': kpi_pack(current.net_sales, previous.net_sales),
        'contribution': kpi_pack(current.contribution, previous.contribution),
        'opex': kpi_pack(current.opex, previous.opex),
        'vat_debit': current.vat_debit,
        'treasury': treasury,
        'ranking': ranking,
        'evolution': sales_evolution(filters['date_from'], filters['date_to'], filters['channel']),
        'alerts': finance_alerts(
            date_from=filters['date_from'],
            date_to=filters['date_to'],
            channel=filters['channel'],
        ),
        'prev_from': prev_from,
        'prev_to': prev_to,
    }
    return render(request, 'finance/resumen.html', context)


@finance_view_required
def sales_lines(request):
    filters = filters_from_request(request)
    kpis = compute_sales_kpis(filters['date_from'], filters['date_to'], filters['channel'])
    qs = (
        sales_lines_qs(filters['date_from'], filters['date_to'], filters['channel'])
        .select_related('order', 'order__payment_method', 'product')
        .annotate(gross_margin_amount=F('net_sale') - F('line_cost_net'))
        .order_by('-order__created_at', '-id')
    )
    search = (request.GET.get('q') or '').strip()
    missing_cost = request.GET.get('missing_cost') == '1'
    if search:
        qs = qs.filter(
            Q(product_name__icontains=search)
            | Q(sku_snapshot__icontains=search)
            | Q(order__order_number__icontains=search)
        )
    if missing_cost:
        qs = qs.filter(cost_missing=True)
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page') or 1)
    list_query = sales_querystring(filters)
    if search:
        list_query += f'&q={quote(search)}'
    if missing_cost:
        list_query += '&missing_cost=1'
    context = {
        'finance_section': 'ingresos',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'list_query': list_query,
        'page': page,
        'search': search,
        'missing_cost': missing_cost,
        'kpis': kpis,
    }
    return render(request, 'finance/sales_lines.html', context)


@finance_view_required
def sales_line_detail(request, item_id: int):
    filters = filters_from_request(request)
    item = get_object_or_404(
        OrderItem.objects.select_related(
            'order', 'order__payment_method', 'order__shipping_method', 'product', 'product_variant'
        ),
        pk=item_id,
    )
    context = {
        'finance_section': 'ingresos',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'item': item,
        'order': item.order,
    }
    return render(request, 'finance/sales_line_detail.html', context)


@finance_view_required
def balances(request):
    filters = filters_from_request(request)
    panel = (request.GET.get('panel') or 'caja').strip()
    if panel not in BALANCE_PANELS:
        panel = 'caja'
    kpis = compute_sales_kpis(filters['date_from'], filters['date_to'], filters['channel'])
    cash = ledger_rows(
        filters['date_from'],
        filters['date_to'],
        account_types=[FinancialAccount.AccountType.CASH],
        account_id=filters['account_id'],
    )
    banks = ledger_rows(
        filters['date_from'],
        filters['date_to'],
        account_types=[FinancialAccount.AccountType.BANK, FinancialAccount.AccountType.DIGITAL],
        account_id=filters['account_id'],
    )
    types_for_panel = None
    if panel == 'caja':
        types_for_panel = [FinancialAccount.AccountType.CASH]
    elif panel == 'bancos':
        types_for_panel = [FinancialAccount.AccountType.BANK, FinancialAccount.AccountType.DIGITAL]
    movements = period_movements(
        filters['date_from'],
        filters['date_to'],
        account_types=types_for_panel,
        account_id=filters['account_id'],
    )
    context = {
        'finance_section': 'saldos',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'panel': panel,
        'kpis': kpis,
        'web_kpis': compute_sales_kpis(filters['date_from'], filters['date_to'], 'web'),
        'pos_kpis': compute_sales_kpis(filters['date_from'], filters['date_to'], 'pos'),
        'cash': cash,
        'banks': banks,
        'movements': movements,
        'tax': tax_snapshot(filters['date_from'], filters['date_to'], filters['channel']),
        'profit_steps': profitability_steps(kpis),
        'ranking': contribution_ranking(filters['date_from'], filters['date_to'], filters['channel']),
        'margin_pct': (
            (kpis.gross_margin / kpis.net_sales * Decimal('100')).quantize(Decimal('0.1'))
            if kpis.net_sales
            else None
        ),
    }
    return render(request, 'finance/balances.html', context)
