from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings

from finance.kpis import compute_sales_kpis
from finance.models import (
    ExpenseCategory,
    FinancialAccount,
    FinancialMovement,
    OperationalExpense,
)
from finance.services.expense import ExpenseError, create_expense_category, register_expense
from finance.services.financing import register_contribution
from finance.services.purchase import register_purchase
from shop.models import Category, CustomUser, Order, Product


def _grant(user, *codenames):
    ct = ContentType.objects.get_for_model(FinancialAccount)
    for code in codenames:
        user.user_permissions.add(Permission.objects.get(content_type=ct, codename=code))


class ExpenseServiceTests(TestCase):
    def setUp(self):
        self.account = FinancialAccount.objects.create(
            name='Banco opex',
            account_type=FinancialAccount.AccountType.BANK,
            opening_balance=Decimal('500000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='bank_transfers',
        )
        self.category = ExpenseCategory.objects.get(slug='publicidad')

    def test_vat_expense_hits_opex_not_sales(self):
        item = register_expense(
            category=self.category,
            account=self.account,
            vendor='Meta',
            description='Campañas septiembre',
            amount=119000,
            occurred_on=date(2026, 9, 5),
            is_vat_affected=True,
        )
        self.assertEqual(item.net_amount, Decimal('100000'))
        self.assertEqual(item.vat_credit, Decimal('19000'))
        self.assertEqual(self.account.get_current_balance(), Decimal('381000'))
        self.assertEqual(Order.objects.count(), 0)
        kpis = compute_sales_kpis(date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(kpis.net_sales, Decimal('0'))
        self.assertEqual(kpis.opex, Decimal('100000'))
        self.assertEqual(kpis.operating_result, Decimal('-100000'))
        self.assertEqual(
            FinancialMovement.objects.filter(
                movement_type=FinancialMovement.MovementType.EXPENSE
            ).count(),
            1,
        )

    def test_purchase_and_aporte_are_not_opex(self):
        shop_cat = Category.objects.create(name='Cascos', slug='cascos-opex')
        product = Product.objects.create(
            name='Casco opex',
            sku='CASCO-OPEX',
            short_description='Casco',
            description='Casco',
            category=shop_cat,
            price=119000,
            cost_net=Decimal('40000'),
            cost_gross=Decimal('47600'),
            stock=1,
        )
        register_purchase(
            account=self.account,
            supplier='Proveedor',
            lines=[{
                'product_id': product.id,
                'variant_id': None,
                'quantity': 1,
                'unit_cost_gross': 47600,
            }],
            occurred_on=date(2026, 9, 5),
            updates_stock=False,
            updates_catalog_cost=False,
        )
        register_contribution(
            account=self.account,
            amount=20000,
            occurred_on=date(2026, 9, 5),
            counterparty='Socio',
        )
        kpis = compute_sales_kpis(date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(kpis.opex, Decimal('0'))
        self.assertEqual(kpis.net_sales, Decimal('0'))
        self.assertEqual(OperationalExpense.objects.count(), 0)

    def test_requires_active_category_and_amount(self):
        self.category.is_active = False
        self.category.save(update_fields=['is_active'])
        with self.assertRaises(ExpenseError):
            register_expense(
                category=self.category,
                account=self.account,
                vendor='Meta',
                description='Ads',
                amount=1000,
                occurred_on=date(2026, 9, 5),
            )
        with self.assertRaises(ExpenseError):
            create_expense_category(name='Publicidad', kind=ExpenseCategory.Kind.ADS)


@override_settings(SECURE_SSL_REDIRECT=False)
class ExpenseViewTests(TestCase):
    def setUp(self):
        self.account = FinancialAccount.objects.create(
            name='Caja opex',
            account_type=FinancialAccount.AccountType.CASH,
            opening_balance=Decimal('100000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='cash',
        )
        self.category = ExpenseCategory.objects.get(slug='servicios')
        self.staff = CustomUser.objects.create_user(
            email='opex@motomoto.cl',
            password='pass-12345',
            first_name='Opex',
            last_name='User',
            is_staff=True,
        )

    def test_view_without_register_cannot_post(self):
        _grant(self.staff, 'view_finance')
        self.client.force_login(self.staff)
        response = self.client.get('/dashboard/finanzas/gastos/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gastos')
        posted = self.client.post(
            '/dashboard/finanzas/gastos/',
            {
                'action': 'create',
                'category': str(self.category.id),
                'vendor': 'Enel',
                'description': 'Luz',
                'amount': '11900',
                'account': str(self.account.id),
                'occurred_on': '2026-09-05',
                'is_vat_affected': 'on',
            },
        )
        self.assertEqual(posted.status_code, 302)
        self.assertEqual(OperationalExpense.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)

    def test_staff_with_perm_registers_expense_and_category(self):
        _grant(self.staff, 'view_finance', 'register_expense')
        self.client.force_login(self.staff)
        created_cat = self.client.post(
            '/dashboard/finanzas/gastos/',
            {'action': 'add_category', 'name': 'Meta Ads', 'kind': 'ads'},
        )
        self.assertEqual(created_cat.status_code, 302)
        ads = ExpenseCategory.objects.get(name='Meta Ads')
        self.assertEqual(ads.kind, ExpenseCategory.Kind.ADS)
        response = self.client.post(
            '/dashboard/finanzas/gastos/',
            {
                'action': 'create',
                'category': str(ads.id),
                'vendor': 'Meta',
                'description': 'Campañas',
                'amount': '11900',
                'account': str(self.account.id),
                'occurred_on': '2026-09-05',
                'is_vat_affected': 'on',
            },
        )
        self.assertEqual(response.status_code, 302)
        item = OperationalExpense.objects.get()
        self.assertEqual(item.net_amount, Decimal('10000'))
        self.assertEqual(self.account.get_current_balance(), Decimal('88100'))
        listing = self.client.get(
            '/dashboard/finanzas/gastos/',
            {'date_from': '2026-09-01', 'date_to': '2026-09-30'},
        )
        self.assertContains(listing, 'Campañas')
        self.assertContains(listing, 'Meta Ads')
        resumen = self.client.get(
            '/dashboard/finanzas/',
            {'date_from': '2026-09-01', 'date_to': '2026-09-30'},
        )
        self.assertContains(resumen, 'Gastos operacionales')
        self.assertEqual(resumen.context['opex']['value'], Decimal('10000'))
        self.assertEqual(Order.objects.count(), 0)
