from decimal import Decimal

from django.test import SimpleTestCase

from finance.calculations import (
    contribution_margin,
    line_gross_margin,
    margin_percentage,
    sale_components,
)
from finance.money import allocate_proportional, split_gross_vat, to_decimal


class MoneyConversionTests(SimpleTestCase):
    def test_rejects_float(self):
        with self.assertRaises(TypeError):
            to_decimal(1.19)


class VatSplitTests(SimpleTestCase):
    def test_affected_119000(self):
        net, vat = split_gross_vat(Decimal('119000'), is_vat_affected=True)
        self.assertEqual(net, Decimal('100000'))
        self.assertEqual(vat, Decimal('19000'))
        self.assertEqual(net + vat, Decimal('119000'))

    def test_not_affected_keeps_gross(self):
        net, vat = split_gross_vat(Decimal('119000'), is_vat_affected=False)
        self.assertEqual(net, Decimal('119000'))
        self.assertEqual(vat, Decimal('0'))

    def test_zero(self):
        net, vat = split_gross_vat(0, is_vat_affected=True)
        self.assertEqual(net, Decimal('0'))
        self.assertEqual(vat, Decimal('0'))


class ProrationTests(SimpleTestCase):
    def test_sum_equals_total_with_rounding(self):
        allocated = allocate_proportional(Decimal('100'), [Decimal('1'), Decimal('1'), Decimal('1')])
        self.assertEqual(sum(allocated, Decimal('0')), Decimal('100'))
        self.assertEqual(len(allocated), 3)
        self.assertTrue(all(part >= Decimal('0') for part in allocated))

    def test_proportional_to_line_nets(self):
        # Casco 120000, guantes 30000, mica 20000 → pesos 120/30/20
        weights = [Decimal('120000'), Decimal('30000'), Decimal('20000')]
        allocated = allocate_proportional(Decimal('17000'), weights)
        self.assertEqual(sum(allocated, Decimal('0')), Decimal('17000'))
        self.assertEqual(allocated[0], Decimal('12000'))
        self.assertEqual(allocated[1], Decimal('3000'))
        self.assertEqual(allocated[2], Decimal('2000'))

    def test_zero_weights_do_not_divide(self):
        allocated = allocate_proportional(Decimal('5000'), [0, 0, 0])
        self.assertEqual(allocated, [Decimal('0'), Decimal('0'), Decimal('0')])

    def test_empty_weights(self):
        self.assertEqual(allocate_proportional(Decimal('10'), []), [])


class MarginFormulaTests(SimpleTestCase):
    def test_sale_components_affected(self):
        components = sale_components(Decimal('119000'), Decimal('40000'), is_vat_affected=True)
        self.assertEqual(components['net_sale'], Decimal('100000'))
        self.assertEqual(components['vat_debit'], Decimal('19000'))
        self.assertEqual(components['gross_margin'], Decimal('60000'))
        self.assertEqual(components['gross_margin_pct'], Decimal('60'))

    def test_margin_percentage_zero_net(self):
        self.assertEqual(margin_percentage(Decimal('10'), Decimal('0')), Decimal('0'))

    def test_contribution_subtracts_variable_costs(self):
        result = contribution_margin(
            net_sale=Decimal('100000'),
            cost_net=Decimal('40000'),
            commission=Decimal('3080'),
            shipping_assumed=Decimal('2000'),
            other_variable=Decimal('0'),
        )
        self.assertEqual(result, Decimal('54920'))
        self.assertEqual(line_gross_margin(Decimal('100000'), Decimal('40000')), Decimal('60000'))
