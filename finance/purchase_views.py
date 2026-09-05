from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from finance.access import FINANCE_PURCHASES_PERM, user_has_finance_perm
from finance.decorators import finance_view_required
from finance.forms import PurchaseForm
from finance.kpis import filters_from_request
from finance.models import MerchandisePurchase
from finance.page_context import filter_context, sales_querystring
from finance.pos_catalog import default_unit_cost_gross, pos_catalog_payload, pos_catalog_qs
from finance.services.purchase import PurchaseError, register_purchase
from shop.models import Brand, Category, Product, ProductVariant

TICKET_KEY = 'finance_purchase_ticket'


def _ticket(request) -> list:
    return list(request.session.get(TICKET_KEY) or [])


def _save_ticket(request, ticket: list) -> None:
    request.session[TICKET_KEY] = ticket
    request.session.modified = True


def _ticket_rows(ticket: list) -> list[dict]:
    rows = []
    for index, line in enumerate(ticket):
        product = Product.objects.filter(pk=line['product_id']).select_related('brand', 'category').first()
        if not product:
            continue
        variant = None
        if line.get('variant_id'):
            variant = ProductVariant.objects.filter(pk=line['variant_id'], product=product).first()
        unit = int(line.get('unit_cost_gross') or 0)
        qty = int(line['quantity'])
        rows.append({
            'index': index,
            'product': product,
            'variant': variant,
            'quantity': qty,
            'unit_cost_gross': unit,
            'line_total': unit * qty,
        })
    return rows


def _search_params(request):
    q = (request.POST.get('q') or request.GET.get('q') or '').strip()
    category = request.POST.get('category') or request.GET.get('category') or ''
    brand = request.POST.get('brand') or request.GET.get('brand') or ''
    category_id = int(category) if str(category).isdigit() else None
    brand_id = int(brand) if str(brand).isdigit() else None
    return q, category_id, brand_id


@finance_view_required
def purchases(request):
    filters = filters_from_request(request)
    can_manage = user_has_finance_perm(request.user, FINANCE_PURCHASES_PERM)
    form = PurchaseForm(request.POST if request.POST.get('action') == 'register' else None)
    if not form.is_bound:
        form.initial['occurred_on'] = timezone.localdate()
        form.initial['updates_stock'] = True
        form.initial['updates_catalog_cost'] = True
        form.initial['is_vat_affected'] = True
    q, category_id, brand_id = _search_params(request)

    if request.method == 'POST':
        if not can_manage:
            messages.error(request, 'No tienes permiso para registrar compras.')
            return redirect('finance:purchases')
        action = request.POST.get('action')
        if action == 'add':
            _add_to_ticket(request)
            return redirect(_purchases_url(request, q, category_id, brand_id))
        if action == 'remove':
            _remove_from_ticket(request)
            return redirect(_purchases_url(request, q, category_id, brand_id))
        if action == 'clear':
            _save_ticket(request, [])
            return redirect(_purchases_url(request, q, category_id, brand_id))
        if action == 'register' and form.is_valid():
            rows = _ticket(request)
            try:
                purchase = register_purchase(
                    account=form.cleaned_data['account'],
                    supplier=form.cleaned_data['supplier'],
                    lines=rows,
                    occurred_on=form.cleaned_data['occurred_on'],
                    updates_stock=form.cleaned_data.get('updates_stock', False),
                    updates_catalog_cost=form.cleaned_data.get('updates_catalog_cost', False),
                    is_vat_affected=form.cleaned_data.get('is_vat_affected', False),
                    notes=form.cleaned_data.get('notes') or '',
                    user=request.user,
                )
            except PurchaseError as exc:
                messages.error(request, str(exc))
            else:
                _save_ticket(request, [])
                messages.success(
                    request,
                    f'Compra a {purchase.supplier} registrada. No es venta ni gasto operativo.',
                )
                return redirect('finance:purchases')

    has_filter = bool(q or category_id or brand_id)
    matches = list(pos_catalog_qs(q, category_id, brand_id, active_only=False)[:40]) if has_filter else []
    for product in matches:
        product.purchase_unit_cost = default_unit_cost_gross(product)
    catalog = Product.objects.select_related('category', 'brand').prefetch_related('variants').order_by('name', 'id')
    ticket_rows = _ticket_rows(_ticket(request))
    context = {
        'finance_section': 'inventario',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'form': form,
        'search_q': q,
        'search_category': category_id or '',
        'search_brand': brand_id or '',
        'categories': Category.objects.order_by('name'),
        'brands': Brand.objects.order_by('name'),
        'matches': matches,
        'has_filter': has_filter,
        'ticket_rows': ticket_rows,
        'ticket_total': sum(row['line_total'] for row in ticket_rows),
        'pos_catalog': pos_catalog_payload(catalog),
        'can_manage_purchases': can_manage,
        'purchases': (
            MerchandisePurchase.objects.select_related('account')
            .prefetch_related('lines')
            .order_by('-occurred_on', '-id')[:40]
        ),
    }
    return render(request, 'finance/purchases.html', context)


def _purchases_url(request, q, category_id, brand_id):
    params = {}
    filters = filters_from_request(request)
    params['date_from'] = filters['date_from'].isoformat()
    params['date_to'] = filters['date_to'].isoformat()
    if q:
        params['q'] = q
    if category_id:
        params['category'] = str(category_id)
    if brand_id:
        params['brand'] = str(brand_id)
    return f"{reverse('finance:purchases')}?{urlencode(params)}"


def _add_to_ticket(request):
    product_id = request.POST.get('product_id')
    variant_id = request.POST.get('variant_id') or None
    try:
        quantity = int(request.POST.get('quantity') or '1')
        unit_cost = int(request.POST.get('unit_cost_gross') or '0')
    except ValueError:
        quantity = 0
        unit_cost = 0
    if not str(product_id).isdigit() or quantity < 1:
        messages.error(request, 'Elige un producto y una cantidad válida.')
        return
    product = Product.objects.filter(pk=int(product_id)).first()
    if not product:
        messages.error(request, 'Ese producto ya no existe.')
        return
    if unit_cost < 1:
        unit_cost = default_unit_cost_gross(product)
    if unit_cost < 1:
        messages.error(request, 'Indica el costo unitario bruto.')
        return
    variant_pk = int(variant_id) if str(variant_id or '').isdigit() else None
    if product.variants.exists() and not variant_pk:
        messages.error(request, f'{product.name} requiere talla/color.')
        return
    if variant_pk:
        variant = ProductVariant.objects.filter(pk=variant_pk, product=product).first()
        if not variant:
            messages.error(request, 'La opción no corresponde al producto.')
            return
    ticket = _ticket(request)
    for line in ticket:
        same_product = line['product_id'] == product.id
        same_variant = (line.get('variant_id') or None) == variant_pk
        if same_product and same_variant:
            line['quantity'] = int(line['quantity']) + quantity
            line['unit_cost_gross'] = unit_cost
            _save_ticket(request, ticket)
            messages.success(request, f'{product.name} agregado a la compra.')
            return
    ticket.append({
        'product_id': product.id,
        'variant_id': variant_pk,
        'quantity': quantity,
        'unit_cost_gross': unit_cost,
    })
    _save_ticket(request, ticket)
    messages.success(request, f'{product.name} agregado a la compra.')


def _remove_from_ticket(request):
    try:
        index = int(request.POST.get('index'))
    except (TypeError, ValueError):
        return
    ticket = _ticket(request)
    if 0 <= index < len(ticket):
        ticket.pop(index)
        _save_ticket(request, ticket)
