from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings

from finance.kpis import compute_sales_kpis
from finance.models import FinancialAccount, FinancialMovement, Financing
from finance.services.financing import FinancingError, register_contribution, register_loan, repay_loan
from shop.models import CustomUser, Order


def _grant(user, *codenames):
    ct = ContentType.objects.get_for_model(FinancialAccount)
    for code in codenames:
        user.user_permissions.add(Permission.objects.get(content_type=ct, codename=code))


class FinancingServiceTests(TestCase):
    def setUp(self):
        self.account = FinancialAccount.objects.create(
            name='Banco',
            account_type=FinancialAccount.AccountType.BANK,
            opening_balance=Decimal('100000'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='bank_transfers',
        )

    def test_contribution_increases_cash_not_sales(self):
        item = register_contribution(
            account=self.account,
            amount=50000,
            occurred_on=date(2026, 9, 5),
            counterparty='Socio',
        )
        self.assertEqual(item.kind, Financing.Kind.CONTRIBUTION)
        self.assertEqual(self.account.get_current_balance(), Decimal('150000'))
        self.assertEqual(Order.objects.count(), 0)
        kpis = compute_sales_kpis(date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(kpis.net_sales, Decimal('0'))
        self.assertEqual(item.outstanding(), Decimal('0'))

    def test_loan_then_repay_tracks_outstanding(self):
        loan = register_loan(
            account=self.account,
            amount=80000,
            occurred_on=date(2026, 9, 1),
            counterparty='Banco Estado',
        )
        self.assertEqual(self.account.get_current_balance(), Decimal('180000'))
        self.assertEqual(loan.outstanding(), Decimal('80000'))
        repay_loan(
            financing=loan,
            account=self.account,
            amount=30000,
            occurred_on=date(2026, 9, 5),
        )
        self.assertEqual(self.account.get_current_balance(), Decimal('150000'))
        self.assertEqual(loan.outstanding(), Decimal('50000'))
        with self.assertRaises(FinancingError):
            repay_loan(
                financing=loan,
                account=self.account,
                amount=90000,
                occurred_on=date(2026, 9, 6),
            )
        kpis = compute_sales_kpis(date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(kpis.net_sales, Decimal('0'))
        self.assertEqual(
            FinancialMovement.objects.filter(
                movement_type=FinancialMovement.MovementType.LOAN_REPAYMENT
            ).count(),
            1,
        )

    def test_cannot_repay_contribution(self):
        aporte = register_contribution(
            account=self.account,
            amount=10000,
            occurred_on=date(2026, 9, 5),
            counterparty='Socio',
        )
        with self.assertRaises(FinancingError):
            repay_loan(
                financing=aporte,
                account=self.account,
                amount=1000,
                occurred_on=date(2026, 9, 5),
            )


@override_settings(SECURE_SSL_REDIRECT=False)
class FinancingViewTests(TestCase):
    def setUp(self):
        self.account = FinancialAccount.objects.create(
            name='Caja',
            account_type=FinancialAccount.AccountType.CASH,
            opening_balance=Decimal('0'),
            opening_balance_date=date(2026, 1, 1),
            ledger_role='cash',
        )
        self.staff = CustomUser.objects.create_user(
            email='fin@motomoto.cl',
            password='pass-12345',
            first_name='Fin',
            last_name='User',
            is_staff=True,
        )

    def test_view_without_manage_cannot_post(self):
        _grant(self.staff, 'view_finance')
        self.client.force_login(self.staff)
        response = self.client.get('/dashboard/finanzas/ingresos/financiamiento/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Financiamiento')
        posted = self.client.post(
            '/dashboard/finanzas/ingresos/financiamiento/',
            {
                'action': 'create',
                'kind': 'contribution',
                'counterparty': 'Socio',
                'amount': '10000',
                'account': str(self.account.id),
                'occurred_on': '2026-09-05',
            },
        )
        self.assertEqual(posted.status_code, 302)
        self.assertEqual(Financing.objects.count(), 0)

    def test_manager_can_register_contribution(self):
        _grant(self.staff, 'view_finance', 'manage_financing')
        self.client.force_login(self.staff)
        response = self.client.post(
            '/dashboard/finanzas/ingresos/financiamiento/',
            {
                'action': 'create',
                'kind': 'contribution',
                'counterparty': 'Socio',
                'amount': '25000',
                'account': str(self.account.id),
                'occurred_on': '2026-09-05',
            },
        )
        self.assertEqual(response.status_code, 302)
        item = Financing.objects.get()
        self.assertEqual(item.kind, Financing.Kind.CONTRIBUTION)
        self.assertEqual(self.account.get_current_balance(), Decimal('25000'))
        listing = self.client.get('/dashboard/finanzas/ingresos/financiamiento/')
        self.assertContains(listing, 'Socio')
        self.assertContains(listing, 'Aporte de capital')
