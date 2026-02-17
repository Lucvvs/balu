from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json
from urllib.parse import urlparse

from .models import (
    Product, Category, Brand, ProductImage, Cart, CartItem, Order, OrderItem,
    Coupon, ShippingMethod, PaymentMethod, ContactMessage, MetricEvent
)
from .utils import get_comunas_choices
from .forms import (
    UserRegistrationForm, AddToCartForm, UpdateCartItemForm, CouponForm,
    CheckoutForm, ContactForm
)
from .utils import send_order_confirmation_email, send_order_notification_to_admin
from .mercadopago_client import create_checkout_pro_preference, get_payment


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
        Prefetch('images', queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id'))
    ).order_by('offer_order', '-created_at')[:3]

    # Productos más vendidos (máximo 3, ordenados por featured_order)
    best_sellers = Product.objects.filter(
        is_active=True,
        is_best_seller=True,
        stock__gt=0,
        featured_order__gt=0  # Solo productos con orden asignado
    ).select_related('category', 'brand').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id'))
    ).order_by('featured_order', '-created_at')[:3]

    # Categorías destacadas
    categories = Category.objects.filter(is_active=True, highlight_on_home=True)[:3]

    # Marcas para el banner (en orden específico: HRO, SHAFT, motocentric, 4RS, KOVIX)
    brand_order = ['hro', 'shaft', 'motocentric', '4rs', 'kovix']
    brands_dict = {brand.slug: brand for brand in Brand.objects.filter(is_active=True)}
    brands = [brands_dict[slug] for slug in brand_order if slug in brands_dict]

    context = {
        'offers': offers,
        'best_sellers': best_sellers,
        'categories': categories,
        'brands': brands,
    }
    return render(request, 'shop/home.html', context)


def products_list(request):
    """Vista de lista de productos con filtros"""
    products = Product.objects.filter(is_active=True).select_related(
        'category', 'brand'
    ).prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id'))
    ).order_by('-created_at')

    # Filtro por categoría
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)

    # Filtro por marca (insensible a mayúsculas/minúsculas)
    brand_slug = request.GET.get('brand')
    if brand_slug:
        brand_slug = brand_slug.lower().strip()  # Normalizar a minúsculas
        products = products.filter(brand__slug__iexact=brand_slug)

    # Filtro por ofertas - solo productos que realmente tienen oferta válida
    if request.GET.get('offers') == 'true':
        from django.db.models import F
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

    # Ordenamiento
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_asc':
        products = products.order_by('offer_price', 'price')
    elif sort_by == 'price_desc':
        products = products.order_by('-offer_price', '-price')
    elif sort_by == 'name':
        products = products.order_by('name')

    # Paginación
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Categorías para el filtro
    categories = Category.objects.filter(is_active=True)
    
    # Estado de filtro de ofertas
    current_offers = request.GET.get('offers') == 'true'

    context = {
        'products': page_obj,
        'categories': categories,
        'current_category': category_slug,
        'current_brand': brand_slug,
        'current_search': search_query,
        'current_sort': sort_by,
        'current_offers': current_offers,
    }
    return render(request, 'shop/products_list.html', context)


