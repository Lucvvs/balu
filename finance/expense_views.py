from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from finance.access import FINANCE_EXPENSE_PERM, user_has_finance_perm
from finance.decorators import finance_view_required
from finance.forms import ExpenseCategoryForm, ExpenseForm
from finance.kpis import compute_sales_kpis, filters_from_request
from finance.models import ExpenseCategory, OperationalExpense
from finance.money import to_decimal
from finance.page_context import filter_context, sales_querystring
from finance.services.expense import ExpenseError, create_expense_category, register_expense


@finance_view_required
def expenses(request):
    filters = filters_from_request(request)
    can_register = user_has_finance_perm(request.user, FINANCE_EXPENSE_PERM)
    form = ExpenseForm(request.POST if request.POST.get('action') == 'create' else None)
    category_form = ExpenseCategoryForm(request.POST if request.POST.get('action') == 'add_category' else None)
    if not form.is_bound:
        form.initial['occurred_on'] = timezone.localdate()
        form.initial['is_vat_affected'] = True
    if not category_form.is_bound:
        category_form.initial['kind'] = ExpenseCategory.Kind.OTHER

    if request.method == 'POST':
        if not can_register:
            messages.error(request, 'No tienes permiso para registrar gastos.')
            return redirect('finance:expenses')
        action = request.POST.get('action')
        try:
            if action == 'create' and form.is_valid():
                item = register_expense(
                    category=form.cleaned_data['category'],
                    account=form.cleaned_data['account'],
                    vendor=form.cleaned_data['vendor'],
                    description=form.cleaned_data['description'],
                    amount=form.cleaned_data['amount'],
                    occurred_on=form.cleaned_data['occurred_on'],
                    is_vat_affected=form.cleaned_data.get('is_vat_affected', False),
                    notes=form.cleaned_data.get('notes') or '',
                    user=request.user,
                )
                messages.success(
                    request,
                    f'Gasto “{item.description}” registrado. Baja tesorería y suma opex; no es compra ni venta.',
                )
                return redirect('finance:expenses')
            if action == 'add_category' and category_form.is_valid():
                created = create_expense_category(
                    name=category_form.cleaned_data['name'],
                    kind=category_form.cleaned_data['kind'],
                    user=request.user,
                )
                messages.success(request, f'Categoría “{created.name}” creada.')
                return redirect('finance:expenses')
        except ExpenseError as exc:
            messages.error(request, str(exc))

    qs = (
        OperationalExpense.objects.filter(
            occurred_on__gte=filters['date_from'],
            occurred_on__lte=filters['date_to'],
        )
        .select_related('category', 'account')
        .order_by('-occurred_on', '-id')
    )
    if filters['account_id']:
        qs = qs.filter(account_id=filters['account_id'])
    kpis = compute_sales_kpis(filters['date_from'], filters['date_to'], filters['channel'])
    kind_totals = []
    for kind, label in ExpenseCategory.Kind.choices:
        total = to_decimal(
            qs.filter(category__kind=kind).aggregate(total=Sum('net_amount'))['total']
        )
        kind_totals.append({'kind': kind, 'label': label, 'net': total})
    context = {
        'finance_section': 'gastos',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'form': form,
        'category_form': category_form,
        'rows': qs,
        'kpis': kpis,
        'kind_totals': kind_totals,
        'can_register_expense': can_register,
        'vat_credit_total': to_decimal(qs.aggregate(total=Sum('vat_credit'))['total']),
        'gross_total': to_decimal(qs.aggregate(total=Sum('gross_amount'))['total']),
        'list_net': to_decimal(qs.aggregate(total=Sum('net_amount'))['total']),
    }
    return render(request, 'finance/expenses.html', context)
