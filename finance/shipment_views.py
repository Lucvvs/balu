from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from finance.access import FINANCE_EXPENSE_PERM, user_has_finance_perm
from finance.decorators import finance_view_required
from finance.forms import ShipmentForm
from finance.kpis import filters_from_request
from finance.models import OrderShipment
from finance.page_context import filter_context, sales_querystring
from finance.services.shipment import ShipmentError, upsert_shipment
from shop.models import Order


@finance_view_required
def shipments(request):
    filters = filters_from_request(request)
    can_register = user_has_finance_perm(request.user, FINANCE_EXPENSE_PERM)
    form = ShipmentForm(request.POST if request.method == 'POST' else None)
    if not form.is_bound:
        form.initial['occurred_on'] = timezone.localdate()

    if request.method == 'POST':
        if not can_register:
            messages.error(request, 'No tienes permiso para registrar envíos.')
            return redirect('finance:shipments')
        if form.is_valid():
            number = form.cleaned_data['order_number'].strip()
            order = (
                Order.objects.filter(order_number=number).first()
                or (Order.objects.filter(pk=int(number)).first() if number.isdigit() else None)
            )
            if not order:
                messages.error(request, 'No existe un pedido con ese número.')
            else:
                try:
                    actual = form.cleaned_data['actual_cost']
                    assumed = form.cleaned_data.get('assumed_cost')
                    shipment = upsert_shipment(
                        order=order,
                        actual_cost=actual,
                        assumed_cost=assumed if assumed is not None else actual,
                        account=form.cleaned_data.get('account'),
                        carrier=form.cleaned_data.get('carrier') or '',
                        tracking_code=form.cleaned_data.get('tracking_code') or '',
                        occurred_on=form.cleaned_data['occurred_on'],
                        notes=form.cleaned_data.get('notes') or '',
                        user=request.user,
                    )
                except ShipmentError as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(
                        request,
                        f'Envío del pedido #{order.order_number or order.pk} registrado. Una sola transacción de origen.',
                    )
                    return redirect('finance:shipments')

    rows = (
        OrderShipment.objects.filter(
            occurred_on__gte=filters['date_from'],
            occurred_on__lte=filters['date_to'],
        )
        .select_related('order', 'account')
        .order_by('-occurred_on', '-id')
    )
    context = {
        'finance_section': 'gastos',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'form': form,
        'rows': rows,
        'can_register_expense': can_register,
    }
    return render(request, 'finance/shipments.html', context)
