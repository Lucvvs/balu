from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from collections import defaultdict, deque

from django.db.models import Q, Prefetch, F, Case, When, IntegerField, Exists, OuterRef, Value
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse, HttpResponse, HttpRequest, Http404
from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json
from urllib.parse import urlparse

from .models import (
    Product, ProductVariant, Category, Brand, ProductImage, Cart, CartItem, Order, OrderItem,
    Coupon, ShippingMethod, ShippingRule, PaymentMethod, Payment, ContactMessage, MetricEvent, PromotionalBanner,
    HomePromoModal, resolve_cart_shipping_cost, is_cash_payment_method,
)
from .utils import (
    get_comunas_choices,
    get_regiones_choices,
    CHILE_METRO_REGION_NAME,
    SHIPPING_PRICE_METRO_REGION_DEFAULT,
    SHIPPING_PRICE_OTHER_REGIONS_DEFAULT,
)
from .forms import (
    UserRegistrationForm, AddToCartForm, UpdateCartItemForm, CouponForm,
    CheckoutForm, ContactForm, ProfileUpdateForm,
)
from .utils import send_order_confirmation_email, send_order_notification_to_admin
from .mercadopago_client import create_checkout_pro_preference, get_payment
from .email_preview import get_mock_order_email_context


def format_currency_clp(value):
    """Formatea un valor numérico como moneda chilena (CLP)"""
    if value is None:
        return '$0'
    try:
        amount = int(value)
        formatted = f"${amount:,}".replace(',', '.')
        return formatted
    except (ValueError, TypeError):
        return '$0'


