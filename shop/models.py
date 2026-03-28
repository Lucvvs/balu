import json

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Sum


class CustomUserManager(BaseUserManager):
    """Manager personalizado para el modelo de usuario"""
    def create_user(self, email, password=None, **extra_fields):
        """Crea y guarda un usuario con email y contraseña"""
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Crea y guarda un superusuario con email y contraseña"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Modelo de usuario personalizado que usa email como username"""
    email = models.EmailField(unique=True, verbose_name="Correo electrónico")
    first_name = models.CharField(max_length=30, verbose_name="Nombre")
    last_name = models.CharField(max_length=30, verbose_name="Apellido")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    is_staff = models.BooleanField(default=False, verbose_name="Es staff")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.email

    @property
    def username(self):
        """Propiedad username que devuelve el email para compatibilidad con django-allauth"""
        return self.email

    def get_full_name(self):
        """Retorna el nombre completo"""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Retorna el primer nombre"""
        return self.first_name


class Brand(models.Model):
    """Modelo para las marcas de productos"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    slug = models.SlugField(max_length=100, unique=True, blank=True, verbose_name="Slug")
    logo = models.ImageField(upload_to='brands/', blank=True, null=True, verbose_name="Logo")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Category(models.Model):
    """Modelo para las categorías de productos"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    slug = models.SlugField(max_length=100, unique=True, blank=True, verbose_name="Slug")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    highlight_on_home = models.BooleanField(default=False, verbose_name="Destacar en inicio")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Modelo principal para los productos"""
    SIZE_CHOICES = [
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Nombre")
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name="Slug")
    short_description = models.CharField(max_length=200, verbose_name="Descripción corta")
    description = models.TextField(verbose_name="Descripción completa")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', verbose_name="Categoría")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name="Marca")
    price = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Precio original (CLP)")
    offer_price = models.IntegerField(validators=[MinValueValidator(0)], null=True, blank=True, verbose_name="Precio oferta (CLP)")
    stock = models.IntegerField(validators=[MinValueValidator(0)], default=0, verbose_name="Stock")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    is_offer = models.BooleanField(default=False, verbose_name="En oferta")
    is_best_seller = models.BooleanField(default=False, verbose_name="Más vendido")
    offer_order = models.IntegerField(default=0, verbose_name="Orden en ofertas", 
                                      help_text="Número menor = aparece primero. Solo se muestran los 3 primeros. Usar 0 para no mostrar en ofertas.")
    featured_order = models.IntegerField(default=0, verbose_name="Orden en más vendidos",
                                         help_text="Número menor = aparece primero. Solo se muestran los 3 primeros. Usar 0 para no mostrar en más vendidos.")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def current_price(self):
        """Retorna el precio actual (oferta si existe, sino el precio normal)"""
        return self.offer_price if self.offer_price else self.price

    @property
    def has_offer(self):
        """Indica si el producto tiene oferta"""
        return self.offer_price is not None and self.offer_price < self.price

    def uses_variant_stock(self):
        """True si el inventario se controla por filas ProductVariant (talla/color/opción)."""
        return self.variants.exists()

    def variants_catalog_json(self):
        """
        JSON (UTF-8) con variantes en stock para data-attributes en el catálogo.
        Lista de objetos: id, name, stock.
        """
        rows = list(
            self.variants.filter(stock__gt=0)
            .order_by('sort_order', 'name', 'id')
            .values('id', 'name', 'stock')
        )
        return json.dumps(rows, ensure_ascii=False)

    def is_available_for_purchase(self):
        """Hay al menos una unidad vendible (stock simple o alguna variante con stock)."""
        if self.uses_variant_stock():
            return self.variants.filter(stock__gt=0).exists()
        return self.stock > 0
    
    def get_primary_image(self):
        """Retorna la imagen principal del producto, o la primera si no hay principal"""
        try:
            # Primero intentar obtener la imagen con is_primary=True
            primary_image = self.images.filter(is_primary=True).first()
            if primary_image:
                return primary_image
            # Si no hay imagen principal, retornar la primera disponible
            images = self.images.all()
            if images:
                return images[0]
        except (IndexError, AttributeError, TypeError):
            pass
        return None