def product_detail(request, slug):
    """Vista de detalle de producto"""
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand').prefetch_related('images'),
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
    
    # Logging para productos relacionados
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f'[PRODUCT_DETAIL] Productos relacionados encontrados: {related_products.count()}')
    for related_product in related_products:
        images = related_product.images.all()
        logger.info(f'[PRODUCT_DETAIL] Relacionado: {related_product.name} - Imágenes en BD: {images.count()}')
        if images.count() > 0:
            first_img = images.first()
            logger.info(f'[PRODUCT_DETAIL]   Primera imagen: {first_img.image.name} -> URL: {first_img.image.url}')
            try:
                logger.info(f'[PRODUCT_DETAIL]   Path físico: {first_img.image.path}')
            except:
                logger.warning(f'[PRODUCT_DETAIL]   No se pudo obtener path físico')
        else:
            logger.warning(f'[PRODUCT_DETAIL]   [ERROR] No hay imágenes para {related_product.name}')

    # Obtener imágenes del producto
    images = product.images.all()
    primary_image = images.filter(is_primary=True).first()
    if not primary_image and images.exists():
        primary_image = images.first()

    # Registrar vista de producto
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
    
    if product.stock <= 0:
        messages.error(request, f'Lo sentimos, {product.name} no tiene stock disponible en este momento.')
        return redirect('shop:product_detail', slug=product.slug)
    
    form = AddToCartForm(request.POST, product=product)
    if not form.is_valid():
        messages.error(request, 'Por favor completa todos los campos correctamente.')
        return redirect('shop:product_detail', slug=product.slug)

    quantity = form.cleaned_data['quantity']
    size = form.cleaned_data.get('size', '') or None
    
    # Validar talla si el producto requiere tallas
    if product.has_sizes() and not size:
        messages.error(request, 'Por favor selecciona una talla.')
        return redirect('shop:product_detail', slug=product.slug)
    
    if quantity > product.stock:
        messages.error(request, f'No hay suficiente stock. Stock disponible: {product.stock}')
        return redirect('shop:product_detail', slug=product.slug)

    cart = get_or_create_cart(request)
    current_price = product.current_price

    # Obtener o crear item del carrito (con talla si aplica)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        size=size,
        defaults={
            'quantity': quantity,
            'unit_price': current_price,
        }
    )

    if not created:
        # Actualizar cantidad si ya existe
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock:
            messages.error(request, f'No hay suficiente stock. Stock disponible: {product.stock}')
            return redirect('shop:product_detail', slug=product.slug)
        cart_item.quantity = new_quantity
        cart_item.save()

    # Registrar evento
    MetricEvent.objects.create(
        event_type='add_to_cart',
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key,
        metadata={'product_id': product.id, 'quantity': quantity, 'size': size}
    )

    size_text = f" - Talla: {size}" if size else ""
    messages.success(request, f'{product.name}{size_text} agregado al carrito.')
    return redirect('shop:cart')


def cart_view(request):
    """Vista del carrito de compras"""
    cart = None
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.prefetch_related(
                'items__product__images'
            ).get(user=request.user)
        except Cart.DoesNotExist:
            cart = None
    elif request.session.session_key:
        try:
            cart = Cart.objects.prefetch_related(
                'items__product__images'
            ).get(session_key=request.session.session_key)
        except Cart.DoesNotExist:
            cart = None

    context = {
        'cart': cart,
        'coupon_form': CouponForm(),
        'checkout_form': CheckoutForm(),
        'shipping_methods': ShippingMethod.objects.filter(is_active=True),
        'payment_methods': PaymentMethod.objects.filter(is_active=True),
    }
    return render(request, 'shop/cart.html', context)


@require_POST
def update_cart_item(request, item_id):
    """Actualizar cantidad de item en carrito"""
    cart_item = get_object_or_404(CartItem, id=item_id)
    
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

    form = UpdateCartItemForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Cantidad inválida.')
        return redirect('shop:cart')

    quantity = form.cleaned_data['quantity']
    
    if quantity > cart_item.product.stock:
        messages.error(request, f'No hay suficiente stock. Stock disponible: {cart_item.product.stock}')
        return redirect('shop:cart')

    if quantity <= 0:
        cart_item.delete()
        messages.success(request, 'Item eliminado del carrito.')
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, 'Carrito actualizado.')

    return redirect('shop:cart')


