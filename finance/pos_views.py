from django.contrib import messages
from django.shortcuts import redirect, render

from finance.decorators import finance_manual_sale_required
from finance.forms import PosSaleForm
from finance.kpis import filters_from_request
from finance.page_context import filter_context, sales_querystring
from finance.pos_catalog import pos_catalog_payload, pos_catalog_qs
from finance.services.pos_sale import PosSaleError, create_pos_sale
from shop.models import Brand, Category, Product, ProductVariant

TICKET_KEY = 'finance_pos_ticket'


def _ticket(request) -> list:
    return list(request.session.get(TICKET_KEY) or [])


def _save_ticket(request, ticket: list) -> None:
    request.session[TICKET_KEY] = ticket
    request.session.modified = True


def _ticket_rows(ticket: list) -> list[dict]:
    rows = []
    for index, line in enumerate(ticket):
        product = Product.objects.filter(pk=line['product_id']).select_related('brand', 'category').prefetch_related('images').first()
        if not product:
            continue
        variant = None
        if line.get('variant_id'):
            variant = ProductVariant.objects.filter(pk=line['variant_id'], product=product).first()
        unit = int(product.current_price or 0)
        qty = int(line['quantity'])
        rows.append({
            'index': index,
            'product': product,
            'variant': variant,
            'quantity': qty,
            'unit_price': unit,
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


@finance_manual_sale_required
def pos_sale(request):
    filters = filters_from_request(request)
    form = PosSaleForm(request.POST if request.POST.get('action') == 'register' else None)
    q, category_id, brand_id = _search_params(request)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            _add_to_ticket(request)
            return redirect(_pos_url(request, q, category_id, brand_id))
        if action == 'remove':
            _remove_from_ticket(request)
            return redirect(_pos_url(request, q, category_id, brand_id))
        if action == 'clear':
            _save_ticket(request, [])
            return redirect(_pos_url(request, q, category_id, brand_id))
        if action == 'register' and form.is_valid():
            rows = _ticket(request)
            try:
                order = create_pos_sale(
                    processed_by=request.user,
                    payment_method=form.cleaned_data['payment_method'],
                    lines=rows,
                    customer_name=form.cleaned_data.get('customer_name') or '',
                    customer_phone=form.cleaned_data.get('customer_phone') or '',
                    discount_total=form.cleaned_data.get('discount_total') or 0,
                    shipping_cost=form.cleaned_data.get('shipping_cost') or 0,
                    shipping_method=form.cleaned_data.get('shipping_method'),
                    notes=form.cleaned_data.get('notes') or '',
                )
            except PosSaleError as exc:
                messages.error(request, str(exc))
            else:
                _save_ticket(request, [])
                first = order.items.order_by('id').first()
                messages.success(
                    request,
                    f'Venta física #{order.order_number or order.id} registrada. El precio de catálogo no cambió.',
                )
                if first:
                    return redirect('finance:sales_line_detail', item_id=first.pk)
                return redirect('finance:sales_lines')

    has_filter = bool(q or category_id or brand_id)
    matches = list(pos_catalog_qs(q, category_id, brand_id)[:40]) if has_filter else []
    all_active = Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('variants')
    ticket_rows = _ticket_rows(_ticket(request))
    context = {
        'finance_section': 'ingresos',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'form': form,
        'search_q': q,
        'search_category': category_id or '',
        'search_brand': brand_id or '',
        'categories': Category.objects.filter(is_active=True).order_by('name'),
        'brands': Brand.objects.filter(is_active=True).order_by('name'),
        'matches': matches,
        'has_filter': has_filter,
        'ticket_rows': ticket_rows,
        'ticket_total': sum(row['line_total'] for row in ticket_rows),
        'pos_catalog': pos_catalog_payload(all_active),
    }
    return render(request, 'finance/pos_sale.html', context)


def _pos_url(request, q, category_id, brand_id):
    from django.urls import reverse
    from urllib.parse import urlencode

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
    return f"{reverse('finance:pos_sale')}?{urlencode(params)}"


def _add_to_ticket(request):
    product_id = request.POST.get('product_id')
    variant_id = request.POST.get('variant_id') or None
    try:
        quantity = int(request.POST.get('quantity') or '1')
    except ValueError:
        quantity = 0
    if not str(product_id).isdigit() or quantity < 1:
        messages.error(request, 'Elige un producto y una cantidad válida.')
        return
    product = Product.objects.filter(pk=int(product_id), is_active=True).first()
    if not product:
        messages.error(request, 'Ese producto no está disponible.')
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
            _save_ticket(request, ticket)
            messages.success(request, f'{product.name} agregado a la venta.')
            return
    ticket.append({'product_id': product.id, 'variant_id': variant_pk, 'quantity': quantity})
    _save_ticket(request, ticket)
    messages.success(request, f'{product.name} agregado a la venta.')


def _remove_from_ticket(request):
    try:
        index = int(request.POST.get('index'))
    except (TypeError, ValueError):
        return
    ticket = _ticket(request)
    if 0 <= index < len(ticket):
        ticket.pop(index)
        _save_ticket(request, ticket)