def get_or_create_cart(request):
    """Helper para obtener o crear carrito basado en usuario o sesión"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        cart, created = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


def home(request):
    """Vista de la página principal"""
    # Productos en oferta (máximo 3, ordenados por offer_order)
    offers = Product.objects.filter(
        is_active=True,
        is_offer=True,
        stock__gt=0,
        offer_order__gt=0  # Solo productos con orden asignado
    ).select_related('category', 'brand').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id')),
        Prefetch(
            'variants',
            queryset=ProductVariant.objects.order_by('sort_order', 'name', 'id'),
        ),
    ).order_by('offer_order', '-created_at')[:3]

    # Productos más vendidos (máximo 3, ordenados por featured_order)
    best_sellers = Product.objects.filter(
        is_active=True,
        is_best_seller=True,
        stock__gt=0,
        featured_order__gt=0  # Solo productos con orden asignado
    ).select_related('category', 'brand').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id')),
        Prefetch(
            'variants',
            queryset=ProductVariant.objects.order_by('sort_order', 'name', 'id'),
        ),
    ).order_by('featured_order', '-created_at')[:3]

    # Categorías destacadas
    categories = Category.objects.filter(is_active=True, highlight_on_home=True)[:3]

    # Marcas para el banner (en orden específico: HRO, SHAFT, motocentric, 4RS, KOVIX, ICH, SHOT)
    brand_order = ['hro', 'shaft', 'motocentric', '4rs', 'kovix', 'ich', 'shot']
    brands_dict = {brand.slug: brand for brand in Brand.objects.filter(is_active=True)}
    brands = [brands_dict[slug] for slug in brand_order if slug in brands_dict]

    # Franjas promocionales (máximo 3, ordenadas por order)
    promotional_banners = PromotionalBanner.objects.filter(
        is_active=True
    ).order_by('order', 'created_at')[:3]

    home_promo_modal = HomePromoModal.get_solo()

    context = {
        'offers': offers,
        'best_sellers': best_sellers,
        'categories': categories,
        'brands': brands,
        'promotional_banners': promotional_banners,
        'home_promo_modal': home_promo_modal,
    }
    return render(request, 'shop/home.html', context)


def _annotate_catalog_stock_sort(queryset):
    """0 = con stock vendible, 1 = agotado (alinea con is_available_for_purchase)."""
    variant_in_stock = Exists(
        ProductVariant.objects.filter(product_id=OuterRef('pk'), stock__gt=0)
    )
    has_variants = Exists(ProductVariant.objects.filter(product_id=OuterRef('pk')))
    return queryset.annotate(
        _cat_has_variants=has_variants,
        _cat_variant_in_stock=variant_in_stock,
    ).annotate(
        catalog_stock_sort=Case(
            When(
                _cat_has_variants=True,
                then=Case(
                    When(_cat_variant_in_stock=True, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
            ),
            When(stock__gt=0, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
    )


def _round_robin_catalog_by_category(by_category):
    """
    by_category: {category_id: [product_id, ...]} ya ordenados dentro de la categoría.
    Devuelve IDs en round-robin según el orden alfabético de categorías activas.
    """
    if not by_category:
        return []
    category_order = list(
        Category.objects.filter(is_active=True).order_by('name').values_list('id', flat=True)
    )
    round_cats = [cid for cid in category_order if cid in by_category]
    extra = sorted(set(by_category.keys()) - set(round_cats))
    round_cats.extend(extra)
    deques = {cid: deque(by_category[cid]) for cid in by_category}
    result = []
    active = list(round_cats)
    while active:
        nxt = []
        for cid in active:
            dq = deques.get(cid)
            if dq:
                result.append(dq.popleft())
            if dq:
                nxt.append(cid)
        active = nxt
    return result


def _interleaved_catalog_product_ids(queryset):
    """
    Orden round-robin por categoría (mismo orden que Category: name).
    Primero todos los productos con stock (intercalados por categoría); luego todos los agotados,
    para que sin stock queden al final del catálogo. Dentro de cada bloque, por -created_at.
    """
    qs = queryset.order_by('category_id', 'catalog_stock_sort', '-created_at')
    by_in_stock = defaultdict(list)
    by_out_stock = defaultdict(list)
    for row in qs.values('id', 'category_id', 'catalog_stock_sort'):
        cid = row['category_id']
        if row['catalog_stock_sort'] == 0:
            by_in_stock[cid].append(row['id'])
        else:
            by_out_stock[cid].append(row['id'])

    return (
        _round_robin_catalog_by_category(by_in_stock)
        + _round_robin_catalog_by_category(by_out_stock)
    )


def products_list(request):
    """Vista de lista de productos con filtros"""
    products = Product.objects.filter(is_active=True).select_related(
        'category', 'brand'
    ).prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id')),
        Prefetch(
            'variants',
            queryset=ProductVariant.objects.order_by('sort_order', 'name', 'id'),
        ),
    ).order_by('-created_at')

    # Filtro por una sola categoría
    category_slug = request.GET.get('category')
    categories_param = request.GET.get('categories')  # Legado: se usa solo el primer slug

    selected_category_slug = None
    if category_slug:
        selected_category_slug = category_slug.strip()
    elif categories_param:
        parts = [s.strip() for s in categories_param.split(',') if s.strip()]
        if parts:
            selected_category_slug = parts[0]

    if selected_category_slug:
        products = products.filter(category__slug=selected_category_slug)

    # Filtro por marca (insensible a mayúsculas/minúsculas)
    brand_slug = request.GET.get('brand')
    if brand_slug:
        brand_slug = brand_slug.lower().strip()  # Normalizar a minúsculas
        products = products.filter(brand__slug__iexact=brand_slug)

    # Filtro por ofertas - solo productos que realmente tienen oferta válida
    if request.GET.get('offers') == 'true':
        products = products.filter(
            offer_price__isnull=False,
            offer_price__lt=F('price')
        )

    # Búsqueda
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        )

    # Ordenamiento y paginación
    sort_by = request.GET.get('sort', 'newest')
    page_number = request.GET.get('page')
    use_catalog_mix = (
        sort_by == 'newest'
        and not selected_category_slug
        and not search_query
    )

    if use_catalog_mix:
        mix_qs = _annotate_catalog_stock_sort(products)
        ordered_ids = _interleaved_catalog_product_ids(mix_qs)
        paginator = Paginator(ordered_ids, 12)
        page_obj = paginator.get_page(page_number)
        page_ids = list(page_obj.object_list)
        if page_ids:
            order_case = Case(
                *[When(pk=pk, then=pos) for pos, pk in enumerate(page_ids)],
                output_field=IntegerField(),
            )
            page_obj.object_list = list(
                Product.objects.filter(pk__in=page_ids)
                .select_related('category', 'brand')
                .prefetch_related(
                    Prefetch(
                        'images',
                        queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id'),
                    ),
                    Prefetch(
                        'variants',
                        queryset=ProductVariant.objects.order_by('sort_order', 'name', 'id'),
                    ),
                )
                .order_by(order_case)
            )
        else:
            page_obj.object_list = []
    else:
        # Mismo criterio que is_available_for_purchase: sin stock al final (tras el criterio de orden elegido).
        products = _annotate_catalog_stock_sort(products)
        if sort_by == 'price_asc':
            products = products.annotate(
                effective_price=Case(
                    When(offer_price__isnull=False, then=F('offer_price')),
                    default=F('price'),
                    output_field=IntegerField(),
                )
            ).order_by('catalog_stock_sort', 'effective_price', 'price')
        elif sort_by == 'price_desc':
            products = products.annotate(
                effective_price=Case(
                    When(offer_price__isnull=False, then=F('offer_price')),
                    default=F('price'),
                    output_field=IntegerField(),
                )
            ).order_by('catalog_stock_sort', '-effective_price', '-price')
        elif sort_by == 'name':
            products = products.order_by('catalog_stock_sort', 'name')
        else:
            products = products.order_by('catalog_stock_sort', '-created_at')

        paginator = Paginator(products, 12)
        page_obj = paginator.get_page(page_number)

    # Categorías para el filtro
    categories = Category.objects.filter(is_active=True)
    
    # Estado de filtro de ofertas
    current_offers = request.GET.get('offers') == 'true'
    
    current_categories = [selected_category_slug] if selected_category_slug else []

    context = {
        'products': page_obj,
        'categories': categories,
        'current_category': selected_category_slug,
        'current_categories': current_categories,
        'current_brand': brand_slug,
        'current_search': search_query,
        'current_sort': sort_by,
        'current_offers': current_offers,
    }
    return render(request, 'shop/products_list.html', context)


def product_detail(request, slug):
    """Vista de detalle de producto"""
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand').prefetch_related(
            Prefetch(
                'images',
                queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id'),
            ),
            'variants',
        ),
        slug=slug,
        is_active=True
    )

    # Productos relacionados (misma categoría, excluyendo el actual)
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).select_related('category', 'brand').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id'))
    )[:4]

    # Obtener imágenes del producto
    images = product.images.all()
    primary_image = images.filter(is_primary=True).first()
    if not primary_image and images.exists():
        primary_image = images.first()

    # Registrar vista de producto (evitar duplicados en la misma sesión)
    from datetime import timedelta
    recent_view = MetricEvent.objects.filter(
        event_type='product_view',
        session_key=request.session.session_key,
        metadata__product_id=product.id,
        created_at__gte=timezone.now() - timedelta(seconds=5)
    ).first()
    
    if not recent_view:
        MetricEvent.objects.create(
            event_type='product_view',
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            metadata={'product_id': product.id, 'product_slug': product.slug}
        )

    # Formulario con tallas si el producto las tiene
    form = AddToCartForm(product=product)
    
    context = {
        'product': product,
        'images': images,
        'primary_image': primary_image,
        'related_products': related_products,
        'form': form,
    }
    return render(request, 'shop/product_detail.html', context)


@require_POST
def add_to_cart(request, product_id):
    """Agregar producto al carrito"""
    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        messages.error(request, 'El producto no existe o no está disponible.')
        return redirect('shop:products_list')
    
    if not product.is_available_for_purchase():
        messages.error(request, f'Lo sentimos, {product.name} no tiene stock disponible en este momento.')
        return redirect('shop:product_detail', slug=product.slug)
    
    form = AddToCartForm(request.POST, product=product)
    if not form.is_valid():
        messages.error(request, 'Por favor completa todos los campos correctamente.')
        return redirect('shop:product_detail', slug=product.slug)

    quantity = form.cleaned_data['quantity']
    cart = get_or_create_cart(request)
    current_price = product.current_price

    if product.uses_variant_stock():
        variant = form.cleaned_data.get('variant')
        if not variant or variant.product_id != product.id:
            messages.error(request, 'Selecciona una opción válida (talla/color).')
            return redirect('shop:product_detail', slug=product.slug)
        if quantity > variant.stock:
            messages.error(
                request,
                f'No hay suficiente stock para {variant.name}. Disponible: {variant.stock}',
            )
            return redirect('shop:product_detail', slug=product.slug)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={
                'product': product,
                'quantity': quantity,
                'unit_price': current_price,
                'size': variant.name,
            },
        )

        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > variant.stock:
                messages.error(
                    request,
                    f'No hay suficiente stock para {variant.name}. Disponible: {variant.stock}',
                )
                return redirect('shop:product_detail', slug=product.slug)
            cart_item.quantity = new_quantity
            cart_item.save()

        size_meta = variant.name
    else:
        if quantity > product.stock:
            messages.error(request, f'No hay suficiente stock. Stock disponible: {product.stock}')
            return redirect('shop:product_detail', slug=product.slug)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=None,
            defaults={
                'quantity': quantity,
                'unit_price': current_price,
                'size': None,
            },
        )

        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock:
                messages.error(request, f'No hay suficiente stock. Stock disponible: {product.stock}')
                return redirect('shop:product_detail', slug=product.slug)
            cart_item.quantity = new_quantity
            cart_item.save()

        size_meta = None

    # Registrar evento
    MetricEvent.objects.create(
        event_type='add_to_cart',
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key,
        metadata={'product_id': product.id, 'quantity': quantity, 'size': size_meta},
    )

    size_text = f" — {size_meta}" if size_meta else ""
    messages.success(request, f'{product.name}{size_text} agregado al carrito.')
    return redirect('shop:cart')


def cart_view(request):
    """Vista del carrito de compras"""
    cart = None
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.prefetch_related(
                'items__product__images',
                'items__variant',
            ).get(user=request.user)
        except Cart.DoesNotExist:
            cart = None
    elif request.session.session_key:
        try:
            cart = Cart.objects.prefetch_related(
                'items__product__images',
                'items__variant',
            ).get(session_key=request.session.session_key)
        except Cart.DoesNotExist:
            cart = None

    # Obtener cupón aplicado y calcular descuento
    applied_coupon = None
    discount_amount = 0
    total_with_discount = 0
    
    if cart:
        subtotal = cart.get_subtotal()
        applied_coupon_id = request.session.get('applied_coupon_id')
        
        if applied_coupon_id:
            try:
                applied_coupon = Coupon.objects.get(id=applied_coupon_id)
                if applied_coupon.is_valid(subtotal):
                    discount_amount = applied_coupon.calculate_discount(subtotal)
                    total_with_discount = subtotal - discount_amount
                else:
                    # Cupón inválido, limpiar de sesión
                    del request.session['applied_coupon_id']
                    applied_coupon = None
            except Coupon.DoesNotExist:
                # Cupón no existe, limpiar de sesión
                if 'applied_coupon_id' in request.session:
                    del request.session['applied_coupon_id']
        
        if not applied_coupon:
            total_with_discount = subtotal

    domestic_shipping = ShippingMethod.objects.filter(is_active=True, base_price__gt=0).first()
    metro_price = SHIPPING_PRICE_METRO_REGION_DEFAULT
    other_price = SHIPPING_PRICE_OTHER_REGIONS_DEFAULT
    region_prices = {}
    shipping_price_min = other_price
    shipping_price_max = other_price
    has_special_shipping = False
    cart_products = []
    if cart:
        cart_products = [
            item.product
            for item in cart.items.select_related('product').prefetch_related('product__shipping_rates')
        ]
        has_special_shipping = any(p.uses_special_shipping for p in cart_products)

    if domestic_shipping:
        r_metro = ShippingRule.objects.filter(
            shipping_method=domestic_shipping, is_active=True, region=CHILE_METRO_REGION_NAME, comuna=''
        ).first()
        r_other = ShippingRule.objects.filter(
            shipping_method=domestic_shipping, is_active=True, region='', comuna=''
        ).first()
        if r_metro:
            metro_price = r_metro.price
        if r_other:
            other_price = r_other.price

        subtotal_for_rules = cart.get_subtotal() if cart else 0

        if has_special_shipping and cart_products:
            metro_price = resolve_cart_shipping_cost(
                cart_products, domestic_shipping, subtotal_for_rules, CHILE_METRO_REGION_NAME, ''
            )
            other_price = resolve_cart_shipping_cost(
                cart_products, domestic_shipping, subtotal_for_rules, '', ''
            )
            region_names = [name for name, _label in get_regiones_choices()]
            for rname in region_names:
                region_prices[rname] = resolve_cart_shipping_cost(
                    cart_products, domestic_shipping, subtotal_for_rules, rname, ''
                )
            if region_prices:
                shipping_price_min = min(region_prices.values())
                shipping_price_max = max(region_prices.values())
            else:
                shipping_price_min = min(metro_price, other_price)
                shipping_price_max = max(metro_price, other_price)
        else:
            distinct_regions = (
                ShippingRule.objects.filter(
                    shipping_method=domestic_shipping,
                    is_active=True,
                    comuna='',
                )
                .exclude(region='')
                .values_list('region', flat=True)
                .distinct()
            )
            for rname in distinct_regions:
                region_prices[rname] = domestic_shipping.resolve_price(subtotal_for_rules, rname, '')

            all_rule_prices = list(
                ShippingRule.objects.filter(
                    shipping_method=domestic_shipping,
                    is_active=True,
                ).values_list('price', flat=True)
            )
            if all_rule_prices:
                shipping_price_min = min(all_rule_prices)
                shipping_price_max = max(all_rule_prices)

    cash_payment = PaymentMethod.objects.filter(is_active=True, name__icontains='efectivo').first()

    context = {
        'cart': cart,
        'coupon_form': CouponForm(),
        'checkout_form': CheckoutForm(),
        'shipping_methods': ShippingMethod.objects.filter(is_active=True),
        'payment_methods': PaymentMethod.objects.filter(is_active=True),
        'applied_coupon': applied_coupon,
        'discount_amount': discount_amount,
        'total_with_discount': total_with_discount,
        'domestic_shipping_method_id': domestic_shipping.id if domestic_shipping else None,
        'shipping_metro_region_name': CHILE_METRO_REGION_NAME,
        'shipping_price_metro': metro_price,
        'shipping_price_other': other_price,
        'shipping_region_prices_json': json.dumps(region_prices, ensure_ascii=False),
        'shipping_price_min': shipping_price_min,
        'shipping_price_max': shipping_price_max,
        'has_special_shipping': has_special_shipping,
        'cash_payment_method_id': cash_payment.id if cash_payment else None,
    }
    return render(request, 'shop/cart.html', context)


@require_POST
def update_cart_item(request, item_id):
    """Actualizar cantidad de item en carrito"""
    cart_item = get_object_or_404(
        CartItem.objects.select_related('product', 'variant'),
        id=item_id,
    )
    
    # Verificar que el carrito pertenece al usuario/sesión
    cart = cart_item.cart
    if request.user.is_authenticated:
        if cart.user != request.user:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'No tienes permiso para modificar este carrito.'}, status=403)
            messages.error(request, 'No tienes permiso para modificar este carrito.')
            return redirect('shop:cart')
    else:
        if cart.session_key != request.session.session_key:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'No tienes permiso para modificar este carrito.'}, status=403)
            messages.error(request, 'No tienes permiso para modificar este carrito.')
            return redirect('shop:cart')

    form = UpdateCartItemForm(request.POST)
    if not form.is_valid():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Cantidad inválida.'}, status=400)
        messages.error(request, 'Cantidad inválida.')
        return redirect('shop:cart')

    quantity = form.cleaned_data['quantity']
    
    cap = cart_item.get_stock_cap()
    if quantity > cap:
        error_msg = f'No hay suficiente stock. Stock disponible: {cap}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('shop:cart')

    if quantity <= 0:
        cart_item.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'deleted': True, 'cart_subtotal': format_currency_clp(cart.get_subtotal())})
        messages.success(request, 'Item eliminado del carrito.')
    else:
        cart_item.quantity = quantity
        cart_item.save()
        # Si es petición AJAX, devolver JSON con los datos actualizados
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'item_total': format_currency_clp(cart_item.get_line_total()),
                'cart_subtotal': format_currency_clp(cart.get_subtotal())
            })
        messages.success(request, 'Carrito actualizado.')

    return redirect('shop:cart')


@require_POST
def remove_cart_item(request, item_id):
    """Eliminar item del carrito"""
    cart_item = get_object_or_404(
        CartItem.objects.select_related('product', 'variant'),
        id=item_id,
    )
    
    # Verificar que el carrito pertenece al usuario/sesión
    cart = cart_item.cart
    if request.user.is_authenticated:
        if cart.user != request.user:
            messages.error(request, 'No tienes permiso para modificar este carrito.')
            return redirect('shop:cart')
    else:
        if cart.session_key != request.session.session_key:
            messages.error(request, 'No tienes permiso para modificar este carrito.')
            return redirect('shop:cart')

    product_name = cart_item.product.name
    opt = cart_item.variant.name if cart_item.variant_id else cart_item.size
    size_text = f" — {opt}" if opt else ""
    cart_item.delete()
    messages.success(request, f'{product_name}{size_text} eliminado del carrito.')
    return redirect('shop:cart')


@require_POST
def clear_cart(request):
    """Limpiar todo el carrito"""
    cart = None
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            pass
    elif request.session.session_key:
        try:
            cart = Cart.objects.get(session_key=request.session.session_key)
        except Cart.DoesNotExist:
            pass

    if cart:
        cart.items.all().delete()
        messages.success(request, 'Carrito limpiado.')
    else:
        messages.info(request, 'El carrito ya está vacío.')

    return redirect('shop:cart')


@require_POST
def apply_coupon(request):
    """Aplicar cupón de descuento"""
    form = CouponForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Código de cupón inválido.')
        return redirect('shop:cart')

    code = form.cleaned_data['code']
    
    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        messages.error(request, 'Código de cupón no encontrado.')
        return redirect('shop:cart')

    cart = None
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            messages.error(request, 'Tu carrito está vacío.')
            return redirect('shop:cart')
    elif request.session.session_key:
        try:
            cart = Cart.objects.get(session_key=request.session.session_key)
        except Cart.DoesNotExist:
            messages.error(request, 'Tu carrito está vacío.')
            return redirect('shop:cart')

    if not cart:
        messages.error(request, 'Tu carrito está vacío.')
        return redirect('shop:cart')

    subtotal = cart.get_subtotal()
    
    if coupon.is_valid(subtotal):
        # Guardar cupón en sesión para usar en checkout
        request.session['applied_coupon_id'] = coupon.id
        discount = coupon.calculate_discount(subtotal)
        messages.success(request, f'Cupón "{code}" aplicado correctamente. Descuento: ${discount:,}'.replace(',', '.'))
    else:
        messages.error(request, 'El cupón no es válido o ha expirado.')
        if 'applied_coupon_id' in request.session:
            del request.session['applied_coupon_id']

    return redirect('shop:cart')


@require_POST
def remove_coupon(request):
    """Eliminar cupón aplicado"""
    if 'applied_coupon_id' in request.session:
        del request.session['applied_coupon_id']
        messages.info(request, 'Cupón eliminado.')
    return redirect('shop:cart')


@require_POST
@transaction.atomic
def checkout(request):
    """Procesar checkout y crear pedido"""
    cart = None
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.prefetch_related('items__product', 'items__variant').get(user=request.user)
        except Cart.DoesNotExist:
            messages.error(request, 'Tu carrito está vacío.')
            return redirect('shop:cart')
    elif request.session.session_key:
        try:
            cart = Cart.objects.prefetch_related('items__product', 'items__variant').get(session_key=request.session.session_key)
        except Cart.DoesNotExist:
            messages.error(request, 'Tu carrito está vacío.')
            return redirect('shop:cart')

    if not cart or cart.items.count() == 0:
        messages.error(request, 'Tu carrito está vacío.')
        return redirect('shop:cart')

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        # Mostrar errores específicos del formulario
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
        # Si hay errores de validación personalizados (clean method)
        if form.non_field_errors():
            for error in form.non_field_errors():
                messages.error(request, str(error))
        return redirect('shop:cart')

    # Obtener cupón si existe
    coupon = None
    coupon_id = request.session.get('applied_coupon_id')
    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id)
        except Coupon.DoesNotExist:
            pass

    # Calcular totales
    subtotal = cart.get_subtotal()
    shipping_method = form.cleaned_data['shipping_method']
    shipping_region = (form.cleaned_data.get('shipping_region') or '').strip()
    shipping_comuna = (form.cleaned_data.get('shipping_comuna') or '').strip()
    cart_products = [
        item.product
        for item in cart.items.select_related('product').prefetch_related('product__shipping_rates')
    ]
    shipping_cost = resolve_cart_shipping_cost(
        cart_products, shipping_method, subtotal, shipping_region, shipping_comuna
    )

    # Validación adicional para envío a domicilio
    if shipping_method.base_price > 0:
        shipping_address = form.cleaned_data.get('shipping_address', '').strip()
        payment_method_early = form.cleaned_data.get('payment_method')

        if not shipping_region:
            messages.error(request, '❌ Error: Debe seleccionar una región para envío a domicilio.')
            return redirect('shop:cart')
        if not shipping_comuna:
            messages.error(request, '❌ Error: Debe seleccionar una comuna para envío a domicilio.')
            return redirect('shop:cart')
        if not shipping_address:
            messages.error(request, '❌ Error: Debe ingresar la dirección para envío a domicilio.')
            return redirect('shop:cart')
        if is_cash_payment_method(payment_method_early):
            messages.error(
                request,
                '❌ Con envío a domicilio no se acepta pago en efectivo. '
                'El pedido se despacha una vez confirmado el pago.',
            )
            return redirect('shop:cart')

    # Reserva de stock atómica (evita carreras y asegura descuento también con Mercado Pago)
    cart_items = list(cart.items.select_related('product', 'variant').all())
    if not cart_items:
        messages.error(request, 'Tu carrito está vacío.')
        return redirect('shop:cart')

    product_ids = sorted({ci.product_id for ci in cart_items})
    locked_products = {
        p.id: p
        for p in Product.objects.select_for_update().filter(pk__in=product_ids)
    }
    if len(locked_products) != len(product_ids):
        messages.error(request, 'Uno o más productos ya no están disponibles.')
        return redirect('shop:cart')

    variant_ids = sorted({ci.variant_id for ci in cart_items if ci.variant_id})
    locked_variants = {
        v.id: v
        for v in ProductVariant.objects.select_for_update().filter(pk__in=variant_ids)
    }
    if len(locked_variants) != len(variant_ids):
        messages.error(request, 'Una o más variantes ya no están disponibles.')
        return redirect('shop:cart')

    for ci in cart_items:
        product = locked_products[ci.product_id]
        if ci.variant_id:
            variant = locked_variants[ci.variant_id]
            if variant.product_id != product.id:
                messages.error(request, 'Error de consistencia en el carrito. Vuelve a agregar el producto.')
                return redirect('shop:cart')
            if ci.quantity > variant.stock:
                messages.error(
                    request,
                    f'No hay suficiente stock para {product.name} ({variant.name}). Disponible: {variant.stock}',
                )
                return redirect('shop:cart')
        else:
            if product.uses_variant_stock():
                messages.error(
                    request,
                    f'El producto {product.name} requiere elegir talla/color. Actualiza el carrito.',
                )
                return redirect('shop:cart')
            if ci.quantity > product.stock:
                messages.error(
                    request,
                    f'No hay suficiente stock para {product.name}. Stock disponible: {product.stock}',
                )
                return redirect('shop:cart')

    # Aplicar descuento del cupón
    discount_total = 0
    if coupon and coupon.is_valid(subtotal):
        discount_total = coupon.calculate_discount(subtotal)
        coupon.uses_count += 1
        coupon.save()

    total = subtotal + shipping_cost - discount_total

    payment_method = form.cleaned_data['payment_method']
    # Determinar si el método elegido debe ir por Mercado Pago (tarjeta crédito/débito)
    pm_name = (payment_method.name or "").strip().lower()
    mp_base_name = (settings.MP_PAYMENT_METHOD_NAME or "mercado pago").strip().lower()

    # Normalización básica: quitar acentos y espacios extra
    def _norm(s: str) -> str:
        return (
            s.replace('á', 'a')
             .replace('é', 'e')
             .replace('í', 'i')
             .replace('ó', 'o')
             .replace('ú', 'u')
             .replace('ñ', 'n')
             .strip()
        )

    norm_name = _norm(pm_name)
    norm_mp_name = _norm(mp_base_name)

    # Considerar varias formas comunes de nombrar tarjetas
    is_card_mp = (
        'tarjeta' in norm_name
        and ('credito' in norm_name or 'debito' in norm_name)
    )

    is_mp = norm_name == norm_mp_name or is_card_mp

    # Crear pedido
    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        shipping_method=shipping_method,
        shipping_region=form.cleaned_data.get('shipping_region'),
        shipping_comuna=form.cleaned_data.get('shipping_comuna'),
        shipping_address=form.cleaned_data.get('shipping_address'),
        shipping_notes=form.cleaned_data.get('shipping_notes'),
        shipping_cost=shipping_cost,
        payment_method=payment_method,
        coupon=coupon,
        subtotal=subtotal,
        discount_total=discount_total,
        total=total,
        customer_name=form.cleaned_data.get('customer_name') or (request.user.get_full_name() if request.user.is_authenticated else None),
        # Nunca permitir que el email del usuario autenticado sea cambiado desde el navegador.
        customer_email=(request.user.email if request.user.is_authenticated else form.cleaned_data.get('customer_email')),
        customer_phone=form.cleaned_data.get('customer_phone'),
        status='pending_payment' if is_mp else 'realized',
    )

    # Crear items del pedido y descontar stock (transferencia y MP: reserva al crear el pedido)
    for cart_item in cart_items:
        product = locked_products[cart_item.product_id]
        if cart_item.variant_id:
            variant = locked_variants[cart_item.variant_id]
            snapshot_name = f'{product.name} — {variant.name}'
            variant.stock -= cart_item.quantity
            variant.save(update_fields=['stock'])
            ProductVariant.sync_parent_product_stock(product.id)
            OrderItem.objects.create(
                order=order,
                product=product,
                product_variant=variant,
                product_name=snapshot_name,
                variant_label=variant.name,
                unit_price=cart_item.unit_price,
                quantity=cart_item.quantity,
                line_total=cart_item.get_line_total(),
            )
        else:
            product.stock -= cart_item.quantity
            product.save(update_fields=['stock'])
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                variant_label='',
                unit_price=cart_item.unit_price,
                quantity=cart_item.quantity,
                line_total=cart_item.get_line_total(),
            )
    order.stock_committed = True
    order.save(update_fields=['stock_committed'])

    # Limpiar carrito
    cart.items.all().delete()
    
    # Limpiar cupón de sesión
    if 'applied_coupon_id' in request.session:
        del request.session['applied_coupon_id']

    # Crear registro de pago
    payment_type = 'mercado_pago' if is_mp else 'transfer' if 'transferencia' in payment_method.name.lower() else 'other'
    payment_status = 'pending' if is_mp or payment_type == 'transfer' else 'approved'
    
    Payment.objects.create(
        order=order,
        payment_method=payment_method,
        amount=total,
        status=payment_status,
        payment_type=payment_type,
    )

    # Registrar evento
    MetricEvent.objects.create(
        event_type='checkout_started',
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key,
        metadata={'order_id': order.id, 'total': total}
    )

    # Correos al crear el pedido (todos los métodos de pago, incl. MP antes de ir al checkout MP)
    try:
        send_order_confirmation_email(order)
    except Exception as e:
        print(f'Error al enviar email de confirmación: {str(e)}')
    try:
        send_order_notification_to_admin(order)
    except Exception as e:
        print(f'Error al enviar notificación al admin: {str(e)}')

    if is_mp:
        base_url = (settings.MP_BASE_URL or '').strip().rstrip('/')
        if not base_url:
            messages.error(request, 'Mercado Pago no está configurado (falta MP_BASE_URL).')
            return redirect('shop:order_confirmation', order_id=order.id)
        # MP exige HTTPS y URLs con formato válido. Error típico: pegar la línea completa de ngrok
        # "Forwarding https://... -> http://localhost:8000" en vez de solo la URL.
        parsed = urlparse(base_url)
        if parsed.scheme != 'https' or not parsed.netloc or ' ' in base_url or '->' in base_url:
            messages.error(
                request,
                f'MP_BASE_URL inválido. Debe ser solo una URL HTTPS (ej: https://xxxx.ngrok-free.dev). Valor actual: "{base_url}"'
            )
            return redirect('shop:order_confirmation', order_id=order.id)

        # Recomendaciones Mercado Pago: enriquecer "items" dentro de la sección "Preferencias"
        # usando los OrderItem del pedido (creamos 1 solo item con el total, pero igual enviamos
        # id/categoría/description para mejorar el motor de prevención de fraude).
        items_qs = order.items.select_related('product__category')
        mp_item_id = None
        mp_item_category_id = None
        mp_item_description = None
        if items_qs.exists():
            first = items_qs.first()
            if first:
                mp_item_id = str(first.id)
                if first.product_id and first.product and first.product.category_id:
                    mp_item_category_id = str(first.product.category_id)
                product_names = [it.product.name for it in items_qs[:3] if it.product_id and it.product]
                if product_names:
                    suffix = "..." if items_qs.count() > 3 else ""
                    mp_item_description = f"Pedido {order.order_number}: {', '.join(product_names)}{suffix}"

        success_url = f"{base_url}{reverse('shop:mp_return', kwargs={'status': 'success', 'order_id': order.id})}"
        pending_url = f"{base_url}{reverse('shop:mp_return', kwargs={'status': 'pending', 'order_id': order.id})}"
        failure_url = f"{base_url}{reverse('shop:mp_return', kwargs={'status': 'failure', 'order_id': order.id})}"

        notification_url = (settings.MP_WEBHOOK_URL or "").strip()
        if not notification_url:
            notification_url = f"{base_url}{reverse('shop:mp_webhook')}"
        # Sanitizar notification_url también
        nparsed = urlparse(notification_url)
        if nparsed.scheme != 'https' or not nparsed.netloc or ' ' in notification_url:
            messages.error(
                request,
                f'MP_WEBHOOK_URL inválido (debe ser HTTPS). Valor actual: "{notification_url}"'
            )
            return redirect('shop:order_confirmation', order_id=order.id)

        pref = create_checkout_pro_preference(
            order_id=order.id,
            order_number=order.order_number,
            total_amount_clp=order.total,
            buyer_email=order.customer_email,
            success_url=success_url,
            pending_url=pending_url,
            failure_url=failure_url,
            notification_url=notification_url,
            item_id=mp_item_id,
            item_category_id=mp_item_category_id,
            item_description=mp_item_description,
        )
        order.mp_preference_id = pref.preference_id
        order.mp_init_point = pref.init_point
        order.save(update_fields=['mp_preference_id', 'mp_init_point', 'status', 'stock_committed'])
        
        # Actualizar Payment con información de Mercado Pago
        payment = order.get_latest_payment()
        if payment:
            payment.mp_preference_id = pref.preference_id
            payment.mp_init_point = pref.init_point
            payment.save(update_fields=['mp_preference_id', 'mp_init_point'])

        return redirect(pref.init_point)

    # Mensaje de éxito (flujo existente)
    messages.success(
        request,
        f'¡Pedido #{order.order_number} creado exitosamente! 🎉 Serás contactado por uno de nuestros vendedores en breve. '
        f'Puedes contactarnos indicando tu número de pedido: #{order.order_number}',
        extra_tags='alert-success alert-dismissible fade show'
    )
    return redirect('shop:order_confirmation', order_id=order.id)


def mp_return(request: HttpRequest, status: str, order_id: int):
    """
    Retorno del Checkout Pro (NO confiable para confirmar pago).
    La confirmación real se hace por webhook.
    """
    order = get_object_or_404(Order, id=order_id)

    if status == 'success':
        messages.info(request, 'Pago recibido. Estamos confirmando tu transacción… (puede tardar unos segundos).')
    elif status == 'pending':
        messages.warning(request, 'Tu pago quedó pendiente. Puedes reintentar o esperar la confirmación.')
    else:
        messages.error(request, 'El pago fue rechazado o cancelado. Puedes reintentar el pago.')

    return redirect('shop:order_confirmation', order_id=order.id)


@csrf_exempt
def mp_webhook(request: HttpRequest):
    """
    Webhook de Mercado Pago.
    - Recibe notificaciones de pagos
    - Consulta el pago vía API (source of truth)
    - Actualiza Order y descuenta stock cuando el pago queda aprobado (idempotente)
    """
    if request.method not in ('POST', 'GET'):
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}') if request.body else {}
    except Exception:
        payload = {}

    # Mercado Pago puede enviar payment_id por query o por body
    payment_id = (
        request.GET.get('data.id')
        or request.GET.get('id')
        or (payload.get('data') or {}).get('id')
        or payload.get('id')
    )
    if not payment_id:
        # Aceptar igualmente (evita reintentos infinitos por payloads no-payment)
        return HttpResponse(status=200)

    mp_payment_data = get_payment(str(payment_id))
    external_reference = mp_payment_data.get('external_reference')
    status = mp_payment_data.get('status')

    if not external_reference:
        return HttpResponse(status=200)

    try:
        order_id = int(str(external_reference))
    except ValueError:
        return HttpResponse(status=200)

    with transaction.atomic():
        order = Order.objects.select_for_update().filter(id=order_id).first()
        if not order:
            return HttpResponse(status=200)

        # Mantener compatibilidad con campos antiguos en Order
        order.mp_payment_id = str(payment_id)
        order.mp_payment_status = str(status) if status else None
        order.mp_last_event_at = timezone.now()

        # Obtener o crear Payment para este pago de Mercado Pago
        payment_obj, created = Payment.objects.get_or_create(
            order=order,
            mp_payment_id=str(payment_id),
            defaults={
                'payment_method': order.payment_method,
                'amount': order.total,
                'status': 'pending',
                'payment_type': 'mercado_pago',
                'mp_preference_id': order.mp_preference_id,
                'mp_init_point': order.mp_init_point,
            }
        )
        
        # Actualizar Payment con el estado actual
        mp_status_map = {
            'approved': 'approved',
            'rejected': 'rejected',
            'cancelled': 'cancelled',
            'refunded': 'refunded',
            'charged_back': 'charged_back',
            'in_process': 'in_process',
            'pending': 'pending',
        }
        payment_status = mp_status_map.get(status, 'pending')
        payment_obj.status = payment_status
        # Obtener status_detail del diccionario de MP
        mp_status_detail = mp_payment_data.get('status_detail', '')
        payment_obj.mp_status_detail = mp_status_detail
        
        if status == 'approved':
            payment_obj.mark_as_approved(save=False)
        elif status in ('rejected', 'cancelled', 'charged_back', 'refunded'):
            payment_obj.mark_as_rejected(save=False)
        
        payment_obj.save()

        # Si se aprobó: confirmar pedido. Stock ya se descontó en checkout (pedidos nuevos);
        # pedidos antiguos MP pueden tener stock_committed=False hasta este webhook.
        if status == 'approved':
            order.status = 'confirmed'
            if not order.stock_committed:
                for item in order.items.select_related('product', 'product_variant').all():
                    if item.product_variant_id:
                        pv = ProductVariant.objects.select_for_update().get(pk=item.product_variant_id)
                        if item.quantity > pv.stock:
                            order.status = 'cancelled'
                            payment_obj.status = 'cancelled'
                            payment_obj.save()
                            order.save(update_fields=['mp_payment_id', 'mp_payment_status', 'mp_last_event_at', 'status'])
                            return HttpResponse(status=200)
                        pv.stock -= item.quantity
                        pv.save(update_fields=['stock'])
                        ProductVariant.sync_parent_product_stock(item.product_id)
                    else:
                        product = Product.objects.select_for_update().get(id=item.product_id)
                        if item.quantity > product.stock:
                            order.status = 'cancelled'
                            payment_obj.status = 'cancelled'
                            payment_obj.save()
                            order.save(update_fields=['mp_payment_id', 'mp_payment_status', 'mp_last_event_at', 'status'])
                            return HttpResponse(status=200)
                        product.stock -= item.quantity
                        product.save(update_fields=['stock'])
                order.stock_committed = True

        elif status in ('rejected', 'cancelled', 'charged_back', 'refunded'):
            # Devolver stock si el pago nunca se concretó (reserva hecha en checkout)
            if order.status == 'pending_payment':
                order.restore_committed_stock()
            order.status = 'cancelled'
        else:
            # in_process / pending / etc.
            if order.status == 'realized':
                order.status = 'pending_payment'

        order.save(update_fields=[
            'mp_payment_id',
            'mp_payment_status',
            'mp_last_event_at',
            'status',
            'stock_committed',
        ])

    return HttpResponse(status=200)


def order_confirmation(request, order_id):
    """Vista de confirmación de pedido"""
    order = get_object_or_404(
        Order.objects.select_related(
            'shipping_method', 'payment_method', 'user', 'coupon'
        ).prefetch_related('items'),
        id=order_id,
    )

    # Permitir ver el pedido si:
    # - El usuario está autenticado y es el dueño o es staff
    # - O si es usuario anónimo (no verificamos permisos, solo mostramos el pedido)
    if request.user.is_authenticated:
        if order.user != request.user and not request.user.is_staff:
            # Si no es el dueño ni staff, redirigir sin mensaje de error
            return redirect('shop:home')

    pm_raw = (order.payment_method.name or '') if order.payment_method_id else ''
    pm_lower = pm_raw.lower()
    is_mercadopago = 'mercado' in pm_lower
    mp_approved = order.mp_payment_status == 'approved' or order.status == 'confirmed'
    mp_rejected = order.mp_payment_status == 'rejected' or order.status == 'cancelled'
    is_transfer = 'transferencia' in pm_lower

    if is_mercadopago:
        if mp_approved:
            order_confirm_tone = 'success'
        elif mp_rejected:
            order_confirm_tone = 'danger'
        else:
            order_confirm_tone = 'warning'
    else:
        order_confirm_tone = 'success'

    context = {
        'order': order,
        'pm_lower': pm_lower,
        'is_mercadopago': is_mercadopago,
        'mp_approved': mp_approved,
        'mp_rejected': mp_rejected,
        'is_transfer': is_transfer,
        'order_confirm_tone': order_confirm_tone,
    }
    return render(request, 'shop/order_confirmation.html', context)


def register_view(request):
    """Vista de registro de usuario"""
    if request.user.is_authenticated:
        return redirect('shop:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Especificar el backend de autenticación
            from django.contrib.auth.backends import ModelBackend
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'¡Cuenta creada exitosamente, {user.first_name}!')
            return redirect('shop:home')
    else:
        form = UserRegistrationForm()

    return render(request, 'shop/register.html', {'form': form})


def login_view(request):
    """Vista de login con email"""
    from django.contrib.auth import authenticate

    if request.user.is_authenticated:
        return redirect('shop:home')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        if email and password:
            user = authenticate(request, username=email, password=password)
            if user is not None:
                # Especificar el backend de autenticación
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f'¡Bienvenido, {user.first_name or user.email}!')
                next_url = request.GET.get('next', 'shop:home')
                return redirect(next_url)
            else:
                messages.error(request, 'Correo electrónico o contraseña incorrectos.')
        else:
            messages.error(request, 'Por favor completa todos los campos.')
    
    return render(request, 'shop/login.html')


def logout_view(request):
    """Vista de logout"""
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('shop:home')


def contact_view(request):
    """Vista de contacto"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Mensaje enviado! Te contactaremos pronto.')
            return redirect('shop:contact')
    else:
        form = ContactForm()

    return render(request, 'shop/contact.html', {'form': form})


