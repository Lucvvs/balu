from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.utils import timezone


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

    def get_full_name(self):
        """Retorna el nombre completo"""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Retorna el primer nombre"""
        return self.first_name
    
    @property
    def username(self):
        """Propiedad username que retorna el email para compatibilidad con django-allauth"""
        return self.email


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
    available_sizes = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tallas disponibles (separadas por coma, ej: S,M,L,XL)", help_text="Dejar vacío si no aplica tallas. Ejemplo: S,M,L,XL")
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

    def get_available_sizes_list(self):
        """Retorna lista de tallas disponibles"""
        if not self.available_sizes:
            return []
        return [size.strip() for size in self.available_sizes.split(',') if size.strip()]

    def has_sizes(self):
        """Indica si el producto tiene tallas"""
        return bool(self.available_sizes)
    
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
        ordering = ['is_primary', 'order', 'id']

    def __str__(self):
        return f"{self.product.name} - Imagen {self.order}"


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
    quantity = models.IntegerField(validators=[MinValueValidator(1)], default=1, verbose_name="Cantidad")
    unit_price = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Precio unitario al agregar")
    size = models.CharField(max_length=10, blank=True, null=True, verbose_name="Talla")

    class Meta:
        verbose_name = "Item de carrito"
        verbose_name_plural = "Items de carrito"
        unique_together = ['cart', 'product', 'size']

    def __str__(self):
        size_text = f" - Talla: {self.size}" if self.size else ""
        return f"{self.product.name} x {self.quantity}{size_text}"

    def get_line_total(self):
        """Retorna el total de la línea (cantidad * precio unitario)"""
        return self.quantity * self.unit_price


class Order(models.Model):
    """Modelo para pedidos"""
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('pending_payment', 'Pendiente de pago'),
        ('confirmed', 'Confirmado'),
        ('preparing', 'Preparando'),
        ('shipped', 'Enviado'),
        ('delivered', 'Entregado'),
        ('cancelled', 'Cancelado'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="Usuario")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Estado")
    
    # Datos de envío
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.PROTECT, verbose_name="Método de envío")
    shipping_region = models.CharField(max_length=100, blank=True, null=True, verbose_name="Región")
    shipping_comuna = models.CharField(max_length=100, blank=True, null=True, verbose_name="Comuna")
    shipping_address = models.TextField(blank=True, null=True, verbose_name="Dirección")
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
    stock_committed = models.BooleanField(default=False, verbose_name="Stock descontado (MP)")
    
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


class OrderItem(models.Model):
    """Modelo para items de pedido"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Pedido")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Producto")
    product_name = models.CharField(max_length=200, verbose_name="Nombre del producto (snapshot)")
    unit_price = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Precio unitario")
    quantity = models.IntegerField(validators=[MinValueValidator(1)], verbose_name="Cantidad")
    line_total = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Total línea")

    class Meta:
        verbose_name = "Item de pedido"
        verbose_name_plural = "Items de pedido"

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


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