class ProductImage(models.Model):
    """Modelo para las imágenes de productos"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name="Producto")
    image = models.ImageField(upload_to='products/', verbose_name="Imagen")
    is_primary = models.BooleanField(default=False, verbose_name="Imagen principal")
    order = models.IntegerField(default=0, verbose_name="Orden")

    class Meta:
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de productos"
        # True antes que False: la principal primero; luego campo "Orden" e id
        ordering = ['-is_primary', 'order', 'id']

    def __str__(self):
        return f"{self.product.name} - Imagen {self.order}"


class ProductVariant(models.Model):
    """
    Una opción vendible del producto (talla, color, etc.) con stock propio.
    Si el producto tiene al menos una variante, el stock del producto padre
    se mantiene como suma de las variantes (sincronizado al guardar/borrar variantes).
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Producto',
    )
    name = models.CharField(
        max_length=64,
        verbose_name='Opción (talla, color, etc.)',
        help_text='Etiqueta que ve el cliente, ej: S, M, Amarilla.',
    )
    stock = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        verbose_name='Stock',
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name='Orden',
        help_text='Menor número = aparece primero en el selector.',
    )

    class Meta:
        verbose_name = 'Variante de producto'
        verbose_name_plural = 'Variantes de producto'
        ordering = ['sort_order', 'name', 'id']
        unique_together = [('product', 'name')]

    def __str__(self):
        return f'{self.product.name} — {self.name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        ProductVariant.sync_parent_product_stock(self.product_id)

    def delete(self, *args, **kwargs):
        product_id = self.product_id
        super().delete(*args, **kwargs)
        ProductVariant.sync_parent_product_stock(product_id)

    @staticmethod
    def sync_parent_product_stock(product_id):
        """Actualiza Product.stock como suma de variantes; no hace nada si no hay variantes."""
        agg = ProductVariant.objects.filter(product_id=product_id).aggregate(t=Sum('stock'))
        total = agg['t']
        if total is None:
            return
        Product.objects.filter(pk=product_id).update(stock=total or 0)

    @classmethod
    def replace_from_available_sizes_csv(cls, product, available_sizes_raw, total_stock: int):
        """
        Elimina variantes actuales y las recrea desde una cadena tipo "S,M,L" o colores.
        Reparte total_stock entre las opciones. Sin opciones, deja solo el stock del producto.
        """
        raw = (available_sizes_raw or '').strip()
        cls.objects.filter(product=product).delete()
        total_stock = max(0, int(total_stock))
        if not raw:
            Product.objects.filter(pk=product.pk).update(stock=total_stock)
            return
        names = [s.strip() for s in raw.split(',') if s.strip()]
        if not names:
            Product.objects.filter(pk=product.pk).update(stock=total_stock)
            return
        n = len(names)
        base = total_stock // n
        rem = total_stock % n
        for i, name in enumerate(names):
            stock = base + (1 if i < rem else 0)
            cls.objects.create(
                product=product,
                name=name[:64],
                stock=stock,
                sort_order=i,
            )