@login_required
def profile(request):
    """Perfil del usuario: datos personales y pedidos (POST = guardar cambios con validación)."""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('shop:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(
        request,
        'shop/profile.html',
        {'form': form, 'orders': orders},
    )


def get_comunas(request):
    """
    Vista AJAX para obtener las comunas de una región específica
    """
    region = request.GET.get('region', '')
    if not region:
        return JsonResponse({'comunas': []})
    
    comunas = get_comunas_choices(region)
    return JsonResponse({'comunas': comunas})


def search_order(request):
    """
    Vista para buscar pedidos por número de pedido.
    Accesible para usuarios anónimos.
    """
    order = None
    order_number = request.GET.get('order_number', '').strip()
    error = None
    
    if order_number:
        # Limpiar el número de pedido (eliminar espacios y caracteres especiales comunes)
        order_number_clean = order_number.upper().strip().replace('#', '').replace(' ', '')
        
        # Buscar por número de pedido completo
        # El número de pedido tiene formato: {ID}{InicialNombre}{InicialEmail}{Año-Día-Mes}
        # Extraer el ID del inicio para buscar el pedido
        try:
            # Extraer todos los dígitos consecutivos del inicio (el ID)
            order_id_str = ''
            for char in order_number_clean:
                if char.isdigit():
                    order_id_str += char
                else:
                    break
            
            if order_id_str:
                # Buscar el pedido por ID
                try:
                    order = Order.objects.get(id=int(order_id_str))
                    # Verificar que el número generado coincida exactamente con el ingresado
                    generated_number = order.order_number.upper()
                    if generated_number != order_number_clean:
                        order = None
                        error = "No se encontró ningún pedido con ese número. Verifica que hayas ingresado el número completo correctamente."
                except Order.DoesNotExist:
                    error = "No se encontró ningún pedido con ese número."
            else:
                error = "El número de pedido no es válido. Debe contener al menos un número al inicio."
        except ValueError:
            error = "El número de pedido no es válido."
    
    context = {
        'order': order,
        'order_number': order_number,
        'error': error,
    }
    
    return render(request, 'shop/search_order.html', context)


