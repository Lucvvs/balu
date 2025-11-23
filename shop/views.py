from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction

from .models import (
    Product, Category, Brand, ProductImage, Cart, CartItem, Order, OrderItem,
    Coupon, ShippingMethod, PaymentMethod, ContactMessage, MetricEvent
)
from .forms import (
    UserRegistrationForm, AddToCartForm, UpdateCartItemForm, CouponForm,
    CheckoutForm, ContactForm
)


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
    # Productos en oferta (máximo 3)
    offers = Product.objects.filter(
        is_active=True,
        is_offer=True,
        stock__gt=0
    ).select_related('category', 'brand').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id'))
    )[:3]

    # Productos más vendidos (máximo 3)
    best_sellers = Product.objects.filter(
        is_active=True,
        is_best_seller=True,
        stock__gt=0
    ).select_related('category', 'brand').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.all().order_by('-is_primary', 'order', 'id'))
    )[:3]

    # Categorías destacadas
    categories = Category.objects.filter(is_active=True, highlight_on_home=True)[:3]

    # Marcas para el banner
    brands = Brand.objects.filter(is_active=True)[:6]

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

    # Filtro por marca
    brand_slug = request.GET.get('brand')
    if brand_slug:
        products = products.filter(brand__slug=brand_slug)

    # Filtro por ofertas
    if request.GET.get('offers') == 'true':
        products = products.filter(is_offer=True)

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

    context = {
        'products': page_obj,
        'categories': categories,
        'current_category': category_slug,
        'current_brand': brand_slug,
        'current_search': search_query,
        'current_sort': sort_by,
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
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
    )[:4]

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
    product = get_object_or_404(Product, id=product_id, is_active=True, stock__gt=0)
    
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
        messages.error(request, 'Por favor completa todos los campos requeridos.')
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

    # Aplicar descuento del cupón
    discount_total = 0
    if coupon and coupon.is_valid(subtotal):
        discount_total = coupon.calculate_discount(subtotal)
        coupon.uses_count += 1
        coupon.save()

    total = subtotal + shipping_cost - discount_total

    # Crear pedido
    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        shipping_method=shipping_method,
        shipping_region=form.cleaned_data.get('shipping_region'),
        shipping_comuna=form.cleaned_data.get('shipping_comuna'),
        shipping_address=form.cleaned_data.get('shipping_address'),
        shipping_cost=shipping_cost,
        payment_method=form.cleaned_data['payment_method'],
        coupon=coupon,
        subtotal=subtotal,
        discount_total=discount_total,
        total=total,
        customer_name=form.cleaned_data.get('customer_name') or (request.user.get_full_name() if request.user.is_authenticated else None),
        customer_email=form.cleaned_data.get('customer_email') or (request.user.email if request.user.is_authenticated else None),
        customer_phone=form.cleaned_data.get('customer_phone'),
        status='pending',
    )

    # Crear items del pedido y actualizar stock
    for cart_item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            product_name=cart_item.product.name,
            unit_price=cart_item.unit_price,
            quantity=cart_item.quantity,
            line_total=cart_item.get_line_total(),
        )
        # Actualizar stock
        cart_item.product.stock -= cart_item.quantity
        cart_item.product.save()

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

    messages.success(request, f'¡Pedido #{order.order_number} creado exitosamente! Serás contactado por uno de nuestros vendedores.')
    return redirect('shop:order_confirmation', order_id=order.id)


def order_confirmation(request, order_id):
    """Vista de confirmación de pedido"""
    order = get_object_or_404(Order, id=order_id)
    
    # Verificar que el pedido pertenece al usuario o sesión
    if request.user.is_authenticated:
        if order.user != request.user and not request.user.is_staff:
            messages.error(request, 'No tienes permiso para ver este pedido.')
            return redirect('shop:home')
    else:
        # Para usuarios anónimos, verificar por email o mostrar error
        if order.customer_email and order.customer_email != request.session.get('guest_email'):
            messages.error(request, 'No tienes permiso para ver este pedido.')
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
            login(request, user)
            messages.success(request, '¡Cuenta creada exitosamente!')
            return redirect('shop:home')
    else:
        form = UserRegistrationForm()

    return render(request, 'shop/register.html', {'form': form})


def login_view(request):
    """Vista de login"""
    from django.contrib.auth.forms import AuthenticationForm

    if request.user.is_authenticated:
        return redirect('shop:home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'¡Bienvenido, {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next', 'shop:home')
            return redirect(next_url)
    else:
        form = AuthenticationForm()

    return render(request, 'shop/login.html', {'form': form})


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
