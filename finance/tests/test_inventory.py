from decimal import Decimal

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings

from finance.forms import CatalogProductForm
from finance.inventory import catalog_potential_totals, product_potential
from finance.models import FinancialAccount, FinancialMovement
from shop.models import Category, CustomUser, Order, Product, ProductVariant


def _grant(user, *codenames):
    ct = ContentType.objects.get_for_model(FinancialAccount)
    for code in codenames:
        user.user_permissions.add(Permission.objects.get(content_type=ct, codename=code))


class CatalogPotentialTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Cascos', slug='cascos-inv')

    def test_two_units_at_list_price_with_vat(self):
        product = Product.objects.create(
            name='Casco potencial',
            short_description='Casco',
            description='Casco',
            category=self.category,
            price=119000,
            cost_net=Decimal('40000'),
            stock=2,
            is_vat_affected=True,
        )
        row = product_potential(product)
        self.assertEqual(row.gross, Decimal('238000'))
        self.assertEqual(row.net, Decimal('200000'))
        self.assertEqual(row.vat, Decimal('38000'))
        self.assertEqual(row.cogs, Decimal('80000'))
        self.assertEqual(row.margin, Decimal('120000'))
        self.assertFalse(row.cost_missing)

    def test_uses_published_offer_price_and_flags_missing_cost(self):
        product = Product.objects.create(
            name='Guantes oferta',
            short_description='Guantes',
            description='Guantes',
            category=self.category,
            price=30000,
            offer_price=23800,
            cost_net=Decimal('0'),
            stock=1,
            is_vat_affected=True,
        )
        row = product_potential(product)
        self.assertEqual(row.published_price, Decimal('23800'))
        self.assertEqual(row.net, Decimal('20000'))
        self.assertTrue(row.cost_missing)

    def test_totals_do_not_create_sales_or_movements(self):
        Product.objects.create(
            name='Mica',
            short_description='Mica',
            description='Mica',
            category=self.category,
            price=11900,
            cost_net=Decimal('5000'),
            stock=3,
        )
        totals = catalog_potential_totals(Product.objects.all())
        self.assertEqual(totals['units'], 3)
        self.assertEqual(FinancialMovement.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)


