from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, render

from finance.decorators import finance_view_required
from finance.kpis import (
    compute_sales_kpis,
    contribution_ranking,
    filters_from_request,
    finance_alerts,
    format_delta,
    percent_delta,
    previous_period,
    sales_lines_qs,
    treasury_snapshot,
)
from finance.models import FinancialAccount
from shop.models import OrderItem


def _filter_context(filters: dict) -> dict:
    return {
        'date_from': filters['date_from'].isoformat(),
        'date_to': filters['date_to'].isoformat(),
        'channel': filters['channel'],
        'account_id': filters['account_id'] or '',
        'accounts': FinancialAccount.objects.filter(is_active=True).order_by('name'),
    }


def _sales_querystring(filters: dict) -> str:
    parts = [
        f"date_from={filters['date_from'].isoformat()}",
        f"date_to={filters['date_to'].isoformat()}",
    ]
    if filters['channel']:
        parts.append(f"channel={filters['channel']}")
    if filters['account_id']:
        parts.append(f"account={filters['account_id']}")
    return '&'.join(parts)


@finance_view_required
def resumen(request):
    filters = filters_from_request(request)
    current = compute_sales_kpis(filters['date_from'], filters['date_to'], filters['channel'])
    prev_from, prev_to = previous_period(filters['date_from'], filters['date_to'])
    previous = compute_sales_kpis(prev_from, prev_to, filters['channel'])
    treasury = treasury_snapshot(filters['date_from'], filters['date_to'], filters['account_id'])
    ranking = contribution_ranking(filters['date_from'], filters['date_to'], filters['channel'])
    query = _sales_querystring(filters)

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
        **_filter_context(filters),
        'sales_query': query,
        'operating': kpi_pack(current.operating_result, previous.operating_result),
        'net_sales': kpi_pack(current.net_sales, previous.net_sales),
        'contribution': kpi_pack(current.contribution, previous.contribution),
        'opex': kpi_pack(current.opex, previous.opex),
        'vat_debit': current.vat_debit,
        'treasury': treasury,
        'ranking': ranking,
        'alerts': finance_alerts(),
        'prev_from': prev_from,
        'prev_to': prev_to,
    }
    return render(request, 'finance/resumen.html', context)


@finance_view_required
def sales_lines(request):
    filters = filters_from_request(request)
    qs = (
        sales_lines_qs(filters['date_from'], filters['date_to'], filters['channel'])
        .select_related('order', 'order__payment_method', 'product')
        .annotate(gross_margin_amount=F('net_sale') - F('line_cost_net'))
        .order_by('-order__created_at', '-id')
    )
    search = (request.GET.get('q') or '').strip()
    if search:
        qs = qs.filter(
            Q(product_name__icontains=search)
            | Q(sku_snapshot__icontains=search)
            | Q(order__order_number__icontains=search)
        )
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page') or 1)
    context = {
        'finance_section': 'ingresos',
        'filters': filters,
        **_filter_context(filters),
        'sales_query': _sales_querystring(filters),
        'page': page,
        'search': search,
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
        **_filter_context(filters),
        'sales_query': _sales_querystring(filters),
        'item': item,
        'order': item.order,
    }
    return render(request, 'finance/sales_line_detail.html', context)


@finance_view_required
def coming_soon(request, section: str):
    titles = {
        'financing': 'Financiamiento',
        'expenses': 'Gastos',
        'balances': 'Saldos',
        'inventory': 'Inventario',
    }
    nav = {
        'financing': 'ingresos',
        'expenses': 'gastos',
        'balances': 'saldos',
        'inventory': 'inventario',
    }
    filters = filters_from_request(request)
    context = {
        'finance_section': nav.get(section, 'resumen'),
        'filters': filters,
        **_filter_context(filters),
        'sales_query': _sales_querystring(filters),
        'page_heading': titles.get(section, 'Finanzas'),
        'section_key': section,
    }
    return render(request, 'finance/coming_soon.html', context)
