from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings

from finance.kpis import compute_sales_kpis
from finance.models import FinancialAccount, FinancialMovement, OrderRefund, OrderShipment
from finance.services.pos_sale import create_pos_sale
from finance.services.refund import RefundError, record_refund
from finance.services.sale_sync import sync_sale_from_order
from finance.services.shipment import ShipmentError, upsert_shipment
from shop.models import (
    Category,
    CustomUser,
    Order,
    OrderItem,
    PaymentMethod,
    Product,
    ShippingMethod,
)


def _grant(user, *codenames):
    ct = ContentType.objects.get_for_model(FinancialAccount)
    for code in codenames:
        user.user_permissions.add(Permission.objects.get(content_type=ct, codename=code))


class ShipmentServiceTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Cascos', slug='cascos-ship')
        self.shipping = ShippingMethod.objects.create(
            name='Starken',
            description='Courier',
            base_price=3500,
        )
        self.payment = PaymentMethod.objects.create(name='Efectivo')
        self.account = FinancialAccount.objects.create(
            name='Banco flete',
            account_type=FinancialAccount.AccountType.BANK,
            opening_balance=Decimal('100000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='bank_transfers',
        )
        self.product = Product.objects.create(
            name='Casco flete',
            sku='CASCO-SHIP',
            short_description='Casco',
            description='Casco',
            category=self.category,
            price=119000,
            cost_net=Decimal('40000'),
            stock=3,
            is_vat_affected=True,
        )

    def _order(self):
        order = Order.objects.create(
            shipping_method=self.shipping,
            payment_method=self.payment,
            shipping_cost=3500,
            subtotal=119000,
            discount_total=0,
            total=122500,
            sales_channel='web',
            is_vat_affected=True,
        )
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

    def test_assumed_cost_hits_contribution_once(self):
        order = self._order()
        before = compute_sales_kpis(date(2026, 1, 1), date(2026, 12, 31))
        shipment = upsert_shipment(
            order=order,
            actual_cost=4000,
            assumed_cost=4000,
            account=self.account,
            occurred_on=date(2026, 9, 5),
            carrier='Starken',
        )
        item = order.items.get()
        self.assertEqual(item.shipping_assumed_allocated, Decimal('4000'))
        self.assertEqual(shipment.charged_amount, Decimal('3500'))
        self.assertEqual(self.account.get_current_balance(), Decimal('96000'))
        after = compute_sales_kpis(date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(after.shipping_assumed, Decimal('4000'))
        self.assertEqual(after.contribution, before.contribution - Decimal('4000'))
        upsert_shipment(
            order=order,
            actual_cost=4000,
            assumed_cost=4000,
            account=self.account,
            occurred_on=date(2026, 9, 5),
        )
        self.assertEqual(OrderShipment.objects.count(), 1)
        self.assertEqual(
            FinancialMovement.objects.filter(
                movement_type=FinancialMovement.MovementType.SHIPMENT
            ).count(),
            1,
        )
        sync_sale_from_order(order)
        item.refresh_from_db()
        self.assertEqual(item.shipping_assumed_allocated, Decimal('4000'))

    def test_cannot_change_paid_amount(self):
        order = self._order()
        upsert_shipment(
            order=order,
            actual_cost=4000,
            assumed_cost=4000,
            account=self.account,
            occurred_on=date(2026, 9, 5),
        )
        with self.assertRaises(ShipmentError):
            upsert_shipment(
                order=order,
                actual_cost=5000,
                assumed_cost=5000,
                account=self.account,
                occurred_on=date(2026, 9, 6),
            )


class RefundServiceTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Guantes', slug='guantes-ref')
        ShippingMethod.objects.create(name='Retiro en bodega', description='Retiro', base_price=0)
        self.cash = PaymentMethod.objects.create(name='Efectivo')
        self.account = FinancialAccount.objects.create(
            name='Caja devolución',
            account_type=FinancialAccount.AccountType.CASH,
            opening_balance=Decimal('200000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='cash',
        )
        self.product = Product.objects.create(
            name='Guante ref',
            sku='GUA-REF',
            short_description='Guante',
            description='Guante',
            category=self.category,
            price=30000,
            offer_price=23800,
            cost_net=Decimal('10000'),
            stock=5,
        )

    def test_refund_does_not_delete_original_sale(self):
        order = create_pos_sale(
            processed_by=None,
            payment_method=self.cash,
            lines=[{'product_id': self.product.id, 'variant_id': None, 'quantity': 2}],
        )
        item = order.items.get()
        original_net = item.net_sale
        original_qty = item.quantity
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        before = compute_sales_kpis(date(2026, 1, 1), date(2026, 12, 31))
        refund = record_refund(
            order=order,
            lines=[{'order_item_id': item.pk, 'quantity': 1}],
            occurred_on=date(2026, 9, 5),
            account=self.account,
            restores_stock=True,
        )
        item.refresh_from_db()
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(item.net_sale, original_net)
        self.assertEqual(item.quantity, original_qty)
        self.assertTrue(OrderItem.objects.filter(pk=item.pk).exists())
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(order.financial_status, 'partially_refunded')
        self.assertEqual(refund.net_amount, original_net / 2)
        after = compute_sales_kpis(date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(after.net_sales, before.net_sales - refund.net_amount)
        self.assertEqual(self.account.get_current_balance(), Decimal('200000') - refund.gross_amount)
        record_refund(
            order=order,
            lines=[{'order_item_id': item.pk, 'quantity': 1}],
            occurred_on=date(2026, 9, 5),
            restores_stock=True,
        )
        order.refresh_from_db()
        self.assertEqual(order.financial_status, 'refunded')
        with self.assertRaises(RefundError):
            record_refund(
                order=order,
                lines=[{'order_item_id': item.pk, 'quantity': 1}],
                occurred_on=date(2026, 9, 5),
            )


@override_settings(SECURE_SSL_REDIRECT=False)
class ShipmentRefundViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Accesorios', slug='acc-ship-ui')
        self.shipping = ShippingMethod.objects.create(name='Chilexpress', description='CX', base_price=2500)
        self.cash = PaymentMethod.objects.create(name='Efectivo')
        self.account = FinancialAccount.objects.create(
            name='Banco UI',
            account_type=FinancialAccount.AccountType.BANK,
            opening_balance=Decimal('80000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='bank_transfers',
        )
        self.product = Product.objects.create(
            name='Mica UI',
            sku='MICA-UI',
            short_description='Mica',
            description='Mica',
            category=self.category,
            price=20000,
            cost_net=Decimal('5000'),
            stock=4,
        )
        self.staff = CustomUser.objects.create_user(
            email='log@motomoto.cl',
            password='pass-12345',
            first_name='Log',
            last_name='User',
            is_staff=True,
        )
        self.order = Order.objects.create(
            shipping_method=self.shipping,
            payment_method=self.cash,
            shipping_cost=2500,
            subtotal=20000,
            total=22500,
            sales_channel='web',
            order_number='MM-TEST-1',
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            unit_price=20000,
            quantity=1,
            line_total=20000,
        )
        sync_sale_from_order(self.order)

    def test_shipment_post_requires_perm(self):
        _grant(self.staff, 'view_finance')
        self.client.force_login(self.staff)
        response = self.client.get('/dashboard/finanzas/gastos/envios/')
        self.assertEqual(response.status_code, 200)
        posted = self.client.post(
            '/dashboard/finanzas/gastos/envios/',
            {
                'order_number': 'MM-TEST-1',
                'actual_cost': '2500',
                'account': str(self.account.id),
                'occurred_on': '2026-09-05',
            },
        )
        self.assertEqual(posted.status_code, 302)
        self.assertEqual(OrderShipment.objects.count(), 0)

    def test_staff_registers_shipment_and_refund(self):
        _grant(self.staff, 'view_finance', 'register_expense', 'add_manual_sale')
        self.client.force_login(self.staff)
        shipped = self.client.post(
            '/dashboard/finanzas/gastos/envios/',
            {
                'order_number': 'MM-TEST-1',
                'actual_cost': '2500',
                'account': str(self.account.id),
                'occurred_on': '2026-09-05',
                'carrier': 'Chilexpress',
            },
        )
        self.assertEqual(shipped.status_code, 302)
        self.assertEqual(OrderShipment.objects.count(), 1)
        listing = self.client.get('/dashboard/finanzas/gastos/envios/')
        self.assertContains(listing, 'Chilexpress')
        looked = self.client.get('/dashboard/finanzas/ingresos/devoluciones/', {'order_number': 'MM-TEST-1'})
        self.assertEqual(looked.status_code, 200)
        self.assertContains(looked, 'Mica UI')
        item = self.order.items.get()
        refunded = self.client.post(
            '/dashboard/finanzas/ingresos/devoluciones/',
            {
                'action': 'refund',
                'order_number': 'MM-TEST-1',
                f'qty_{item.pk}': '1',
                'occurred_on': '2026-09-05',
                'restores_stock': 'on',
            },
        )
        self.assertEqual(refunded.status_code, 302)
        self.assertEqual(OrderRefund.objects.count(), 1)
        item.refresh_from_db()
        self.assertEqual(item.line_total, 20000)
        history = self.client.get(
            '/dashboard/finanzas/ingresos/devoluciones/',
            {'date_from': '2026-09-01', 'date_to': '2026-09-30'},
        )
        self.assertContains(history, 'Mica UI')
