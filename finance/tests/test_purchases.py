from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings

from finance.kpis import compute_sales_kpis
from finance.models import FinancialAccount, FinancialMovement, MerchandisePurchase
from finance.services.purchase import PurchaseError, register_purchase
from finance.services.sale_sync import sync_sale_from_order
from shop.models import (
    Brand,
    Category,
    CustomUser,
    Order,
    OrderItem,
    PaymentMethod,
    Product,
    ProductVariant,
    ShippingMethod,
)


def _grant(user, *codenames):
    ct = ContentType.objects.get_for_model(FinancialAccount)
    for code in codenames:
        user.user_permissions.add(Permission.objects.get(content_type=ct, codename=code))


class PurchaseServiceTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Cascos', slug='cascos-buy')
        self.account = FinancialAccount.objects.create(
            name='Banco compras',
            account_type=FinancialAccount.AccountType.BANK,
            opening_balance=Decimal('500000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='bank_transfers',
        )
        self.product = Product.objects.create(
            name='Casco compra',
            sku='CASCO-BUY',
            short_description='Casco',
            description='Casco',
            category=self.category,
            price=119000,
            offer_price=100000,
            cost_net=Decimal('40000'),
            cost_gross=Decimal('47600'),
            stock=2,
            is_vat_affected=True,
        )

    def _line(self, quantity=3, unit_cost_gross=59500, variant_id=None):
        return {
            'product_id': self.product.id,
            'variant_id': variant_id,
            'quantity': quantity,
            'unit_cost_gross': unit_cost_gross,
        }

    def test_stock_flag_on_increases_stock_and_pays_treasury(self):
        purchase = register_purchase(
            account=self.account,
            supplier='Proveedor Uno',
            lines=[self._line()],
            occurred_on=date(2026, 9, 5),
            updates_stock=True,
            updates_catalog_cost=True,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(self.product.cost_net, Decimal('50000'))
        self.assertEqual(self.product.cost_gross, Decimal('59500'))
        self.assertEqual(self.product.price, 119000)
        self.assertEqual(self.product.offer_price, 100000)
        self.assertEqual(self.account.get_current_balance(), Decimal('321500'))
        self.assertEqual(purchase.gross_total, Decimal('178500'))
        self.assertEqual(purchase.vat_credit, Decimal('28500'))
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(
            FinancialMovement.objects.filter(
                movement_type=FinancialMovement.MovementType.PURCHASE,
                direction=FinancialMovement.Direction.OUT,
            ).count(),
            1,
        )
        kpis = compute_sales_kpis(date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(kpis.net_sales, Decimal('0'))
        self.assertEqual(kpis.opex, Decimal('0'))

    def test_stock_flag_off_does_not_change_inventory(self):
        register_purchase(
            account=self.account,
            supplier='Proveedor Dos',
            lines=[self._line(quantity=4)],
            occurred_on=date(2026, 9, 5),
            updates_stock=False,
            updates_catalog_cost=False,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.assertEqual(self.product.cost_net, Decimal('40000'))
        self.assertEqual(self.product.cost_gross, Decimal('47600'))
        self.assertEqual(self.product.price, 119000)
        self.assertEqual(self.account.get_current_balance(), Decimal('262000'))
        self.assertEqual(Order.objects.count(), 0)

    def test_catalog_cost_change_does_not_rewrite_sale_snapshot(self):
        shipping = ShippingMethod.objects.create(name='Retiro', description='Retiro', base_price=0)
        payment = PaymentMethod.objects.create(name='Efectivo')
        order = Order.objects.create(
            shipping_method=shipping,
            payment_method=payment,
            shipping_cost=0,
            subtotal=119000,
            discount_total=0,
            total=119000,
            sales_channel='web',
            is_vat_affected=True,
        )
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=119000,
            quantity=1,
            line_total=119000,
        )
        sync_sale_from_order(order)
        item.refresh_from_db()
        self.assertEqual(item.unit_cost_net_snapshot, Decimal('40000'))
        register_purchase(
            account=self.account,
            supplier='Proveedor Tres',
            lines=[self._line(quantity=1, unit_cost_gross=59500)],
            occurred_on=date(2026, 9, 5),
            updates_stock=True,
            updates_catalog_cost=True,
        )
        item.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(item.unit_cost_net_snapshot, Decimal('40000'))
        self.assertEqual(self.product.cost_net, Decimal('50000'))
        self.assertEqual(self.product.price, 119000)
        kpis = compute_sales_kpis(date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(kpis.net_sales, item.net_sale)
        self.assertEqual(kpis.opex, Decimal('0'))

    def test_variant_stock_increments_parent_sum(self):
        self.product.stock = 0
        self.product.save(update_fields=['stock'])
        small = ProductVariant.objects.create(product=self.product, name='S', stock=1)
        ProductVariant.objects.create(product=self.product, name='M', stock=2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        register_purchase(
            account=self.account,
            supplier='Proveedor Tallas',
            lines=[self._line(quantity=2, variant_id=small.id)],
            occurred_on=date(2026, 9, 5),
            updates_stock=True,
            updates_catalog_cost=False,
        )
        small.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(small.stock, 3)
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(self.product.price, 119000)
        self.assertEqual(self.product.cost_net, Decimal('40000'))

    def test_requires_variant_to_add_stock_when_product_has_options(self):
        ProductVariant.objects.create(product=self.product, name='S', stock=1)
        with self.assertRaises(PurchaseError):
            register_purchase(
                account=self.account,
                supplier='Proveedor',
                lines=[self._line(quantity=1)],
                occurred_on=date(2026, 9, 5),
                updates_stock=True,
            )
        self.assertEqual(MerchandisePurchase.objects.count(), 0)
        self.assertEqual(self.account.get_current_balance(), Decimal('500000'))


@override_settings(SECURE_SSL_REDIRECT=False)
class PurchaseViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Guantes', slug='guantes-buy')
        self.brand = Brand.objects.create(name='Shaft', slug='shaft-buy')
        self.other_cat = Category.objects.create(name='Cascos', slug='cascos-buy-ui')
        self.account = FinancialAccount.objects.create(
            name='Caja compras',
            account_type=FinancialAccount.AccountType.CASH,
            opening_balance=Decimal('200000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='cash',
        )
        self.product = Product.objects.create(
            name='Guante compra',
            sku='GUA-BUY',
            short_description='Guante',
            description='Guante',
            category=self.category,
            brand=self.brand,
            price=30000,
            cost_net=Decimal('10000'),
            cost_gross=Decimal('11900'),
            stock=4,
        )
        self.other = Product.objects.create(
            name='Casco distante compra',
            sku='CAS-BUY',
            short_description='Casco',
            description='Casco',
            category=self.other_cat,
            price=119000,
            stock=2,
        )
        self.staff = CustomUser.objects.create_user(
            email='buy@motomoto.cl',
            password='pass-12345',
            first_name='Buy',
            last_name='User',
            is_staff=True,
        )

    def test_view_without_manage_cannot_post(self):
        _grant(self.staff, 'view_finance')
        self.client.force_login(self.staff)
        response = self.client.get('/dashboard/finanzas/compras/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Compras')
        posted = self.client.post(
            '/dashboard/finanzas/compras/',
            {'action': 'add', 'product_id': str(self.product.id), 'quantity': '1', 'unit_cost_gross': '11900'},
        )
        self.assertEqual(posted.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(MerchandisePurchase.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)

    def test_search_filters_by_text_brand_and_category(self):
        _grant(self.staff, 'view_finance', 'manage_purchases')
        self.client.force_login(self.staff)
        by_text = self.client.get('/dashboard/finanzas/compras/', {'q': 'GUA-BUY'})
        self.assertEqual([p.name for p in by_text.context['matches']], ['Guante compra'])
        by_brand = self.client.get('/dashboard/finanzas/compras/', {'brand': str(self.brand.id)})
        self.assertEqual([p.name for p in by_brand.context['matches']], ['Guante compra'])
        by_cat = self.client.get('/dashboard/finanzas/compras/', {'category': str(self.other_cat.id)})
        self.assertEqual([p.name for p in by_cat.context['matches']], ['Casco distante compra'])

    def test_staff_with_perm_registers_purchase(self):
        _grant(self.staff, 'view_finance', 'manage_purchases')
        self.client.force_login(self.staff)
        get_form = self.client.get('/dashboard/finanzas/compras/')
        self.assertEqual(get_form.status_code, 200)
        self.assertContains(get_form, 'Registrar compra')
        added = self.client.post(
            '/dashboard/finanzas/compras/',
            {
                'action': 'add',
                'product_id': str(self.product.id),
                'quantity': '2',
                'unit_cost_gross': '11900',
            },
        )
        self.assertEqual(added.status_code, 302)
        response = self.client.post(
            '/dashboard/finanzas/compras/',
            {
                'action': 'register',
                'supplier': 'Distribuidora Sur',
                'account': str(self.account.id),
                'occurred_on': '2026-09-05',
                'updates_stock': 'on',
                'updates_catalog_cost': 'on',
                'is_vat_affected': 'on',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 6)
        self.assertEqual(self.product.price, 30000)
        purchase = MerchandisePurchase.objects.get()
        self.assertEqual(purchase.supplier, 'Distribuidora Sur')
        self.assertEqual(purchase.gross_total, Decimal('23800'))
        listing = self.client.get('/dashboard/finanzas/compras/')
        self.assertContains(listing, 'Distribuidora Sur')
        self.assertContains(listing, 'Guante compra')
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.account.get_current_balance(), Decimal('176200'))
