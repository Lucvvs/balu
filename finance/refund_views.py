from datetime import date

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from finance.access import FINANCE_MANUAL_SALE_PERM, user_has_finance_perm
from finance.decorators import finance_view_required
from finance.forms import RefundLookupForm
from finance.kpis import filters_from_request
from finance.models import FinancialAccount, OrderRefund
from finance.page_context import filter_context, sales_querystring
from finance.services.refund import RefundError, qty_already_refunded, record_refund
from shop.models import Order


def _find_order(number: str):
    number = (number or '').strip()
    if not number:
        return None
    order = Order.objects.filter(order_number=number).first()
    if order:
        return order
    if number.isdigit():
        return Order.objects.filter(pk=int(number)).first()
    return None


@finance_view_required
def refunds(request):
    filters = filters_from_request(request)
    can_register = user_has_finance_perm(request.user, FINANCE_MANUAL_SALE_PERM)
    lookup = RefundLookupForm(
        request.POST if request.POST.get('action') == 'lookup'
        else (request.GET if request.GET.get('order_number') else None)
    )
    target = None
    line_rows = []
    order_number = (request.POST.get('order_number') or request.GET.get('order_number') or '').strip()
    if order_number:
        target = _find_order(order_number)
        if target:
            for item in target.items.order_by('id'):
                refunded = qty_already_refunded(item)
                line_rows.append({
                    'item': item,
                    'refunded': refunded,
                    'remaining': max(item.quantity - refunded, 0),
                })

    if request.method == 'POST' and request.POST.get('action') == 'refund':
        if not can_register:
            messages.error(request, 'No tienes permiso para registrar devoluciones.')
            return redirect('finance:refunds')
        target = _find_order(request.POST.get('order_number') or '')
        if not target:
            messages.error(request, 'No existe un pedido con ese número.')
        else:
            lines = []
            for item in target.items.all():
                raw = request.POST.get(f'qty_{item.pk}') or '0'
                try:
                    qty = int(raw)
                except ValueError:
                    qty = 0
                if qty > 0:
                    lines.append({'order_item_id': item.pk, 'quantity': qty})
            account_id = request.POST.get('account') or ''
            account = None
            if str(account_id).isdigit():
                account = FinancialAccount.objects.filter(pk=int(account_id), is_active=True).first()
            raw_date = (request.POST.get('occurred_on') or '').strip()
            try:
                occurred = date.fromisoformat(raw_date) if raw_date else timezone.localdate()
            except ValueError:
                occurred = timezone.localdate()
            try:
                refund = record_refund(
                    order=target,
                    lines=lines,
                    occurred_on=occurred,
                    account=account,
                    restores_stock=bool(request.POST.get('restores_stock')),
                    notes=request.POST.get('notes') or '',
                    user=request.user,
                )
            except RefundError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request,
                    f'Devolución de {refund.gross_amount} registrada. La venta original no se borró.',
                )
                return redirect('finance:refunds')

    rows = (
        OrderRefund.objects.filter(
            occurred_on__gte=filters['date_from'],
            occurred_on__lte=filters['date_to'],
        )
        .select_related('order', 'account')
        .prefetch_related('items__order_item')
        .order_by('-occurred_on', '-id')
    )
    context = {
        'finance_section': 'ingresos',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'lookup': lookup,
        'target': target,
        'line_rows': line_rows,
        'order_number': order_number,
        'rows': rows,
        'can_add_manual_sale': can_register,
        'accounts': FinancialAccount.objects.filter(is_active=True).order_by('name'),
        'today': timezone.localdate().isoformat(),
    }
    return render(request, 'finance/refunds.html', context)