class Coupon(models.Model):
    """Modelo para cupones de descuento"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Porcentaje'),
        ('fixed', 'Monto fijo'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name="Código")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Descripción")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage', verbose_name="Tipo de descuento")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")
    active = models.BooleanField(default=True, verbose_name="Activo")
    valid_from = models.DateTimeField(verbose_name="Válido desde")
    valid_to = models.DateTimeField(verbose_name="Válido hasta")
    min_order_amount = models.IntegerField(null=True, blank=True, verbose_name="Monto mínimo de pedido (CLP)")
    max_uses = models.IntegerField(null=True, blank=True, verbose_name="Usos máximos")
    uses_count = models.IntegerField(default=0, verbose_name="Usos actuales")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        verbose_name = "Cupón"
        verbose_name_plural = "Cupones"
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    def is_valid(self, order_amount=None):
        """Verifica si el cupón es válido"""
        now = timezone.now()
        if not self.active:
            return False
        if now < self.valid_from or now > self.valid_to:
            return False
        if self.max_uses and self.uses_count >= self.max_uses:
            return False
        if self.min_order_amount and order_amount and order_amount < self.min_order_amount:
            return False
        return True

    def calculate_discount(self, order_amount):
        """Calcula el descuento aplicable"""
        if not self.is_valid(order_amount):
            return 0
        if self.discount_type == 'percentage':
            return int(order_amount * (self.amount / 100))
        return int(self.amount)


class ShippingMethod(models.Model):
    """Modelo para métodos de envío"""
    name = models.CharField(max_length=100, verbose_name="Nombre")
    description = models.TextField(verbose_name="Descripción")
    base_price = models.IntegerField(validators=[MinValueValidator(0)], default=0, verbose_name="Precio base (CLP)")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Método de envío"
        verbose_name_plural = "Métodos de envío"
        ordering = ['base_price']

    def __str__(self):
        return self.name

    def resolve_price(self, subtotal: int, region: str = '', comuna: str = '') -> int:
        """
        Precio de envío según reglas (región/comuna/monto). Retiro (base_price 0) → 0.
        Si no hay reglas activas, usa base_price.
        """
        from .utils import normalize_shipping_match_string

        if self.base_price == 0:
            return 0
        region_n = normalize_shipping_match_string(region or '')
        comuna_n = normalize_shipping_match_string(comuna or '')
        rules = list(
            ShippingRule.objects.filter(
                shipping_method=self,
                is_active=True,
                min_order_amount__lte=subtotal,
            )
        )
        if not rules:
            return self.base_price
        candidates = []
        for rule in rules:
            if rule.region and normalize_shipping_match_string(rule.region) != region_n:
                continue
            if rule.comuna and normalize_shipping_match_string(rule.comuna) != comuna_n:
                continue
            specificity = (2 if rule.region else 0) + (1 if rule.comuna else 0)
            candidates.append((specificity, rule.priority, rule.min_order_amount, rule.price))
        if not candidates:
            return self.base_price
        candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        return candidates[0][3]


class ShippingRule(models.Model):
    """Reglas de precio por región/comuna/monto para un método de envío (ej. domicilio)."""
    shipping_method = models.ForeignKey(
        ShippingMethod,
        on_delete=models.CASCADE,
        related_name='rules',
        verbose_name="Método de envío",
    )
    min_order_amount = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Monto mínimo del pedido (CLP)',
        help_text='La regla aplica si el subtotal del carrito es mayor o igual a este monto.',
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Región',
        help_text='Opcional. Copiar el nombre exacto del listado de checkout (ej. desde regiones_comunas.json). Vacío = resto de regiones.',
    )
    comuna = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Comuna',
        help_text='Opcional. Si se indica, debe coincidir con la comuna del cliente. Vacío = cualquier comuna de la región.',
    )
    price = models.IntegerField(validators=[MinValueValidator(0)], verbose_name='Precio de envío (CLP)')
    priority = models.IntegerField(
        default=0,
        verbose_name='Prioridad',
        help_text='Desempate: mayor valor gana si hay empate en especificidad y monto mínimo.',
    )
    is_active = models.BooleanField(default=True, verbose_name='Activa')

    class Meta:
        verbose_name = 'Regla de envío'
        verbose_name_plural = 'Reglas de envío'
        ordering = ['shipping_method', '-min_order_amount', 'region', 'comuna']

    def __str__(self):
        label = self.region or 'Resto de regiones'
        return f'{self.shipping_method.name}: {label} → ${self.price:,}'.replace(',', '.')


class PaymentMethod(models.Model):
    """Modelo para métodos de pago"""
    name = models.CharField(max_length=100, verbose_name="Nombre")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    image = models.ImageField(upload_to='payment_methods/', blank=True, null=True, verbose_name="Imagen/Icono")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Método de pago"
        verbose_name_plural = "Métodos de pago"
        ordering = ['name']

    def __str__(self):
        return self.name


class Cart(models.Model):
    """Modelo para carritos de compra"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='carts', verbose_name="Usuario")
    session_key = models.CharField(max_length=40, null=True, blank=True, verbose_name="Clave de sesión")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        verbose_name = "Carrito"
        verbose_name_plural = "Carritos"
        ordering = ['-updated_at']

    def __str__(self):
        if self.user:
            return f"Carrito de {self.user.email}"
        return f"Carrito anónimo {self.session_key}"

    def get_total_items(self):
        """Retorna el total de items en el carrito"""
        return sum(item.quantity for item in self.items.all())

    def get_subtotal(self):
        """Retorna el subtotal del carrito"""
        return sum(item.get_line_total() for item in self.items.all())


