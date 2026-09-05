from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from shop.models import Category, Order, OrderItem, PaymentMethod, Product, ShippingMethod


class OrderFinanceDefaultsTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Accesorios', slug='accesorios')
        self.shipping = ShippingMethod.objects.create(
            name='Retiro en bodega',
            description='Retiro',
            base_price=0,
        )
        self.payment = PaymentMethod.objects.create(name='Efectivo')
        self.product = Product.objects.create(
            name='Producto línea',
            short_description='Prod',
            description='Prod',
            category=self.category,
            price=119000,
            cost_net=Decimal('40000'),
        )

    def test_order_defaults_to_web_channel(self):
        order = Order.objects.create(
            shipping_method=self.shipping,
            payment_method=self.payment,
            subtotal=119000,
            total=119000,
            customer_name='Cliente Test',
            customer_email='cliente@test.cl',
        )
        self.assertEqual(order.sales_channel, 'web')
        self.assertEqual(order.financial_status, 'open')
        self.assertTrue(order.is_vat_affected)

    def test_order_item_financial_defaults_are_zero_until_sync(self):
        order = Order.objects.create(
            shipping_method=self.shipping,
            payment_method=self.payment,
            subtotal=119000,
            total=119000,
        )
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=119000,
            quantity=1,
            line_total=119000,
        )
        self.assertEqual(item.gross_sale, Decimal('0'))
        self.assertEqual(item.net_sale, Decimal('0'))
        self.assertEqual(item.vat_debit, Decimal('0'))
        self.assertTrue(item.cost_missing)
        self.assertEqual(item.allocation_method, 'net_proportional')

    def test_order_item_rejects_zero_quantity(self):
        order = Order.objects.create(
            shipping_method=self.shipping,
            payment_method=self.payment,
            subtotal=0,
            total=0,
        )
        item = OrderItem(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=0,
            quantity=0,
            line_total=0,
        )
        with transaction.atomic(), self.assertRaises(IntegrityError):
            item.save()