@require_POST
def remove_cart_item(request, item_id):
    """Eliminar item del carrito"""
    cart_item = get_object_or_404(CartItem, id=item_id)
    
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
    size_text = f" - Talla: {cart_item.size}" if cart_item.size else ""
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
@transaction.atomic
def checkout(request):
    """Procesar checkout y crear pedido"""
    cart = None
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.prefetch_related('items__product').get(user=request.user)
        except Cart.DoesNotExist:
            messages.error(request, 'Tu carrito está vacío.')
            return redirect('shop:cart')
    elif request.session.session_key:
        try:
            cart = Cart.objects.prefetch_related('items__product').get(session_key=request.session.session_key)
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

    # Verificar stock antes de procesar
    for item in cart.items.all():
        if item.quantity > item.product.stock:
            messages.error(request, f'No hay suficiente stock para {item.product.name}. Stock disponible: {item.product.stock}')
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
    shipping_cost = shipping_method.base_price
    
    # Validación adicional para envío a domicilio
    if shipping_method.base_price > 0:
        shipping_region = form.cleaned_data.get('shipping_region', '').strip()
        shipping_comuna = form.cleaned_data.get('shipping_comuna', '').strip()
        shipping_address = form.cleaned_data.get('shipping_address', '').strip()
        
        if not shipping_region:
            messages.error(request, '❌ Error: Debe seleccionar una región para envío a domicilio.')
            return redirect('shop:cart')
        if not shipping_comuna:
            messages.error(request, '❌ Error: Debe seleccionar una comuna para envío a domicilio.')
            return redirect('shop:cart')
        if not shipping_address:
            messages.error(request, '❌ Error: Debe ingresar la dirección para envío a domicilio.')
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
        customer_email=form.cleaned_data.get('customer_email') or (request.user.email if request.user.is_authenticated else None),
        customer_phone=form.cleaned_data.get('customer_phone'),
        status='pending_payment' if is_mp else 'realized',
    )

    # Crear items del pedido y (si NO es Mercado Pago) actualizar stock inmediatamente
    for cart_item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            product_name=cart_item.product.name,
            unit_price=cart_item.unit_price,
            quantity=cart_item.quantity,
            line_total=cart_item.get_line_total(),
        )
        if not is_mp:
            # Actualizar stock (flujo existente)
            cart_item.product.stock -= cart_item.quantity
            cart_item.product.save()
            order.stock_committed = True

    # Limpiar carrito
    cart.items.all().delete()
    
    # Limpiar cupón de sesión
    if 'applied_coupon_id' in request.session:
        del request.session['applied_coupon_id']

    # Registrar evento
    MetricEvent.objects.create(
        event_type='checkout_started',
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key,
        metadata={'order_id': order.id, 'total': total}
    )

    # Enviar emails solo si NO es Mercado Pago (en MP se envía al aprobar vía webhook)
    if not is_mp:
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
        )
        order.mp_preference_id = pref.preference_id
        order.mp_init_point = pref.init_point
        order.save(update_fields=['mp_preference_id', 'mp_init_point', 'status', 'stock_committed'])

        return redirect(pref.init_point)

    # Mensaje de éxito (flujo existente)
    messages.success(
        request,
        f'¡Pedido #{order.order_number} creado exitosamente! 🎉 Serás contactado por uno de nuestros vendedores en breve. '
        f'Puedes contactarnos indicando tu número de pedido: #{order.order_number}',
        extra_tags='alert-success alert-dismissible fade show'
    )
    order.save(update_fields=['stock_committed'])
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

    payment = get_payment(str(payment_id))
    external_reference = payment.get('external_reference')
    status = payment.get('status')

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

        order.mp_payment_id = str(payment_id)
        order.mp_payment_status = str(status) if status else None
        order.mp_last_event_at = timezone.now()

        # Si se aprobó, confirmar y descontar stock una sola vez
        if status == 'approved':
            order.status = 'confirmed'
            if not order.stock_committed:
                # Descontar stock de manera segura
                for item in order.items.select_related('product').all():
                    product = Product.objects.select_for_update().get(id=item.product_id)
                    if item.quantity > product.stock:
                        # Si no hay stock, cancelar pedido (edge-case por carreras)
                        order.status = 'cancelled'
                        order.save(update_fields=['mp_payment_id', 'mp_payment_status', 'mp_last_event_at', 'status'])
                        return HttpResponse(status=200)
                    product.stock -= item.quantity
                    product.save(update_fields=['stock'])
                order.stock_committed = True

                # Emails post-pago
                try:
                    send_order_confirmation_email(order)
                except Exception as e:
                    print(f'Error al enviar email de confirmación (MP): {str(e)}')
                try:
                    send_order_notification_to_admin(order)
                except Exception as e:
                    print(f'Error al enviar notificación al admin (MP): {str(e)}')

        elif status in ('rejected', 'cancelled', 'charged_back', 'refunded'):
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
    order = get_object_or_404(Order, id=order_id)
    
    # Permitir ver el pedido si:
    # - El usuario está autenticado y es el dueño o es staff
    # - O si es usuario anónimo (no verificamos permisos, solo mostramos el pedido)
    if request.user.is_authenticated:
        if order.user != request.user and not request.user.is_staff:
            # Si no es el dueño ni staff, redirigir sin mensaje de error
            return redirect('shop:home')

    context = {
        'order': order,
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
    """Vista de perfil del usuario"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'shop/profile.html', context)


@login_required
@require_POST
def update_profile(request):
    """Actualizar perfil del usuario"""
    user = request.user
    
    # Confirmar con el usuario
    if request.POST.get('confirm') != 'yes':
        messages.error(request, 'Debes confirmar los cambios.')
        return redirect('shop:profile')
    
    # Actualizar datos
    user.first_name = request.POST.get('first_name', user.first_name)
    user.last_name = request.POST.get('last_name', user.last_name)
    user.email = request.POST.get('email', user.email)
    user.save()
    
    messages.success(request, 'Perfil actualizado correctamente.')
    return redirect('shop:profile')


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
