from datetime import date, datetime, time
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.utils import timezone

from finance.kpis import compute_sales_kpis
from finance.models import FinancialAccount
from finance.services import sync_sale_from_order
from shop.models import Category, CustomUser, Order, OrderItem, PaymentMethod, Product, ShippingMethod


@override_settings(SECURE_SSL_REDIRECT=False)
class FinanceDashboardAccessTests(TestCase):
    def setUp(self):
        self.url = '/dashboard/finanzas/'

    def test_anonymous_is_redirected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_staff_without_permission_is_blocked(self):
        user = CustomUser.objects.create_user(
            email='staff@motomoto.cl',
            password='pass-12345',
            first_name='Staff',
            last_name='User',
            is_staff=True,
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_superuser_can_open_resumen(self):
        user = CustomUser.objects.create_superuser(
            email='admin@motomoto.cl',
            password='pass-12345',
            first_name='Admin',
            last_name='User',
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resultado operativo')
        self.assertContains(response, 'Control financiero de MotoMoto')


@override_settings(SECURE_SSL_REDIRECT=False)
class KpiDateFilterTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Cascos', slug='cascos-kpi')
        shipping = ShippingMethod.objects.create(name='Retiro', description='Retiro', base_price=0)
        payment = PaymentMethod.objects.create(name='Efectivo')
        product = Product.objects.create(
            name='Casco KPI',
            short_description='Casco',
            description='Casco',
            category=category,
            price=119000,
            cost_net=Decimal('40000'),
        )
        self.shipping = shipping
        self.payment = payment
        self.product = product

    def _order_on(self, day: date):
        order = Order.objects.create(
            shipping_method=self.shipping,
            payment_method=self.payment,
            subtotal=119000,
            total=119000,
            sales_channel='web',
        )
        tz = timezone.get_current_timezone()
        when = timezone.make_aware(datetime.combine(day, time(12, 0)), tz)
        Order.objects.filter(pk=order.pk).update(created_at=when)
        order.refresh_from_db()
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=119000,
            quantity=1,
            line_total=119000,
        )
        sync_sale_from_order(order)
        return order

    def test_kpis_change_with_date_range(self):
        self._order_on(date(2026, 8, 10))
        self._order_on(date(2026, 9, 5))

        august = compute_sales_kpis(date(2026, 8, 1), date(2026, 8, 31))
        september = compute_sales_kpis(date(2026, 9, 1), date(2026, 9, 30))
        both = compute_sales_kpis(date(2026, 8, 1), date(2026, 9, 30))

        self.assertEqual(august.net_sales, Decimal('100000'))
        self.assertEqual(september.net_sales, Decimal('100000'))
        self.assertEqual(both.net_sales, Decimal('200000'))
        self.assertEqual(august.orders, 1)
        self.assertEqual(both.orders, 2)

    def test_staff_with_permission_sees_filtered_sales_list(self):
        self._order_on(date(2026, 8, 10))
        self._order_on(date(2026, 9, 5))
        user = CustomUser.objects.create_user(
            email='finanzas@motomoto.cl',
            password='pass-12345',
            first_name='Fin',
            last_name='anzas',
            is_staff=True,
        )
        perm = Permission.objects.get(
            content_type=ContentType.objects.get_for_model(FinancialAccount),
            codename='view_finance',
        )
        user.user_permissions.add(perm)
        self.client.force_login(user)
        response = self.client.get(
            '/dashboard/finanzas/ingresos/ventas/',
            {'date_from': '2026-08-01', 'date_to': '2026-08-31'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Casco KPI')
        self.assertEqual(len(response.context['page'].object_list), 1)
