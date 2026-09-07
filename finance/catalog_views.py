from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from finance.decorators import finance_catalog_required, finance_view_required
from finance.forms import CatalogProductForm, ImageFormSet, SimpleStockForm, VariantFormSet
from finance.inventory import catalog_potential_totals, product_potential
from finance.kpis import filters_from_request
from finance.page_context import filter_context, sales_querystring
from shop.models import Product


def _inventory_querystring(filters, extra: dict) -> str:
    data = {
        'date_from': filters['date_from'].isoformat(),
        'date_to': filters['date_to'].isoformat(),
    }
    if filters['channel']:
        data['channel'] = filters['channel']
    if filters['account_id']:
        data['account'] = str(filters['account_id'])
    for key in ('q', 'status', 'stock', 'cost'):
        if extra.get(key):
            data[key] = extra[key]
    return urlencode(data)


def _safe_inventory_next(request) -> str:
    nxt = request.POST.get('next') or request.GET.get('next') or ''
    if nxt.startswith('/dashboard/finanzas/inventario'):
        return nxt
    return reverse('finance:inventory')


def _catalog_qs(request):
    qs = Product.objects.select_related('category', 'brand').prefetch_related('variants', 'images')
    search = (request.GET.get('q') or '').strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(sku__icontains=search))
    status = request.GET.get('status') or ''
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    stock = request.GET.get('stock') or ''
    if stock == 'in':
        qs = qs.filter(stock__gt=0)
    elif stock == 'out':
        qs = qs.filter(stock=0)
    cost = request.GET.get('cost') or ''
    if cost == 'missing':
        qs = qs.filter(cost_net=0, stock__gt=0)
    return qs.order_by('name', 'id'), {
        'q': search,
        'status': status,
        'stock': stock,
        'cost': cost,
    }


@finance_view_required
def inventory(request):
    filters = filters_from_request(request)
    qs, extra = _catalog_qs(request)
    matching = list(qs)
    totals = catalog_potential_totals(matching)
    paginator = Paginator(matching, 25)
    page = paginator.get_page(request.GET.get('page') or 1)
    rows = [{'product': product, 'potential': product_potential(product)} for product in page.object_list]
    context = {
        'finance_section': 'inventario',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'inventory_query': _inventory_querystring(filters, extra),
        'search': extra['q'],
        'status_filter': extra['status'],
        'stock_filter': extra['stock'],
        'cost_filter': extra['cost'],
        'page': page,
        'rows': rows,
        'totals': totals,
    }
    return render(request, 'finance/inventory.html', context)


@finance_catalog_required
def inventory_stock(request, product_id: int):
    if request.method != 'POST':
        return redirect(_safe_inventory_next(request))
    form = SimpleStockForm(request.POST)
    nxt = _safe_inventory_next(request)
    if not form.is_valid():
        messages.error(request, 'El stock debe ser un número entero mayor o igual a 0.')
        return redirect(nxt)
    with transaction.atomic():
        product = get_object_or_404(Product.objects.select_for_update(), pk=product_id)
        if product.variants.exists():
            messages.error(request, 'Este producto usa variantes: edita el stock por opción.')
            return redirect(nxt)
        product.stock = form.cleaned_data['stock']
        product.save(update_fields=['stock', 'updated_at'])
    messages.success(request, f'Stock de {product.name} actualizado a {product.stock}.')
    return redirect(nxt)


def _product_formsets(request, product):
    instance = product if product is not None else Product()
    if request.method == 'POST':
        variant_formset = VariantFormSet(request.POST, instance=instance, prefix='variants')
        image_formset = ImageFormSet(request.POST, request.FILES, instance=instance, prefix='images')
    else:
        variant_formset = VariantFormSet(instance=instance, prefix='variants')
        image_formset = ImageFormSet(instance=instance, prefix='images')
    return variant_formset, image_formset


@finance_catalog_required
def product_create(request):
    return _product_editor(request, product=None)


@finance_catalog_required
def product_edit(request, product_id: int):
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand').prefetch_related('variants', 'images'),
        pk=product_id,
    )
    return _product_editor(request, product=product)


def _product_editor(request, product):
    filters = filters_from_request(request)
    form = CatalogProductForm(request.POST or None, instance=product)
    variant_formset, image_formset = _product_formsets(request, product)
    if request.method == 'POST' and form.is_valid() and variant_formset.is_valid() and image_formset.is_valid():
        with transaction.atomic():
            saved = form.save()
            variant_formset.instance = saved
            image_formset.instance = saved
            variant_formset.save()
            image_formset.save()
        messages.success(request, f'{saved.name} guardado. El precio publicado rige el potencial, no crea una venta.')
        return redirect('finance:product_edit', product_id=saved.pk)
    context = {
        'finance_section': 'inventario',
        'filters': filters,
        **filter_context(request, filters),
        'sales_query': sales_querystring(filters),
        'form': form,
        'variant_formset': variant_formset,
        'image_formset': image_formset,
        'product': product,
        'is_create': product is None,
        'potential': product_potential(product) if product else None,
    }
    return render(request, 'finance/product_form.html', context)
