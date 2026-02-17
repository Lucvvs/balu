from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    CustomUser, Brand, Category, Product, ProductImage, Coupon, ShippingMethod, PaymentMethod,
    Cart, CartItem, Order, OrderItem, ContactMessage, MetricEvent, PromotionalBanner
)


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Admin para el modelo de usuario personalizado"""
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas importantes', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'highlight_on_home')
    list_filter = ('is_active', 'highlight_on_home')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(admin.TabularInline):
    """Inline para imágenes de productos"""
    model = ProductImage
    extra = 1
    fields = ('image', 'is_primary', 'order')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'current_price_display', 'stock', 'is_active', 'is_offer', 'offer_order', 'is_best_seller', 'featured_order', 'created_at')
    list_filter = ('is_active', 'is_offer', 'is_best_seller', 'category', 'brand', 'created_at')
    search_fields = ('name', 'short_description', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ProductImageInline]
    fieldsets = (
        ('Información básica', {
            'fields': ('name', 'slug', 'short_description', 'description')
        }),
        ('Categorización', {
            'fields': ('category', 'brand')
        }),
        ('Precios', {
            'fields': ('price', 'offer_price')
        }),
        ('Stock y Estado', {
            'fields': ('stock', 'available_sizes', 'is_active', 'is_offer', 'is_best_seller')
        }),
        ('Orden en Destacados', {
            'fields': ('offer_order', 'featured_order'),
            'description': 'Asigna números de orden (1, 2, 3) para controlar qué productos aparecen primero. Solo se muestran los 3 primeros. Usa 0 para no mostrar.'
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def current_price_display(self, obj):
        """Muestra el precio actual formateado"""
        if obj.has_offer:
            return format_html(
                '<span style="text-decoration: line-through; color: #999;">${}</span> '
                '<span style="color: red; font-weight: bold;">${:,}</span>'.format(
                    obj.price, obj.offer_price
                ).replace(',', '.')
            )
        return format_html('<span>${:,}</span>'.format(obj.price).replace(',', '.'))
    current_price_display.short_description = 'Precio'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'amount_display', 'active', 'valid_from', 'valid_to', 'uses_count', 'max_uses')
    list_filter = ('active', 'discount_type', 'valid_from', 'valid_to')
    search_fields = ('code', 'description')
    readonly_fields = ('uses_count',)

    def amount_display(self, obj):
        """Muestra el monto del descuento formateado"""
        if obj.discount_type == 'percentage':
            return f"{obj.amount}%"
        return f"${int(obj.amount):,}".replace(',', '.')
    amount_display.short_description = 'Descuento'


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price_display', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')

    def base_price_display(self, obj):
        """Muestra el precio formateado"""
        if obj.base_price == 0:
            return "Gratis"
        return f"${obj.base_price:,}".replace(',', '.')
    base_price_display.short_description = 'Precio Base'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


class CartItemInline(admin.TabularInline):
    """Inline para items del carrito"""
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'size', 'unit_price', 'get_line_total_display')
    can_delete = False

    def get_line_total_display(self, obj):
        return f"${obj.get_line_total():,}".replace(',', '.')
    get_line_total_display.short_description = 'Total'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'session_key_display', 'items_count', 'subtotal_display', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'session_key')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CartItemInline]

    def user_display(self, obj):
        if obj.user:
            return obj.user.email
        return "Anónimo"
    user_display.short_description = 'Usuario'

    def session_key_display(self, obj):
        if obj.session_key:
            return obj.session_key[:20] + "..."
        return "-"
    session_key_display.short_description = 'Sesión'

    def items_count(self, obj):
        return obj.get_total_items()
    items_count.short_description = 'Items'

    def subtotal_display(self, obj):
        return f"${obj.get_subtotal():,}".replace(',', '.')
    subtotal_display.short_description = 'Subtotal'


class OrderItemInline(admin.TabularInline):
    """Inline para items de pedido"""
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'unit_price', 'quantity', 'line_total')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number_display', 'user_display', 'status', 'total_display', 'payment_method', 'shipping_method', 'created_at')
    list_filter = ('status', 'payment_method', 'shipping_method', 'created_at')
    search_fields = ('id', 'user__email', 'customer_name', 'customer_email', 'customer_phone')
    readonly_fields = ('created_at', 'updated_at', 'total', 'subtotal', 'discount_total', 'shipping_cost')
    inlines = [OrderItemInline]
    fieldsets = (
        ('Información del Pedido', {
            'fields': ('user', 'status', 'created_at', 'updated_at')
        }),
        ('Cliente', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Envío', {
            'fields': ('shipping_method', 'shipping_region', 'shipping_comuna', 'shipping_address', 'shipping_cost')
        }),
        ('Pago', {
            'fields': ('payment_method', 'coupon')
        }),
        ('Totales', {
            'fields': ('subtotal', 'discount_total', 'total')
        }),
    )
    actions = ['mark_as_confirmed', 'mark_as_shipped', 'mark_as_ready_for_pickup', 'mark_as_delivered', 'mark_as_cancelled']

    def order_number_display(self, obj):
        """Muestra el número de pedido personalizado"""
        return f"#{obj.order_number}"
    order_number_display.short_description = 'Número de Pedido'
    order_number_display.admin_order_field = 'id'  # Permite ordenar por ID

    def user_display(self, obj):
        if obj.user:
            return obj.user.email
        return obj.customer_name or "Anónimo"
    user_display.short_description = 'Cliente'

    def total_display(self, obj):
        return f"${obj.total:,}".replace(',', '.')
    total_display.short_description = 'Total'

    @admin.action(description='Marcar como confirmado')
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, f'{queryset.count()} pedido(s) marcado(s) como confirmado(s).')

    @admin.action(description='Marcar como enviado')
    def mark_as_shipped(self, request, queryset):
        """Marca como enviado (solo para pedidos con envío)"""
        updated = 0
        for order in queryset:
            if not order.is_pickup_order():
                order.status = 'shipped'
                order.save()
                updated += 1
        if updated > 0:
            self.message_user(request, f'{updated} pedido(s) marcado(s) como enviado(s).')
        else:
            self.message_user(request, 'No se actualizó ningún pedido. Esta acción solo aplica a pedidos con envío.', level='warning')

    @admin.action(description='Marcar como listo para retiro')
    def mark_as_ready_for_pickup(self, request, queryset):
        """Marca como listo para retiro (solo para pedidos de retiro en bodega)"""
        updated = 0
        for order in queryset:
            if order.is_pickup_order():
                order.status = 'ready_for_pickup'
                order.save()
                updated += 1
        if updated > 0:
            self.message_user(request, f'{updated} pedido(s) marcado(s) como listo(s) para retiro.')
        else:
            self.message_user(request, 'No se actualizó ningún pedido. Esta acción solo aplica a pedidos de retiro en bodega.', level='warning')

    @admin.action(description='Marcar como entregado')
    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')
        self.message_user(request, f'{queryset.count()} pedido(s) marcado(s) como entregado(s).')

    @admin.action(description='Marcar como cancelado')
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, f'{queryset.count()} pedido(s) marcado(s) como cancelado(s).')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at', 'resolved')
    list_filter = ('resolved', 'created_at')
    search_fields = ('name', 'email', 'phone', 'message')
    readonly_fields = ('created_at',)
    actions = ['mark_as_resolved', 'mark_as_unresolved']

    @admin.action(description='Marcar como resuelto')
    def mark_as_resolved(self, request, queryset):
        queryset.update(resolved=True)
        self.message_user(request, f'{queryset.count()} mensaje(s) marcado(s) como resuelto(s).')

    @admin.action(description='Marcar como no resuelto')
    def mark_as_unresolved(self, request, queryset):
        queryset.update(resolved=False)
        self.message_user(request, f'{queryset.count()} mensaje(s) marcado(s) como no resuelto(s).')


@admin.register(MetricEvent)
class MetricEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'user_display', 'created_at', 'metadata_summary')
    list_filter = ('event_type', 'created_at')
    search_fields = ('user__email', 'session_key', 'ip_address')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    def user_display(self, obj):
        if obj.user:
            return obj.user.email
        return "Anónimo"
    user_display.short_description = 'Usuario'

    def metadata_summary(self, obj):
        if obj.metadata:
            return str(obj.metadata)[:50] + "..."
        return "-"
    metadata_summary.short_description = 'Metadatos'

    def has_add_permission(self, request):
        return False  # Los eventos solo se crean automáticamente


@admin.register(PromotionalBanner)
class PromotionalBannerAdmin(admin.ModelAdmin):
    list_display = ('text', 'order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('text',)
    ordering = ('order', 'created_at')
    fieldsets = (
        ('Información', {
            'fields': ('text', 'is_active', 'order')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


# Configurar el sitio de admin
admin.site.site_header = "MotoMoto Admin"
admin.site.site_title = "MotoMoto Admin"
admin.site.index_title = "Panel de Administración"