class CartItem(models.Model):
    """Modelo para items del carrito"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="Carrito")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Producto")
    variant = models.ForeignKey(
        'ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Variante',
        related_name='cart_items',
    )
    quantity = models.IntegerField(validators=[MinValueValidator(1)], default=1, verbose_name="Cantidad")
    unit_price = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Precio unitario al agregar")
    size = models.CharField(max_length=10, blank=True, null=True, verbose_name="Talla")

    class Meta:
        verbose_name = "Item de carrito"
        verbose_name_plural = "Items de carrito"
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'variant'],
                condition=models.Q(variant__isnull=False),
                name='unique_cartitem_cart_variant',
            ),
            models.UniqueConstraint(
                fields=['cart', 'product'],
                condition=models.Q(variant__isnull=True),
                name='unique_cartitem_cart_product_simple',
            ),
        ]

    def __str__(self):
        opt = self.variant.name if self.variant_id else self.size
        size_text = f" — {opt}" if opt else ""
        return f"{self.product.name} x {self.quantity}{size_text}"

    def get_line_total(self):
        """Retorna el total de la línea (cantidad * precio unitario)"""
        qty = self.quantity if self.quantity is not None else 0
        price = self.unit_price if self.unit_price is not None else 0
        return qty * price

    def get_stock_cap(self):
        """Tope de cantidad según inventario (variante o producto simple)."""
        if self.variant_id:
            return self.variant.stock
        return self.product.stock


class Order(models.Model):
    """Modelo para pedidos"""
    STATUS_CHOICES = [
        ('realized', 'Realizado'),
        ('pending_payment', 'Pendiente de pago'),
        ('confirmed', 'Confirmado'),
        ('shipped', 'Enviado'),
        ('ready_for_pickup', 'Listo para Retiro'),
        ('delivered', 'Entregado'),
        ('cancelled', 'Cancelado'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="Usuario")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='realized', verbose_name="Estado")
    
    # Datos de envío
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.PROTECT, verbose_name="Método de envío")
    shipping_region = models.CharField(max_length=100, blank=True, null=True, verbose_name="Región")
    shipping_comuna = models.CharField(max_length=100, blank=True, null=True, verbose_name="Comuna")
    shipping_address = models.TextField(blank=True, null=True, verbose_name="Dirección")
    shipping_notes = models.TextField(blank=True, null=True, verbose_name="Indicaciones adicionales")
    shipping_cost = models.IntegerField(validators=[MinValueValidator(0)], default=0, verbose_name="Costo de envío (CLP)")
    
    # Método de pago
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, verbose_name="Método de pago")
    
    # Cupón
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Cupón")
    
    # Totales
    subtotal = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Subtotal (CLP)")
    discount_total = models.IntegerField(validators=[MinValueValidator(0)], default=0, verbose_name="Descuento total (CLP)")
    total = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Total (CLP)")

    # Mercado Pago (Checkout Pro)
    mp_preference_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="MP Preference ID")
    mp_init_point = models.URLField(blank=True, null=True, verbose_name="MP Init Point")
    mp_payment_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="MP Payment ID")
    mp_payment_status = models.CharField(max_length=50, blank=True, null=True, verbose_name="MP Payment Status")
    mp_last_event_at = models.DateTimeField(blank=True, null=True, verbose_name="Último evento MP")
    stock_committed = models.BooleanField(
        default=False,
        verbose_name="Stock descontado del inventario",
        help_text="True cuando el stock ya se descontó al crear el pedido (transferencia y Mercado Pago).",
    )
    
    # Datos del cliente (para usuarios no registrados)
    customer_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre del cliente")
    customer_email = models.EmailField(blank=True, null=True, verbose_name="Email del cliente")
    customer_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono del cliente")

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-created_at']

    def __str__(self):
        if self.user:
            return f"Pedido #{self.id} - {self.user.email}"
        return f"Pedido #{self.id} - {self.customer_name or 'Anónimo'}"

    def generate_order_number(self):
        """Genera número de pedido según formato: ID + inicial nombre + inicial email + (año - día - mes)"""
        from datetime import datetime
        now = datetime.now()
        
        # ID del pedido
        order_id = str(self.id)
        
        # Primera inicial del nombre y email
        if self.user:
            name_init = self.user.first_name[0].upper() if self.user.first_name else 'A'
            email_init = self.user.email[0].upper() if self.user.email else 'A'
        else:
            name_init = self.customer_name[0].upper() if self.customer_name else 'A'
            email_init = self.customer_email[0].upper() if self.customer_email else 'A'
        
        # Año - (día + mes)
        year = now.year
        day_month = now.day + now.month
        year_code = year - day_month
        
        return f"{order_id}{name_init}{email_init}{year_code}"

    @property
    def order_number(self):
        """Retorna el número de pedido formateado"""
        return self.generate_order_number()

    def is_pickup_order(self):
        """Determina si el pedido es para retiro en bodega"""
        if not self.shipping_method:
            return False
        # Verificar si el método de envío contiene palabras clave de retiro
        shipping_name = self.shipping_method.name.lower()
        return 'retiro' in shipping_name or 'bodega' in shipping_name or 'pickup' in shipping_name

    def get_status_progress(self):
        """
        Retorna información sobre el progreso del estado del pedido para la barra de progreso
        Returns: dict con 'current_index', 'statuses', 'current_status_display', 'progress_percentage'
        """
        # Si está cancelado, no mostrar progreso
        if self.status == 'cancelled':
            return None
        
        # Determinar si es retiro o envío
        is_pickup = self.is_pickup_order()
        
        # Estados según el tipo de pedido
        if is_pickup:
            # Para retiro en bodega: Realizado, Pendiente de Pago, Confirmado, Listo para Retiro, Entregado
            status_progress = [
                ('realized', 'Realizado'),
                ('pending_payment', 'Pendiente de Pago'),
                ('confirmed', 'Confirmado'),
                ('ready_for_pickup', 'Listo para Retiro'),
                ('delivered', 'Entregado'),
            ]
            status_order = ['realized', 'pending_payment', 'confirmed', 'ready_for_pickup', 'delivered']
        else:
            # Para envío: Realizado, Pendiente de Pago, Confirmado, Enviado, Entregado
            status_progress = [
                ('realized', 'Realizado'),
                ('pending_payment', 'Pendiente de Pago'),
                ('confirmed', 'Confirmado'),
                ('shipped', 'Enviado'),
                ('delivered', 'Entregado'),
            ]
            status_order = ['realized', 'pending_payment', 'confirmed', 'shipped', 'delivered']
        
        # Encontrar el índice del estado actual
        current_index = 0
        if self.status in status_order:
            current_index = status_order.index(self.status)
        
        # Calcular porcentaje de progreso (0-100%)
        total_steps = len(status_progress) - 1  # 4 pasos (0-3)
        if total_steps > 0:
            progress_percentage = int((current_index / total_steps) * 100)
        else:
            progress_percentage = 0
        
        return {
            'current_index': current_index,
            'statuses': status_progress,
            'current_status_display': self.get_status_display(),
            'progress_percentage': progress_percentage,
        }

    def get_total_paid(self):
        """Retorna el total pagado de todos los pagos aprobados"""
        from django.db.models import Sum
        total = self.payments.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
        return total

    def get_pending_amount(self):
        """Retorna el monto pendiente de pago"""
        return self.total - self.get_total_paid()

    def has_approved_payment(self):
        """Retorna True si tiene al menos un pago aprobado"""
        return self.payments.filter(status='approved').exists()

    def get_latest_payment(self):
        """Retorna el último pago creado"""
        return self.payments.order_by('-created_at').first()


class OrderItem(models.Model):
    """Modelo para items de pedido"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Pedido")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Producto")
    product_variant = models.ForeignKey(
        'ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Variante (referencia)',
        related_name='order_items',
    )
    product_name = models.CharField(max_length=200, verbose_name="Nombre del producto (snapshot)")
    variant_label = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name='Opción (snapshot)',
        help_text='Talla, color u otra opción al momento de la compra.',
    )
    unit_price = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Precio unitario")
    quantity = models.IntegerField(validators=[MinValueValidator(1)], verbose_name="Cantidad")
    line_total = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Total línea")

    class Meta:
        verbose_name = "Item de pedido"
        verbose_name_plural = "Items de pedido"

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class Payment(models.Model):
    """Modelo para pagos de pedidos"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('in_process', 'En proceso'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Cancelado'),
        ('refunded', 'Reembolsado'),
        ('charged_back', 'Contracargo'),
    ]

    PAYMENT_TYPE_CHOICES = [
        ('transfer', 'Transferencia Bancaria'),
        ('mercado_pago', 'Mercado Pago'),
        ('cash', 'Efectivo'),
        ('other', 'Otro'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments', verbose_name="Pedido")
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, verbose_name="Método de pago")
    amount = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Monto (CLP)")
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name="Estado")
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='other', verbose_name="Tipo de pago")
    
    # Información de Mercado Pago (si aplica)
    mp_payment_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="MP Payment ID")
    mp_preference_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="MP Preference ID")
    mp_init_point = models.URLField(blank=True, null=True, verbose_name="MP Init Point")
    mp_status_detail = models.CharField(max_length=100, blank=True, null=True, verbose_name="MP Status Detail")
    
    # Información de transferencia bancaria (si aplica)
    transfer_reference = models.CharField(max_length=200, blank=True, null=True, verbose_name="Referencia/Número de transferencia")
    transfer_bank = models.CharField(max_length=100, blank=True, null=True, verbose_name="Banco")
    transfer_account = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de cuenta")
    
    # Información adicional
    notes = models.TextField(blank=True, null=True, verbose_name="Notas")
    receipt_image = models.ImageField(upload_to='payment_receipts/', blank=True, null=True, verbose_name="Comprobante")
    
    # Fechas
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de pago")
    
    # Usuario que procesó el pago (para pagos manuales)
    processed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_payments', verbose_name="Procesado por")

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-created_at']

    def __str__(self):
        return f"Pago #{self.id} - Pedido #{self.order.id} - {self.get_status_display()} - ${self.amount:,}".replace(',', '.')

    @property
    def is_approved(self):
        """Retorna True si el pago está aprobado"""
        return self.status == 'approved'

    @property
    def is_pending(self):
        """Retorna True si el pago está pendiente"""
        return self.status == 'pending'

    def mark_as_approved(self, save=True):
        """Marca el pago como aprobado"""
        self.status = 'approved'
        if not self.paid_at:
            from django.utils import timezone
            self.paid_at = timezone.now()
        if save:
            self.save()

    def mark_as_rejected(self, save=True):
        """Marca el pago como rechazado"""
        self.status = 'rejected'
        if save:
            self.save()


class ContactMessage(models.Model):
    """Modelo para mensajes de contacto"""
    name = models.CharField(max_length=200, verbose_name="Nombre")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    message = models.TextField(verbose_name="Mensaje")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    resolved = models.BooleanField(default=False, verbose_name="Resuelto")

    class Meta:
        verbose_name = "Mensaje de contacto"
        verbose_name_plural = "Mensajes de contacto"
        ordering = ['-created_at']

    def __str__(self):
        return f"Mensaje de {self.name} - {self.created_at.strftime('%d/%m/%Y')}"


class MetricEvent(models.Model):
    """Modelo para eventos de métricas/analytics básico"""
    EVENT_TYPE_CHOICES = [
        ('product_view', 'Vista de producto'),
        ('add_to_cart', 'Agregar al carrito'),
        ('checkout_started', 'Inicio de checkout'),
        ('button_click', 'Click en botón'),
    ]

    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, verbose_name="Tipo de evento")
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario")
    session_key = models.CharField(max_length=40, blank=True, null=True, verbose_name="Clave de sesión")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="Dirección IP")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadatos")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        verbose_name = "Evento de métrica"
        verbose_name_plural = "Eventos de métricas"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"


class PromotionalBanner(models.Model):
    """Modelo para las franjas promocionales rotativas"""
    text = models.CharField(max_length=200, verbose_name="Texto promocional")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    order = models.IntegerField(default=0, verbose_name="Orden", 
                                help_text="Número menor = aparece primero. Usar 0 para no mostrar.")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        verbose_name = "Franja Promocional"
        verbose_name_plural = "Franjas Promocionales"
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.text
