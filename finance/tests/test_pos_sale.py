from decimal import Decimal

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings

from finance.models import FinancialAccount, FinancialMovement
from finance.services.pos_sale import PosSaleError, create_pos_sale
from shop.models import (
    Brand,
    Category,
    CustomUser,
    Order,
    PaymentMethod,
    Product,
    ProductVariant,
    ShippingMethod,
)


def _grant(user, *codenames):
    ct = ContentType.objects.get_for_model(FinancialAccount)
    for code in codenames:
        user.user_permissions.add(Permission.objects.get(content_type=ct, codename=code))


class PosSaleServiceTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Cascos', slug='cascos-pos')
        self.shipping = ShippingMethod.objects.create(
            name='Retiro en bodega',
            description='Retiro',
            base_price=0,
        )
        self.cash = PaymentMethod.objects.create(name='Efectivo')
        self.mp = PaymentMethod.objects.create(name='Mercado Pago')
        self.product = Product.objects.create(
            name='Casco POS',
            sku='CASCO-POS',
            short_description='Casco',
            description='Casco',
            category=self.category,
            price=119000,
            offer_price=100000,
            cost_net=Decimal('40000'),
            stock=5,
            is_vat_affected=True,
        )

    def test_uses_published_price_and_does_not_change_catalog(self):
        order = create_pos_sale(
            processed_by=None,
            payment_method=self.cash,
            lines=[{'product_id': self.product.id, 'variant_id': None, 'quantity': 2}],
            customer_name='Lucas',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 119000)
        self.assertEqual(self.product.offer_price, 100000)
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(order.sales_channel, 'pos')
        self.assertEqual(order.status, 'confirmed')
        item = order.items.get()
        self.assertEqual(item.unit_price, 100000)
        self.assertEqual(item.line_total, 200000)
        self.assertEqual(item.gross_sale, Decimal('200000'))
        self.assertEqual(item.net_sale, Decimal('168067'))
        self.assertIsNotNone(item.finance_synced_at)
        self.assertEqual(item.list_unit_price, Decimal('119000'))
        self.assertEqual(FinancialMovement.objects.count(), 0)
        self.assertEqual(order.payments.get().status, 'approved')

    def test_rejects_mercadopago_and_over_stock(self):
        with self.assertRaises(PosSaleError):
            create_pos_sale(
                processed_by=None,
                payment_method=self.mp,
                lines=[{'product_id': self.product.id, 'quantity': 1}],
            )
        with self.assertRaises(PosSaleError):
            create_pos_sale(
                processed_by=None,
                payment_method=self.cash,
                lines=[{'product_id': self.product.id, 'quantity': 9}],
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(Order.objects.count(), 0)

    def test_variant_stock_decrements_parent_sum(self):
        self.product.stock = 0
        self.product.save(update_fields=['stock'])
        small = ProductVariant.objects.create(product=self.product, name='S', stock=2)
        ProductVariant.objects.create(product=self.product, name='M', stock=3)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        order = create_pos_sale(
            processed_by=None,
            payment_method=self.cash,
            lines=[{'product_id': self.product.id, 'variant_id': small.id, 'quantity': 2}],
        )
        small.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(small.stock, 0)
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.product.price, 119000)
        self.assertEqual(order.items.get().variant_label, 'S')


@override_settings(SECURE_SSL_REDIRECT=False)
class PosSaleViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Guantes', slug='guantes-pos')
        self.brand = Brand.objects.create(name='Shaft', slug='shaft-pos')
        self.other_cat = Category.objects.create(name='Cascos', slug='cascos-pos-ui')
        ShippingMethod.objects.create(name='Retiro', description='Retiro', base_price=0)
        self.cash = PaymentMethod.objects.create(name='Efectivo')
        self.product = Product.objects.create(
            name='Guante POS',
            sku='GUA-POS',
            short_description='Guante',
            description='Guante',
            category=self.category,
            brand=self.brand,
            price=30000,
            cost_net=Decimal('10000'),
            stock=4,
        )
        self.other = Product.objects.create(
            name='Casco distante',
            sku='CAS-DIST',
            short_description='Casco',
            description='Casco',
            category=self.other_cat,
            price=119000,
            stock=2,
        )
        self.staff = CustomUser.objects.create_user(
            email='pos@motomoto.cl',
            password='pass-12345',
            first_name='Pos',
            last_name='User',
            is_staff=True,
        )

    def test_view_permission_required(self):
        _grant(self.staff, 'view_finance')
        self.client.force_login(self.staff)
        response = self.client.get('/dashboard/finanzas/ingresos/ventas/nueva/')
        self.assertEqual(response.status_code, 302)
        posted = self.client.post(
            '/dashboard/finanzas/ingresos/ventas/nueva/',
            {'action': 'add', 'product_id': str(self.product.id), 'quantity': '1'},
        )
        self.assertEqual(posted.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(Order.objects.count(), 0)

    def test_search_filters_by_text_brand_and_category(self):
        _grant(self.staff, 'view_finance', 'add_manual_sale')
        self.client.force_login(self.staff)
        by_text = self.client.get('/dashboard/finanzas/ingresos/ventas/nueva/', {'q': 'GUA-POS'})
        self.assertEqual([p.name for p in by_text.context['matches']], ['Guante POS'])
        by_brand = self.client.get(
            '/dashboard/finanzas/ingresos/ventas/nueva/',
            {'brand': str(self.brand.id)},
        )
        self.assertEqual([p.name for p in by_brand.context['matches']], ['Guante POS'])
        by_cat = self.client.get(
            '/dashboard/finanzas/ingresos/ventas/nueva/',
            {'category': str(self.other_cat.id)},
        )
        self.assertEqual([p.name for p in by_cat.context['matches']], ['Casco distante'])

    def test_staff_with_perm_creates_sale_visible_in_ingresos(self):
        _grant(self.staff, 'view_finance', 'add_manual_sale')
        self.client.force_login(self.staff)
        get_form = self.client.get('/dashboard/finanzas/ingresos/ventas/nueva/')
        self.assertEqual(get_form.status_code, 200)
        self.assertContains(get_form, 'Registrar venta')
        self.assertContains(get_form, 'Buscar producto')
        added = self.client.post(
            '/dashboard/finanzas/ingresos/ventas/nueva/',
            {'action': 'add', 'product_id': str(self.product.id), 'quantity': '1'},
        )
        self.assertEqual(added.status_code, 302)
        response = self.client.post(
            '/dashboard/finanzas/ingresos/ventas/nueva/',
            {
                'action': 'register',
                'customer_name': 'Mostrador',
                'payment_method': str(self.cash.id),
                'discount_total': '0',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.product.price, 30000)
        order = Order.objects.get()
        self.assertEqual(order.sales_channel, 'pos')
        listing = self.client.get(
            '/dashboard/finanzas/ingresos/ventas/',
            {'channel': 'pos'},
        )
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, 'Guante POS')
        self.assertContains(listing, 'Venta física')
        self.assertContains(listing, 'Ventas netas')
        web_only = self.client.get(
            '/dashboard/finanzas/ingresos/ventas/',
            {'channel': 'web'},
        )
        self.assertNotContains(web_only, 'Guante POS')
