from datetime import date, datetime, time
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from finance.alerts import finance_alerts
from finance.models import ExpenseCategory, FinancialAccount, FinancialMovement
from finance.series import sales_evolution
from finance.services.backfill import backfill_unsynced_sales, unsynced_orders_qs
from finance.services.expense import register_expense
from finance.services.refund import record_refund
from finance.services.sale_sync import sync_sale_from_order
from shop.models import Category, CustomUser, Order, OrderItem, PaymentMethod, Product, ShippingMethod


def _grant(user, *codenames):
    ct = ContentType.objects.get_for_model(FinancialAccount)
    for code in codenames:
        user.user_permissions.add(Permission.objects.get(content_type=ct, codename=code))


class OpsBase(TestCase):
    def setUp(self):
        self.shop_cat = Category.objects.create(name='Cascos', slug='cascos-ops')
        self.shipping = ShippingMethod.objects.create(name='Retiro', description='Retiro', base_price=0)
        self.payment = PaymentMethod.objects.create(name='Efectivo')
        self.product = Product.objects.create(
            name='Casco ops',
            sku='CASCO-OPS',
            short_description='Casco',
            description='Casco',
            category=self.shop_cat,
            price=119000,
            cost_net=Decimal('40000'),
            cost_gross=Decimal('47600'),
            stock=4,
            is_active=True,
            is_vat_affected=True,
        )

    def _order_on(self, day: date, *, cost_net=None, sync=True, status='realized'):
        if cost_net is not None:
            self.product.cost_net = Decimal(str(cost_net))
            self.product.save(update_fields=['cost_net'])
        order = Order.objects.create(
            shipping_method=self.shipping,
            payment_method=self.payment,
            subtotal=119000,
            total=119000,
            sales_channel='web',
            is_vat_affected=True,
            status=status,
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
        if sync:
            sync_sale_from_order(order)
        return order


@override_settings(SECURE_SSL_REDIRECT=False)
class AlertTests(OpsBase):
    def test_missing_cost_zero_stock_vat_and_negative_account(self):
        self._order_on(date(2026, 9, 5), cost_net=0)
        self.product.stock = 0
        self.product.save(update_fields=['stock'])
        account = FinancialAccount.objects.create(
            name='Caja flaca',
            account_type=FinancialAccount.AccountType.CASH,
            opening_balance=Decimal('10000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='cash',
        )
        register_expense(
            category=ExpenseCategory.objects.get(slug='publicidad'),
            account=account,
            vendor='Meta',
            description='Pauta',
            amount=50000,
            occurred_on=date(2026, 9, 5),
            is_vat_affected=False,
        )
        alerts = finance_alerts(date(2026, 9, 1), date(2026, 9, 30))
        texts = [item['text'] for item in alerts]
        self.assertTrue(any('sin costo histórico' in text for text in texts))
        self.assertTrue(any('sin stock' in text for text in texts))
        self.assertTrue(any('IVA estimado a pagar' in text for text in texts))
        self.assertTrue(any('saldo negativo' in text for text in texts))
        vat = next(item for item in alerts if 'IVA estimado' in item['text'])
        self.assertIn('panel=impuestos', vat['href'])
        missing = next(item for item in alerts if 'sin costo' in item['text'])
        self.assertIn('missing_cost=1', missing['href'])

    def test_no_vat_alert_without_sales(self):
        alerts = finance_alerts(date(2026, 9, 1), date(2026, 9, 30))
        self.assertFalse(any('IVA estimado' in item['text'] for item in alerts))


@override_settings(SECURE_SSL_REDIRECT=False)
class EvolutionTests(OpsBase):
    def test_daily_series_matches_sales(self):
        self._order_on(date(2026, 9, 1))
        self._order_on(date(2026, 9, 5))
        series = sales_evolution(date(2026, 9, 1), date(2026, 9, 5))
        self.assertEqual(series['grain'], 'day')
        self.assertTrue(series['has_values'])
        self.assertEqual(len(series['points']), 5)
        by_day = {point['key']: point['net'] for point in series['points']}
        self.assertEqual(by_day[date(2026, 9, 1)], Decimal('100000'))
        self.assertEqual(by_day[date(2026, 9, 5)], Decimal('100000'))
        self.assertEqual(by_day[date(2026, 9, 2)], Decimal('0'))
        self.assertEqual(sum((point['net'] for point in series['points']), Decimal('0')), Decimal('200000'))

    def test_refunds_subtract_without_sqlite_trunc(self):
        order = self._order_on(date(2026, 9, 5))
        item = order.items.get()
        record_refund(
            order=order,
            lines=[{'order_item_id': item.pk, 'quantity': 1}],
            occurred_on=date(2026, 9, 5),
            restores_stock=False,
        )
        series = sales_evolution(date(2026, 9, 1), date(2026, 9, 5))
        by_day = {point['key']: point['net'] for point in series['points']}
        self.assertEqual(by_day[date(2026, 9, 5)], Decimal('0'))

    def test_long_range_uses_weeks(self):
        series = sales_evolution(date(2026, 8, 1), date(2026, 8, 31))
        self.assertEqual(series['grain'], 'week')


@override_settings(SECURE_SSL_REDIRECT=False)
class BackfillTests(OpsBase):
    def test_dry_run_does_not_write(self):
        order = self._order_on(date(2026, 9, 5), sync=False)
        result = backfill_unsynced_sales(dry_run=True)
        order.items.get().refresh_from_db()
        self.assertEqual(result['found'], 1)
        self.assertEqual(result['synced'], 0)
        self.assertIsNone(order.items.get().finance_synced_at)
        self.assertEqual(FinancialMovement.objects.count(), 0)

    def test_backfill_freezes_cost_without_treasury(self):
        order = self._order_on(date(2026, 9, 5), cost_net=40000, sync=False)
        self.product.cost_net = Decimal('47000')
        self.product.save(update_fields=['cost_net'])
        result = backfill_unsynced_sales()
        item = order.items.get()
        item.refresh_from_db()
        self.assertEqual(result['synced'], 1)
        self.assertIsNotNone(item.finance_synced_at)
        self.assertEqual(item.unit_cost_net_snapshot, Decimal('47000'))
        self.assertEqual(item.net_sale, Decimal('100000'))
        self.assertEqual(FinancialMovement.objects.count(), 0)
        self.product.cost_net = Decimal('99000')
        self.product.save(update_fields=['cost_net'])
        backfill_unsynced_sales()
        item.refresh_from_db()
        self.assertEqual(item.unit_cost_net_snapshot, Decimal('47000'))
        self.assertEqual(unsynced_orders_qs().count(), 0)

    def test_skips_cancelled_orders(self):
        self._order_on(date(2026, 9, 5), sync=False, status='cancelled')
        self.assertEqual(unsynced_orders_qs().count(), 0)
        result = backfill_unsynced_sales()
        self.assertEqual(result['synced'], 0)

    def test_management_command_dry_run(self):
        self._order_on(date(2026, 9, 5), sync=False)
        out = StringIO()
        call_command('backfill_finance_sales', '--dry-run', stdout=out)
        self.assertIn('pendientes', out.getvalue())
        self.assertIsNone(OrderItem.objects.get().finance_synced_at)


@override_settings(SECURE_SSL_REDIRECT=False)
class OpsViewTests(OpsBase):
    def setUp(self):
        super().setUp()
        self.user = CustomUser.objects.create_user(
            email='ops@motomoto.cl',
            password='pass-12345',
            first_name='Ops',
            last_name='User',
            is_staff=True,
        )
        _grant(self.user, 'view_finance')
        self.client.force_login(self.user)

    def test_resumen_shows_evolution_and_alert(self):
        self._order_on(date(2026, 9, 5), cost_net=0)
        response = self.client.get(
            '/dashboard/finanzas/',
            {'date_from': '2026-09-01', 'date_to': '2026-09-30'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Evolución de ventas netas')
        self.assertContains(response, 'sin costo histórico')
        self.assertContains(response, 'evo-chart')

    def test_sales_missing_cost_filter(self):
        cheap = self._order_on(date(2026, 9, 5), cost_net=0)
        self.product.cost_net = Decimal('40000')
        self.product.save(update_fields=['cost_net'])
        priced = Order.objects.create(
            shipping_method=self.shipping,
            payment_method=self.payment,
            subtotal=119000,
            total=119000,
            sales_channel='web',
        )
        OrderItem.objects.create(
            order=priced,
            product=self.product,
            product_name=self.product.name,
            unit_price=119000,
            quantity=1,
            line_total=119000,
        )
        sync_sale_from_order(priced)
        response = self.client.get(
            '/dashboard/finanzas/ingresos/ventas/',
            {'date_from': '2026-01-01', 'date_to': '2026-12-31', 'missing_cost': '1'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sin costo histórico')
        ids = [item.order_id for item in response.context['page'].object_list]
        self.assertIn(cheap.id, ids)
        self.assertNotIn(priced.id, ids)
