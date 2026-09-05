from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from finance.access import FINANCE_FINANCING_PERM, user_has_finance_perm
from finance.decorators import finance_view_required
from finance.forms import FinancingForm, LoanRepayForm
from finance.kpis import filters_from_request
from finance.models import Financing
from finance.page_context import filter_context, sales_querystring
from finance.services.financing import FinancingError, register_contribution, register_loan, repay_loan


@finance_view_required
def financing(request):
    filters = filters_from_request(request)
    can_manage = user_has_finance_perm(request.user, FINANCE_FINANCING_PERM)
    form = FinancingForm(request.POST if request.POST.get('action') == 'create' else None)
    repay_form = LoanRepayForm(request.POST if request.POST.get('action') == 'repay' else None)
    if not form.is_bound:
        form.initial['occurred_on'] = timezone.localdate()
        form.initial['kind'] = Financing.Kind.CONTRIBUTION
    if not repay_form.is_bound:
        repay_form.initial['occurred_on'] = timezone.localdate()

    if request.method == 'POST':
        if not can_manage:
            messages.error(request, 'No tienes permiso para gestionar financiamiento.')
            return redirect('finance:financing')
        action = request.POST.get('action')
        try:
            if action == 'create' and form.is_valid():
                kind = form.cleaned_data['kind']
                kwargs = dict(
                    account=form.cleaned_data['account'],
                    amount=form.cleaned_data['amount'],
                    occurred_on=form.cleaned_data['occurred_on'],
                    counterparty=form.cleaned_data['counterparty'],
                    notes=form.cleaned_data.get('notes') or '',
                    user=request.user,
                )
                if kind == Financing.Kind.LOAN:
                    item = register_loan(**kwargs)
                    messages.success(request, f'Préstamo de {item.counterparty} registrado. No es una venta.')
                else:
                    item = register_contribution(**kwargs)
                    messages.success(request, f'Aporte de {item.counterparty} registrado. No es una venta.')
                return redirect('finance:financing')
            if action == 'repay' and repay_form.is_valid():
                repay_loan(
                    financing=repay_form.cleaned_data['financing'],
                    account=repay_form.cleaned_data['account'],
                    amount=repay_form.cleaned_data['amount'],
                    occurred_on=repay_form.cleaned_data['occurred_on'],
                    notes=repay_form.cleaned_data.get('notes') or '',
                    user=request.user,
                )
                messages.success(request, 'Pago de préstamo registrado. Bajó la caja y el saldo pendiente.')
                return redirect('finance:financing')
        except FinancingError as exc:
            messages.error(request, str(exc))

    rows = []
    for item in Financing.objects.select_related('account').order_by('-occurred_on', '-id'):
        rows.append({
            'item': item,
            'outstanding': item.outstanding(),
        })
    context = {
        'finance_section': 'ingresos',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'form': form,
        'repay_form': repay_form,
        'rows': rows,
        'can_manage_financing': can_manage,
        'open_loans': any(row['outstanding'] for row in rows),
    }
    return render(request, 'finance/financing.html', context)
