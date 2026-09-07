from datetime import date, datetime, time
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.utils import timezone

from finance.balances import ledger_rows, tax_snapshot
from finance.kpis import account_balance_on
from finance.models import ExpenseCategory, FinancialAccount
from finance.services.expense import register_expense
from finance.services.financing import register_contribution
from finance.services.purchase import register_purchase
from finance.services.sale_sync import sync_sale_from_order
from shop.models import Category, CustomUser, Order, OrderItem, PaymentMethod, Product, ShippingMethod


def _grant(user, *codenames):
    ct = ContentType.objects.get_for_model(FinancialAccount)
    for code in codenames:
        user.user_permissions.add(Permission.objects.get(content_type=ct, codename=code))


@override_settings(SECURE_SSL_REDIRECT=False)
class TaxSnapshotTests(TestCase):
    def setUp(self):
        self.shop_cat = Category.objects.create(name='Cascos', slug='cascos-tax')
        self.shipping = ShippingMethod.objects.create(name='Retiro', description='Retiro', base_price=0)
        self.payment = PaymentMethod.objects.create(name='Efectivo')
        self.product = Product.objects.create(
            name='Casco IVA',
            sku='CASCO-TAX',
            short_description='Casco',
            description='Casco',
            category=self.shop_cat,
            price=119000,
            cost_net=Decimal('40000'),
            cost_gross=Decimal('47600'),
            is_vat_affected=True,
        )
        self.cash = FinancialAccount.objects.create(
            name='Caja local',
            account_type=FinancialAccount.AccountType.CASH,
            opening_balance=Decimal('200000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='cash',
        )
        self.bank = FinancialAccount.objects.create(
            name='Banco IVA',
            account_type=FinancialAccount.AccountType.BANK,
            opening_balance=Decimal('500000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='bank_transfers',
        )
        self.opex_cat = ExpenseCategory.objects.get(slug='publicidad')

    def _sale_on(self, day: date, *, channel='web'):
        order = Order.objects.create(
            shipping_method=self.shipping,
            payment_method=self.payment,
            subtotal=119000,
            total=119000,
            sales_channel=channel,
            is_vat_affected=True,
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

    def test_sale_119000_debit_19000(self):
        self._sale_on(date(2026, 9, 5))
        tax = tax_snapshot(date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(tax['vat_debit'], Decimal('19000'))
        self.assertEqual(tax['vat_credit'], Decimal('0'))
        self.assertEqual(tax['vat_net'], Decimal('19000'))

    def test_purchase_and_expense_credits_reduce_net(self):
        self._sale_on(date(2026, 9, 5))
        register_purchase(
            account=self.bank,
            supplier='Proveedor IVA',
            lines=[{
                'product_id': self.product.id,
                'quantity': 1,
                'unit_cost_gross': 119000,
            }],
            occurred_on=date(2026, 9, 5),
            updates_stock=False,
            updates_catalog_cost=False,
        )
        register_expense(
            category=self.opex_cat,
            account=self.bank,
            vendor='Meta',
            description='Pauta septiembre',
            amount=119000,
            occurred_on=date(2026, 9, 5),
            is_vat_affected=True,
        )
        tax = tax_snapshot(date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(tax['vat_debit'], Decimal('19000'))
        self.assertEqual(tax['purchase_credit'], Decimal('19000'))
        self.assertEqual(tax['expense_credit'], Decimal('19000'))
        self.assertEqual(tax['vat_credit'], Decimal('38000'))
        self.assertEqual(tax['vat_net'], Decimal('-19000'))

    def test_tax_respects_date_filter(self):
        self._sale_on(date(2026, 8, 10))
        register_purchase(
            account=self.bank,
            supplier='Proveedor agosto no',
            lines=[{
                'product_id': self.product.id,
                'quantity': 1,
                'unit_cost_gross': 119000,
            }],
            occurred_on=date(2026, 9, 5),
            updates_stock=False,
            updates_catalog_cost=False,
        )
        august = tax_snapshot(date(2026, 8, 1), date(2026, 8, 31))
        september = tax_snapshot(date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(august['vat_debit'], Decimal('19000'))
        self.assertEqual(august['vat_credit'], Decimal('0'))
        self.assertEqual(september['vat_debit'], Decimal('0'))
        self.assertEqual(september['purchase_credit'], Decimal('19000'))
        self.assertEqual(september['vat_net'], Decimal('-19000'))


@override_settings(SECURE_SSL_REDIRECT=False)
class CashLedgerTests(TestCase):
    def setUp(self):
        self.cash = FinancialAccount.objects.create(
            name='Caja mostrador',
            account_type=FinancialAccount.AccountType.CASH,
            opening_balance=Decimal('200000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='cash',
        )
        self.bank = FinancialAccount.objects.create(
            name='Banco no caja',
            account_type=FinancialAccount.AccountType.BANK,
            opening_balance=Decimal('800000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='bank_transfers',
        )

    def test_cash_closing_matches_derived_balance(self):
        register_contribution(
            account=self.cash,
            amount=50000,
            occurred_on=date(2026, 9, 5),
            counterparty='Socio',
        )
        ledger = ledger_rows(
            date(2026, 9, 1),
            date(2026, 9, 30),
            account_types=[FinancialAccount.AccountType.CASH],
        )
        self.assertEqual(len(ledger['rows']), 1)
        row = ledger['rows'][0]
        self.assertEqual(row['opening'], Decimal('200000'))
        self.assertEqual(row['inflow'], Decimal('50000'))
        self.assertEqual(row['outflow'], Decimal('0'))
        self.assertEqual(row['closing'], Decimal('250000'))
        self.assertEqual(row['closing'], self.cash.get_current_balance())
        self.assertEqual(row['closing'], account_balance_on(self.cash, date(2026, 9, 30)))
        banks = ledger_rows(
            date(2026, 9, 1),
            date(2026, 9, 30),
            account_types=[FinancialAccount.AccountType.BANK, FinancialAccount.AccountType.DIGITAL],
        )
        self.assertEqual(banks['closing'], Decimal('800000'))
        self.assertEqual(banks['inflow'], Decimal('0'))


@override_settings(SECURE_SSL_REDIRECT=False)
class BalancesViewTests(TestCase):
    def setUp(self):
        self.url = '/dashboard/finanzas/saldos/'
        self.user = CustomUser.objects.create_user(
            email='saldos@motomoto.cl',
            password='pass-12345',
            first_name='Sal',
            last_name='Dos',
            is_staff=True,
        )
        self.staff = CustomUser.objects.create_user(
            email='staff-saldos@motomoto.cl',
            password='pass-12345',
            first_name='Staff',
            last_name='User',
            is_staff=True,
        )

    def test_anonymous_is_redirected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_staff_without_permission_is_blocked(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_view_finance_opens_panels(self):
        _grant(self.user, 'view_finance')
        self.client.force_login(self.user)
        caja = self.client.get(self.url, {'date_from': '2026-09-01', 'date_to': '2026-09-30'})
        self.assertEqual(caja.status_code, 200)
        self.assertContains(caja, 'Caja')
        self.assertContains(caja, 'derivado, no editable')
        taxes = self.client.get(
            self.url,
            {'date_from': '2026-09-01', 'date_to': '2026-09-30', 'panel': 'impuestos'},
        )
        self.assertEqual(taxes.status_code, 200)
        self.assertContains(taxes, 'IVA débito')
        self.assertContains(taxes, 'No es una declaración SII')
        profit = self.client.get(
            self.url,
            {'date_from': '2026-09-01', 'date_to': '2026-09-30', 'panel': 'rentabilidad'},
        )
        self.assertEqual(profit.status_code, 200)
        self.assertContains(profit, 'Resultado operativo')
        self.assertContains(profit, 'De la venta al resultado')