@override_settings(SECURE_SSL_REDIRECT=False)
class InventoryAccessTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Accesorios', slug='accesorios-inv')
        self.product = Product.objects.create(
            name='Casco stock',
            sku='CASCO-INV',
            short_description='Casco',
            description='Casco',
            category=self.category,
            price=119000,
            cost_net=Decimal('40000'),
            stock=1,
        )
        self.url = '/dashboard/finanzas/inventario/'

    def test_staff_with_view_can_see_list_but_cannot_change_stock(self):
        user = CustomUser.objects.create_user(
            email='ver@motomoto.cl',
            password='pass-12345',
            first_name='Ver',
            last_name='Finanzas',
            is_staff=True,
        )
        _grant(user, 'view_finance')
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Potencial neto')
        self.assertContains(response, 'Casco stock')
        self.assertNotContains(response, f'/inventario/{self.product.id}/stock/')

        posted = self.client.post(
            f'/dashboard/finanzas/inventario/{self.product.id}/stock/',
            {'stock': '9', 'next': self.url},
        )
        self.assertEqual(posted.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertEqual(self.product.price, 119000)

    def test_staff_without_catalog_cannot_open_create(self):
        user = CustomUser.objects.create_user(
            email='nocat@motomoto.cl',
            password='pass-12345',
            first_name='No',
            last_name='Cat',
            is_staff=True,
        )
        _grant(user, 'view_finance')
        self.client.force_login(user)
        response = self.client.get('/dashboard/finanzas/inventario/nuevo/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)


@override_settings(SECURE_SSL_REDIRECT=False)
class InventoryMutationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Chaquetas', slug='chaquetas-inv')
        self.other = Product.objects.create(
            name='Producto ancla',
            sku='ANCLA-1',
            short_description='Ancla',
            description='Ancla',
            category=self.category,
            price=50000,
            cost_net=Decimal('20000'),
            stock=4,
        )
        self.user = CustomUser.objects.create_user(
            email='catalogo@motomoto.cl',
            password='pass-12345',
            first_name='Cat',
            last_name='Alogo',
            is_staff=True,
        )
        _grant(self.user, 'view_finance', 'manage_catalog')
        self.client.force_login(self.user)

    def test_create_form_renders(self):
        response = self.client.get('/dashboard/finanzas/inventario/nuevo/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Guardar producto')
        self.assertContains(response, 'Variantes')
        self.assertContains(response, 'Se calcula solo')
        self.assertContains(response, 'id_cost_gross')

    def _formsets(self, **extra):
        data = {
            'variants-TOTAL_FORMS': '2',
            'variants-INITIAL_FORMS': '0',
            'variants-MIN_NUM_FORMS': '0',
            'variants-MAX_NUM_FORMS': '1000',
            'variants-0-name': '',
            'variants-0-stock': '0',
            'variants-0-sort_order': '0',
            'variants-1-name': '',
            'variants-1-stock': '0',
            'variants-1-sort_order': '0',
            'images-TOTAL_FORMS': '1',
            'images-INITIAL_FORMS': '0',
            'images-MIN_NUM_FORMS': '0',
            'images-MAX_NUM_FORMS': '1000',
            'images-0-order': '0',
            'is_active': 'on',
            'is_vat_affected': 'on',
        }
        data.update(extra)
        return data

    def test_stock_update_does_not_change_price(self):
        response = self.client.post(
            f'/dashboard/finanzas/inventario/{self.other.id}/stock/',
            {'stock': '7', 'next': '/dashboard/finanzas/inventario/'},
        )
        self.assertEqual(response.status_code, 302)
        self.other.refresh_from_db()
        self.assertEqual(self.other.stock, 7)
        self.assertEqual(self.other.price, 50000)

    def test_create_product_leaves_other_prices_untouched(self):
        payload = self._formsets(
            name='Chaqueta nueva',
            sku='CHAQ-NEW',
            short_description='Chaqueta',
            description='Chaqueta de tes',
            category=str(self.category.id),
            price='89000',
            cost_net='30000',
            cost_gross='35700',
            stock='3',
        )
        response = self.client.post('/dashboard/finanzas/inventario/nuevo/', payload)
        self.assertEqual(response.status_code, 302)
        created = Product.objects.get(sku='CHAQ-NEW')
        self.assertEqual(created.price, 89000)
        self.assertEqual(created.cost_gross, Decimal('35700'))
        self.assertEqual(created.stock, 3)
        self.other.refresh_from_db()
        self.assertEqual(self.other.price, 50000)
        self.assertEqual(self.other.stock, 4)
        self.assertEqual(FinancialMovement.objects.count(), 0)

    def test_variant_stock_updates_parent_sum_not_price(self):
        product = Product.objects.create(
            name='Chaqueta tallas',
            sku='CHAQ-VAR',
            short_description='Tallas',
            description='Tallas',
            category=self.category,
            price=99000,
            cost_net=Decimal('40000'),
            stock=0,
        )
        small = ProductVariant.objects.create(product=product, name='S', stock=2, sort_order=0)
        medium = ProductVariant.objects.create(product=product, name='M', stock=3, sort_order=1)
        product.refresh_from_db()
        self.assertEqual(product.stock, 5)

        payload = self._formsets(
            name=product.name,
            sku=product.sku,
            short_description=product.short_description,
            description=product.description,
            category=str(self.category.id),
            price=str(product.price),
            cost_net='40000',
            cost_gross='0',
            is_active='on',
            is_vat_affected='on',
            **{
                'variants-TOTAL_FORMS': '3',
                'variants-INITIAL_FORMS': '2',
                'variants-0-id': str(small.pk),
                'variants-0-name': 'S',
                'variants-0-stock': '10',
                'variants-0-sort_order': '0',
                'variants-1-id': str(medium.pk),
                'variants-1-name': 'M',
                'variants-1-stock': '4',
                'variants-1-sort_order': '1',
                'variants-2-name': '',
                'variants-2-stock': '0',
                'variants-2-sort_order': '0',
            },
        )
        response = self.client.post(f'/dashboard/finanzas/inventario/{product.id}/', payload)
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.stock, 14)
        self.assertEqual(product.price, 99000)
        self.other.refresh_from_db()
        self.assertEqual(self.other.price, 50000)

        blocked = self.client.post(
            f'/dashboard/finanzas/inventario/{product.id}/stock/',
            {'stock': '1'},
        )
        self.assertEqual(blocked.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.stock, 14)


class CatalogProductCostFormTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Cascos costo', slug='cascos-costo')

    def _data(self, **extra):
        data = {
            'name': 'Casco integral',
            'short_description': 'Casco',
            'description': 'Casco de prueba',
            'category': str(self.category.id),
            'price': '64990',
            'cost_net': '35378',
            'cost_gross': '1',
            'stock': '1',
            'is_active': 'on',
            'is_vat_affected': 'on',
        }
        data.update(extra)
        return data

    def test_gross_is_derived_from_net_even_if_posted_wrong(self):
        form = CatalogProductForm(data=self._data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['cost_net'], Decimal('35378'))
        self.assertEqual(form.cleaned_data['cost_gross'], Decimal('42100'))
        product = form.save()
        self.assertEqual(product.cost_net, Decimal('35378'))
        self.assertEqual(product.cost_gross, Decimal('42100'))

    def test_without_vat_gross_equals_net(self):
        data = self._data()
        data.pop('is_vat_affected')
        form = CatalogProductForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['cost_gross'], Decimal('35378'))

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_create_view_persists_derived_gross(self):
        user = CustomUser.objects.create_user(
            email='costo@motomoto.cl',
            password='pass-12345',
            first_name='Costo',
            last_name='Bruto',
            is_staff=True,
        )
        _grant(user, 'view_finance', 'manage_catalog')
        self.client.force_login(user)
        payload = {
            'name': 'Casco lista',
            'sku': 'CASCO-64990',
            'short_description': 'Casco',
            'description': 'Casco',
            'category': str(self.category.id),
            'price': '64990',
            'cost_net': '35378',
            'cost_gross': '99999',
            'stock': '1',
            'is_active': 'on',
            'is_vat_affected': 'on',
            'variants-TOTAL_FORMS': '1',
            'variants-INITIAL_FORMS': '0',
            'variants-MIN_NUM_FORMS': '0',
            'variants-MAX_NUM_FORMS': '1000',
            'variants-0-name': '',
            'variants-0-stock': '0',
            'variants-0-sort_order': '0',
            'images-TOTAL_FORMS': '1',
            'images-INITIAL_FORMS': '0',
            'images-MIN_NUM_FORMS': '0',
            'images-MAX_NUM_FORMS': '1000',
            'images-0-order': '0',
        }
        response = self.client.post('/dashboard/finanzas/inventario/nuevo/', payload)
        self.assertEqual(response.status_code, 302)
        created = Product.objects.get(sku='CASCO-64990')
        self.assertEqual(created.price, 64990)
        self.assertEqual(created.cost_net, Decimal('35378'))
        self.assertEqual(created.cost_gross, Decimal('42100'))
