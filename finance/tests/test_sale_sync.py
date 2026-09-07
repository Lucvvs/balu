from decimal import Decimal

from django.test import TestCase

from finance.calculations import line_gross_margin
from finance.services import sync_sale_from_order
from shop.models import Category, Order, OrderItem, PaymentMethod, Product, ShippingMethod


class SaleSyncTestCase(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Accesorios', slug='accesorios-sync')
        self.shipping = ShippingMethod.objects.create(
            name='Retiro en bodega',
            description='Retiro',
            base_price=0,
        )
        self.payment = PaymentMethod.objects.create(name='Efectivo')

    def _product(self, name, price, cost_net, sku=None):
        return Product.objects.create(
            name=name,
            sku=sku,
            short_description=name,
            description=name,
            category=self.category,
            price=price,
            cost_net=Decimal(str(cost_net)),
            cost_gross=Decimal('0'),
            is_vat_affected=True,
        )

    def _order(self, *, discount=0, shipping_cost=0, subtotal=0, total=None):
        if total is None:
            total = subtotal + shipping_cost - discount
        return Order.objects.create(
            shipping_method=self.shipping,
            payment_method=self.payment,
            shipping_cost=shipping_cost,
            subtotal=subtotal,
            discount_total=discount,
            total=total,
            sales_channel='web',
            is_vat_affected=True,
        )

    def _line(self, order, product, line_total, quantity=1):
        return OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            unit_price=line_total // quantity,
            quantity=quantity,
            line_total=line_total,
        )


class ThreeLineSaleTests(SaleSyncTestCase):
    def test_order_with_three_products_creates_three_financial_lines(self):
        casco = self._product('Casco Shaft', 120000, 40000, sku='CASCO-1')
        guantes = self._product('Guantes', 30000, 10000, sku='GUA-1')
        mica = self._product('Mica', 20000, 5000, sku='MICA-1')
        order = self._order(subtotal=170000, total=170000)
        self._line(order, casco, 120000)
        self._line(order, guantes, 30000)
        self._line(order, mica, 20000)

        lines = sync_sale_from_order(order)

        self.assertEqual(len(lines), 3)
        self.assertEqual(order.items.count(), 3)
        by_sku = {item.sku_snapshot: item for item in lines}
        self.assertEqual(set(by_sku), {'CASCO-1', 'GUA-1', 'MICA-1'})
        self.assertEqual(by_sku['CASCO-1'].gross_sale, Decimal('120000'))
        self.assertEqual(by_sku['GUA-1'].gross_sale, Decimal('30000'))
        self.assertEqual(by_sku['MICA-1'].gross_sale, Decimal('20000'))
        self.assertEqual(
            sum((item.discount_allocated for item in lines), Decimal('0')),
            Decimal('0'),
        )


class HistoricalCostTests(SaleSyncTestCase):
    def test_later_catalog_cost_change_does_not_change_historical_margin(self):
        product = self._product('Casco', 119000, 40000, sku='CASCO-H')
        order = self._order(subtotal=119000, total=119000)
        item = self._line(order, product, 119000)

        sync_sale_from_order(order)
        item.refresh_from_db()
        original_cost = item.unit_cost_net_snapshot
        original_margin = line_gross_margin(item.net_sale, item.line_cost_net)

        product.cost_net = Decimal('47000')
        product.save(update_fields=['cost_net'])
        sync_sale_from_order(order)
        item.refresh_from_db()

        self.assertEqual(original_cost, Decimal('40000'))
        self.assertEqual(item.unit_cost_net_snapshot, Decimal('40000'))
        self.assertEqual(line_gross_margin(item.net_sale, item.line_cost_net), original_margin)
        self.assertEqual(original_margin, Decimal('60000'))


class VatLineTests(SaleSyncTestCase):
    def test_sale_119000_affected_splits_net_and_vat(self):
        product = self._product('Producto IVA', 119000, 40000)
        order = self._order(subtotal=119000, total=119000)
        item = self._line(order, product, 119000)

        sync_sale_from_order(order)
        item.refresh_from_db()

        self.assertEqual(item.gross_sale, Decimal('119000'))
        self.assertEqual(item.net_sale, Decimal('100000'))
        self.assertEqual(item.vat_debit, Decimal('19000'))
        self.assertTrue(item.is_vat_affected)
        self.assertFalse(item.cost_missing)

    def test_not_affected_skips_vat(self):
        product = self._product('Exento', 119000, 40000)
        product.is_vat_affected = False
        product.save(update_fields=['is_vat_affected'])
        order = self._order(subtotal=119000, total=119000)
        item = self._line(order, product, 119000)

        sync_sale_from_order(order)
        item.refresh_from_db()

        self.assertEqual(item.net_sale, Decimal('119000'))
        self.assertEqual(item.vat_debit, Decimal('0'))
        self.assertFalse(item.is_vat_affected)


class DiscountAllocationTests(SaleSyncTestCase):
    def test_order_discount_prorates_and_sums_to_total(self):
        casco = self._product('Casco', 120000, 40000)
        guantes = self._product('Guantes', 30000, 10000)
        mica = self._product('Mica', 20000, 5000)
        order = self._order(discount=17000, subtotal=170000, total=153000)
        self._line(order, casco, 120000)
        self._line(order, guantes, 30000)
        self._line(order, mica, 20000)

        lines = sync_sale_from_order(order)
        allocated = sum((item.discount_allocated for item in lines), Decimal('0'))
        gross = sum((item.gross_sale for item in lines), Decimal('0'))

        self.assertEqual(allocated, Decimal('17000'))
        self.assertEqual(gross, Decimal('153000'))
        self.assertTrue(all(item.allocation_method == 'net_proportional' for item in lines))