def terms_and_conditions(request):
    """Vista para mostrar los Términos y Condiciones"""
    return render(request, 'shop/terms_and_conditions.html')


def privacy_policy(request):
    """Vista para mostrar las Políticas de Privacidad"""
    return render(request, 'shop/privacy_policy.html')


@login_required
def admin_dashboard(request):
    """Dashboard de administración - Solo para usuarios staff"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('shop:home')
    
    from django.db.models import Sum, Count, Q, F
    from django.utils import timezone
    from datetime import timedelta
    
    # ========== CONTABILIDAD ==========
    # Pedidos pagados (confirmed, shipped, delivered)
    paid_statuses = ['confirmed', 'shipped', 'delivered']
    paid_orders = Order.objects.filter(status__in=paid_statuses)
    
    # Pedidos pendientes
    pending_orders = Order.objects.filter(status='pending_payment')
    
    # Estadísticas de ventas
    total_sales = paid_orders.aggregate(total=Sum('total'))['total'] or 0
    total_orders_paid = paid_orders.count()
    total_orders_pending = pending_orders.count()
    
    # Ventas del mes actual
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_sales = paid_orders.filter(created_at__gte=current_month_start).aggregate(
        total=Sum('total')
    )['total'] or 0
    
    # Ventas de la semana actual
    week_start = timezone.now() - timedelta(days=timezone.now().weekday())
    weekly_sales = paid_orders.filter(created_at__gte=week_start).aggregate(
        total=Sum('total')
    )['total'] or 0
    
    # Últimos pedidos realizados (limitado a 10)
    recent_realized_orders = Order.objects.filter(status='realized').select_related('user', 'payment_method', 'shipping_method').prefetch_related('items').order_by('-created_at')[:10]
    total_orders_realized = Order.objects.filter(status='realized').count()
    
    # Últimos pedidos pagados (limitado a 10)
    recent_paid_orders = paid_orders.select_related('user', 'payment_method', 'shipping_method').prefetch_related('items')[:10]
    
    # Últimos pedidos pendientes (limitado a 10)
    recent_pending_orders = pending_orders.select_related('user', 'payment_method', 'shipping_method').prefetch_related('items')[:10]
    
    # ========== CONTACTO ==========
    # Todos los mensajes de contacto
    contact_messages = ContactMessage.objects.all().order_by('-created_at')
    total_contact_messages = contact_messages.count()
    unresolved_messages = contact_messages.filter(resolved=False).count()
    
    # ========== MÉTRICAS ==========
    # Productos más vistos - obtener todos los eventos y procesar
    all_product_views = MetricEvent.objects.filter(event_type='product_view')
    product_view_counts = {}
    for event in all_product_views:
        product_id = event.metadata.get('product_id')
        if product_id:
            product_view_counts[product_id] = product_view_counts.get(product_id, 0) + 1
    
    # Ordenar y obtener top 10
    sorted_views = sorted(product_view_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    most_viewed_products = []
    for product_id, view_count in sorted_views:
        try:
            product = Product.objects.get(id=product_id)
            most_viewed_products.append({
                'product': product,
                'views': view_count
            })
        except (Product.DoesNotExist, ValueError):
            pass
    
    # Productos más vendidos
    best_sellers = OrderItem.objects.values('product').annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('line_total')
    ).order_by('-total_sold')[:10]
    
    best_selling_products = []
    for bs in best_sellers:
        try:
            product = Product.objects.get(id=bs['product'])
            best_selling_products.append({
                'product': product,
                'total_sold': bs['total_sold'],
                'total_revenue': bs['total_revenue']
            })
        except Product.DoesNotExist:
            pass
    
    # Productos menos clickeados/vistos
    all_products_list = Product.objects.all()
    product_view_map = {}
    for event in all_product_views:
        product_id = event.metadata.get('product_id')
        if product_id:
            product_view_map[product_id] = product_view_map.get(product_id, 0) + 1
    
    least_viewed_products = []
    for product in all_products_list:
        view_count = product_view_map.get(product.id, 0)
        least_viewed_products.append({
            'product': product,
            'views': view_count
        })
    
    # Ordenar por menos vistas y tomar los primeros 10
    least_viewed_products = sorted(least_viewed_products, key=lambda x: x['views'])[:10]
    
    # Productos agregados al carrito más veces
    all_cart_events = MetricEvent.objects.filter(event_type='add_to_cart')
    product_cart_counts = {}
    for event in all_cart_events:
        product_id = event.metadata.get('product_id')
        if product_id:
            product_cart_counts[product_id] = product_cart_counts.get(product_id, 0) + 1
    
    # Ordenar y obtener top 10
    sorted_carts = sorted(product_cart_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    most_carted_products = []
    for product_id, cart_count in sorted_carts:
        try:
            product = Product.objects.get(id=product_id)
            most_carted_products.append({
                'product': product,
                'cart_count': cart_count
            })
        except (Product.DoesNotExist, ValueError):
            pass
    
    context = {
        # Contabilidad
        'total_sales': total_sales,
        'monthly_sales': monthly_sales,
        'weekly_sales': weekly_sales,
        'total_orders_paid': total_orders_paid,
        'total_orders_pending': total_orders_pending,
        'total_orders_realized': total_orders_realized,
        'recent_realized_orders': recent_realized_orders,
        'recent_paid_orders': recent_paid_orders,
        'recent_pending_orders': recent_pending_orders,
        
        # Contacto
        'contact_messages': contact_messages[:20],  # Últimos 20
        'total_contact_messages': total_contact_messages,
        'unresolved_messages': unresolved_messages,
        
        # Métricas
        'most_viewed_products': most_viewed_products,
        'best_selling_products': best_selling_products,
        'least_viewed_products': least_viewed_products,
        'most_carted_products': most_carted_products,
    }
    
    return render(request, 'shop/admin_dashboard.html', context)


@login_required
@require_POST
def delete_contact_message(request, message_id):
    """Eliminar un mensaje de contacto"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('shop:home')
    
    message = get_object_or_404(ContactMessage, id=message_id)
    message.delete()
    messages.success(request, 'Mensaje eliminado correctamente.')
    return redirect('shop:admin_dashboard')


