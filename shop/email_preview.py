"""
Datos simulados para previsualizar plantillas de correo en el navegador (solo DEBUG).
"""
from types import SimpleNamespace

from django.templatetags.static import static
from django.utils import timezone

from shop.models import Order


def get_mock_order_email_context():
    """
    Retorna order + order_items compatibles con:
    - shop/emails/order_confirmation.html
    - shop/emails/order_notification_admin.html
    """
    shipping_method = SimpleNamespace(name="Envío a domicilio")
    payment_method = SimpleNamespace(name="Transferencia Bancaria")
    coupon = SimpleNamespace(code="MOTOMOTO10")

    class MockUser:
        email = "maria.registrada@ejemplo.cl"

        def get_full_name(self):
            return "María González"

    class MockPrimaryImage:
        def __init__(self, url):
            self.image = SimpleNamespace(url=url)

    class MockProduct:
        """Simula Product para miniatura en tabla de correo."""

        def __init__(self, image_url):
            self._image_url = image_url

        def get_primary_image(self):
            return MockPrimaryImage(self._image_url)

    class MockOrderItem:
        def __init__(self, product_name, quantity, unit_price, line_total, image_url):
            self.product_name = product_name
            self.quantity = quantity
            self.unit_price = unit_price
            self.line_total = line_total
            self.product = MockProduct(image_url)

    class MockOrder:
        id = 42

        def __init__(self):
            self.created_at = timezone.now()
            self.customer_name = "Juan Pérez"
            self.customer_email = "juan.perez@ejemplo.cl"
            self.customer_phone = "+56 9 8765 4321"
            self.status = "realized"
            self.shipping_method = shipping_method
            self.shipping_region = "Región Metropolitana de Santiago"
            self.shipping_comuna = "Puente Alto"
            self.shipping_address = "Av. Concha y Toro 1234, Casa B"
            self.payment_method = payment_method
            self.subtotal = 189_990
            self.discount_total = 18_999
            self.shipping_cost = 3_000
            self.total = 173_991
            self.coupon = coupon
            self.user = MockUser()

        @property
        def order_number(self):
            return "42JP2025"

        def get_status_display(self):
            return dict(Order.STATUS_CHOICES).get(self.status, self.status)

    order = MockOrder()

    placeholder = static("img/placeholder.webp")

    order_items = [
        MockOrderItem(
            "Casco SHAFT 502 Negris Talla M",
            1,
            125_000,
            125_000,
            placeholder,
        ),
        MockOrderItem(
            "Candado KOVIX KT6 Verde",
            2,
            32_495,
            64_990,
            placeholder,
        ),
    ]

    return {"order": order, "order_items": order_items}
