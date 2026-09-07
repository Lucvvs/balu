from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from finance.models import FinancialAccount, FinancialMovement, PaymentSettlement
from finance.mp_amounts import extract_mp_settlement_amounts
from finance.services import attach_mercadopago_payment, sync_sale_from_order, upsert_mp_settlement
from shop.models import Category, Order, OrderItem, Payment, PaymentMethod, Product, ShippingMethod


MP_PAYLOAD = {
    'id': '999001',
    'transaction_amount': 100000,
    'transaction_details': {'net_received_amount': 96920},
    'fee_details': [{'amount': 3080, 'type': 'mercadopago_fee'}],
}


class SettlementBase(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Accesorios', slug='acc-set')
        self.shipping = ShippingMethod.objects.create(name='Retiro', description='Retiro', base_price=0)
        self.payment_method = PaymentMethod.objects.create(name='Mercado Pago')
        self.account = FinancialAccount.objects.create(
            name='Mercado Pago',
            account_type=FinancialAccount.AccountType.DIGITAL,
            ledger_role='mp',
            opening_balance=Decimal('0'),
            opening_balance_date=date(2026, 1, 1),
        )
        self.product = Product.objects.create(
            name='Casco',
            short_description='Casco',
            description='Casco',
            category=self.category,
            price=100000,
            cost_net=Decimal('40000'),
        )

    def _order_with_payment(self, *, mp_id=None, amount=100000):
        order = Order.objects.create(
            shipping_method=self.shipping,
            payment_method=self.payment_method,
            subtotal=amount,
            total=amount,
            sales_channel='web',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=amount,
            quantity=1,
            line_total=amount,
        )
        sync_sale_from_order(order)
        payment = Payment.objects.create(
            order=order,
            payment_method=self.payment_method,
            amount=amount,
            status='approved',
            payment_type='mercado_pago',
            mp_payment_id=mp_id,
        )
        return order, payment


class WebSaleDoesNotMoveBankTests(SettlementBase):
    def test_approved_web_sale_does_not_increase_account_until_settlement(self):
        self._order_with_payment()
        self.account.refresh_from_db()
        self.assertEqual(self.account.get_current_balance(), Decimal('0'))
        self.assertEqual(FinancialMovement.objects.count(), 0)
        self.assertEqual(PaymentSettlement.objects.count(), 0)


class DuplicateWebhookTests(SettlementBase):
    def test_duplicate_settlement_call_does_not_duplicate_rows(self):
        _order, payment = self._order_with_payment(mp_id='999001')
        first = upsert_mp_settlement(payment, MP_PAYLOAD)
        second = upsert_mp_settlement(payment, MP_PAYLOAD)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(PaymentSettlement.objects.count(), 1)
        self.assertEqual(FinancialMovement.objects.filter(idempotency_key='settlement:mp:999001').count(), 1)
        self.assertEqual(self.account.get_current_balance(), Decimal('96920'))

    def test_attach_mp_payment_reuses_checkout_row(self):
        order, payment = self._order_with_payment(mp_id=None)
        attached = attach_mercadopago_payment(
            order,
            '888',
            defaults={
                'payment_method': self.payment_method,
                'amount': 100000,
                'status': 'pending',
                'payment_type': 'mercado_pago',
            },
        )
        again = attach_mercadopago_payment(
            order,
            '888',
            defaults={
                'payment_method': self.payment_method,
                'amount': 100000,
                'status': 'pending',
                'payment_type': 'mercado_pago',
            },
        )
        self.assertEqual(attached.pk, payment.pk)
        self.assertEqual(again.pk, payment.pk)
        self.assertEqual(Payment.objects.filter(order=order).count(), 1)
        payment.refresh_from_db()
        self.assertEqual(payment.mp_payment_id, '888')


class AccountBalanceMatchesLedgerTests(SettlementBase):
    def test_balance_equals_opening_plus_confirmed_movements(self):
        self.account.opening_balance = Decimal('1000000')
        self.account.save(update_fields=['opening_balance'])
        _order, payment = self._order_with_payment(mp_id='999001')
        upsert_mp_settlement(payment, MP_PAYLOAD)
        self.assertEqual(self.account.get_current_balance(), Decimal('1096920'))

    def test_confirmed_movement_cannot_be_deleted(self):
        _order, payment = self._order_with_payment(mp_id='999001')
        upsert_mp_settlement(payment, MP_PAYLOAD)
        movement = FinancialMovement.objects.get()
        with self.assertRaises(ValidationError):
            movement.delete()


class MpAmountAndCommissionTests(SettlementBase):
    def test_extract_real_fee_and_net(self):
        gross, fee, net = extract_mp_settlement_amounts(MP_PAYLOAD)
        self.assertEqual(gross, Decimal('100000'))
        self.assertEqual(fee, Decimal('3080'))
        self.assertEqual(net, Decimal('96920'))

    def test_commission_is_allocated_to_sales_lines(self):
        order, payment = self._order_with_payment(mp_id='999001')
        upsert_mp_settlement(payment, MP_PAYLOAD)
        line = order.items.get()
        order.refresh_from_db()
        self.assertEqual(line.commission_allocated, Decimal('3080'))
        self.assertEqual(payment.settlement.fee_amount, Decimal('3080'))
        self.assertEqual(order.financial_status, 'settled')