@login_required
def contact_message_detail(request, message_id):
    """Ver detalles de un mensaje de contacto"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('shop:home')
    
    message = get_object_or_404(ContactMessage, id=message_id)
    return render(request, 'shop/admin_contact_detail.html', {'message': message})


@login_required
@require_POST
def update_order_status(request, order_id):
    """Actualizar el estado de un pedido"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('shop:home')
    
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    
    if not new_status:
        messages.error(request, 'Debes seleccionar un estado válido.')
        return redirect('shop:admin_dashboard')
    
    # Validar que el estado sea válido
    valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
    if new_status not in valid_statuses:
        messages.error(request, 'Estado no válido.')
        return redirect('shop:admin_dashboard')
    
    old_status = order.get_status_display()
    order.status = new_status
    order.save()
    
    messages.success(request, f'Estado del pedido #{order.id} actualizado de "{old_status}" a "{order.get_status_display()}".')
    
    # Redirigir según desde dónde se llamó
    if request.POST.get('from_detail'):
        return redirect('shop:order_confirmation', order_id=order.id)
    return redirect('shop:admin_dashboard')


@require_GET
def preview_email_customer(request):
    """Previsualiza el HTML del correo al cliente (solo DEBUG)."""
    if not settings.DEBUG:
        raise Http404()
    ctx = get_mock_order_email_context()
    # Base del sitio actual para que logo e imágenes carguen en local (no solo SITE_PUBLIC_URL).
    ctx['email_site_base'] = request.build_absolute_uri('/').rstrip('/')
    return render(request, 'shop/emails/order_confirmation.html', ctx)


@require_GET
def preview_email_admin(request):
    """Previsualiza el HTML del correo al administrador (solo DEBUG)."""
    if not settings.DEBUG:
        raise Http404()
    ctx = get_mock_order_email_context()
    ctx['email_site_base'] = request.build_absolute_uri('/').rstrip('/')
    return render(request, 'shop/emails/order_notification_admin.html', ctx)