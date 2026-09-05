from django import forms
from django.forms import formset_factory, inlineformset_factory
from django.utils.text import slugify

from shop.models import PaymentMethod, Product, ProductImage, ProductVariant
from finance.models import ExpenseCategory, FinancialAccount, Financing


def unique_product_slug(name: str, instance_pk=None) -> str:
    base = slugify(name) or 'producto'
    slug = base
    n = 2
    while True:
        qs = Product.objects.filter(slug=slug)
        if instance_pk:
            qs = qs.exclude(pk=instance_pk)
        if not qs.exists():
            return slug
        slug = f'{base}-{n}'
        n += 1


class CatalogProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            'name',
            'sku',
            'short_description',
            'description',
            'category',
            'brand',
            'price',
            'offer_price',
            'cost_net',
            'cost_gross',
            'is_vat_affected',
            'stock',
            'is_active',
            'is_offer',
            'is_best_seller',
            'show_variant_badges',
            'uses_special_shipping',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vacío = MM-{id}'}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'offer_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'cost_net': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'cost_gross': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sku'].required = False
        self.fields['brand'].required = False
        self.fields['offer_price'].required = False
        if self.instance.pk and self.instance.variants.exists():
            self.fields['stock'].disabled = True
            self.fields['stock'].help_text = 'Con variantes, el stock es la suma de las opciones.'

    def clean_sku(self):
        sku = (self.cleaned_data.get('sku') or '').strip()
        return sku or None

    def clean_offer_price(self):
        value = self.cleaned_data.get('offer_price')
        if value == 0:
            return None
        return value

    def save(self, commit=True):
        product = super().save(commit=False)
        if not product.slug:
            product.slug = unique_product_slug(product.name, product.pk)
        if commit:
            product.save()
            self.save_m2m()
        return product


class SimpleStockForm(forms.Form):
    stock = forms.IntegerField(min_value=0, label='Stock')


class VariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ('name', 'stock', 'sort_order')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'S, M, Roja…'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ('image', 'is_primary', 'order')
        widgets = {
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


VariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=VariantForm,
    extra=2,
    can_delete=True,
    min_num=0,
)

ImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=1,
    can_delete=True,
)


class VariantSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            lookup = getattr(self, 'product_lookup', None)
            if lookup is None:
                self.product_lookup = {
                    str(pk): product_id
                    for pk, product_id in ProductVariant.objects.values_list('id', 'product_id')
                }
                lookup = self.product_lookup
            raw = str(getattr(value, 'value', value))
            product_id = lookup.get(raw)
            if product_id:
                option['attrs']['data-product'] = str(product_id)
        return option


class PosSaleForm(forms.Form):
    customer_name = forms.CharField(
        required=False,
        max_length=200,
        label='Cliente',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cliente tienda'}),
    )
    customer_phone = forms.CharField(
        required=False,
        max_length=20,
        label='Teléfono',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.none(),
        label='Medio de pago',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    discount_total = forms.IntegerField(
        required=False,
        min_value=0,
        initial=0,
        label='Descuento (CLP)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
    )
    notes = forms.CharField(
        required=False,
        label='Nota',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'}),
    )

    def __init__(self, *args, **kwargs):
        from finance.services.pos_sale import pos_payment_methods

        super().__init__(*args, **kwargs)
        self.fields['payment_method'].queryset = pos_payment_methods()

    def clean_discount_total(self):
        return self.cleaned_data.get('discount_total') or 0


class PosLineForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).order_by('name'),
        required=False,
        label='Producto',
        widget=forms.Select(attrs={'class': 'form-select pos-product'}),
    )
    variant = forms.ModelChoiceField(
        queryset=ProductVariant.objects.select_related('product').order_by('product__name', 'sort_order', 'name'),
        required=False,
        label='Opción',
        widget=VariantSelect(attrs={'class': 'form-select pos-variant'}),
    )
    quantity = forms.IntegerField(
        required=False,
        min_value=1,
        label='Cantidad',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': '1'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].empty_label = '—'
        self.fields['variant'].empty_label = 'Sin opción'
        self.fields['product'].label_from_instance = lambda obj: (
            f'{obj.name} · {obj.sku or "s/SKU"} · ${obj.current_price:,} · {obj.stock} u.'.replace(',', '.')
        )
        self.fields['variant'].label_from_instance = lambda obj: (
            f'{obj.product.name} — {obj.name} ({obj.stock} u.)'
        )

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get('product')
        variant = cleaned.get('variant')
        quantity = cleaned.get('quantity')
        if not product:
            if variant or quantity:
                raise forms.ValidationError('Elige un producto para esa línea.')
            return cleaned
        if not quantity:
            raise forms.ValidationError('Indica la cantidad.')
        if product.variants.exists():
            if not variant:
                raise forms.ValidationError(f'{product.name} requiere talla/color.')
            if variant.product_id != product.id:
                raise forms.ValidationError('La opción no corresponde al producto.')
        elif variant:
            raise forms.ValidationError(f'{product.name} no usa variantes.')
        return cleaned


PosLineFormSet = formset_factory(PosLineForm, extra=6, min_num=0, validate_min=False)


class FinancingForm(forms.Form):
    kind = forms.ChoiceField(
        choices=Financing.Kind.choices,
        label='Tipo',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    counterparty = forms.CharField(
        max_length=160,
        label='Origen / prestamista',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Socio, banco, etc.'}),
    )
    amount = forms.IntegerField(
        min_value=1,
        label='Monto (CLP)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
    )
    account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.filter(is_active=True).order_by('name'),
        label='Cuenta que recibe el dinero',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    occurred_on = forms.DateField(
        label='Fecha',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    notes = forms.CharField(
        required=False,
        label='Nota',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class LoanRepayForm(forms.Form):
    financing = forms.ModelChoiceField(
        queryset=Financing.objects.none(),
        label='Préstamo',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    amount = forms.IntegerField(
        min_value=1,
        label='Monto a pagar (CLP)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
    )
    account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.filter(is_active=True).order_by('name'),
        label='Cuenta que paga',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    occurred_on = forms.DateField(
        label='Fecha',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    notes = forms.CharField(
        required=False,
        label='Nota',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        open_loans = [
            item.pk
            for item in Financing.objects.filter(kind=Financing.Kind.LOAN).order_by('-occurred_on')
            if item.outstanding() > 0
        ]
        self.fields['financing'].queryset = Financing.objects.filter(pk__in=open_loans).order_by('-occurred_on')


class PurchaseForm(forms.Form):
    supplier = forms.CharField(
        max_length=160,
        label='Proveedor',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del proveedor'}),
    )
    account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.filter(is_active=True).order_by('name'),
        label='Cuenta que paga',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    occurred_on = forms.DateField(
        label='Fecha',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    updates_stock = forms.BooleanField(
        required=False,
        initial=True,
        label='Sumar al stock',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    updates_catalog_cost = forms.BooleanField(
        required=False,
        initial=True,
        label='Actualizar costo vigente',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    is_vat_affected = forms.BooleanField(
        required=False,
        initial=True,
        label='Afecta a IVA',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    notes = forms.CharField(
        required=False,
        label='Nota',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class ExpenseForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.filter(is_active=True).order_by('sort_order', 'name'),
        label='Categoría',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    vendor = forms.CharField(
        max_length=160,
        label='Proveedor / destinatario',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Meta, Enel, etc.'}),
    )
    description = forms.CharField(
        max_length=200,
        label='Descripción',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Campañas septiembre'}),
    )
    amount = forms.IntegerField(
        min_value=1,
        label='Monto bruto (CLP)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
    )
    account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.filter(is_active=True).order_by('name'),
        label='Cuenta que paga',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    occurred_on = forms.DateField(
        label='Fecha',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    is_vat_affected = forms.BooleanField(
        required=False,
        initial=True,
        label='Afecta a IVA',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    notes = forms.CharField(
        required=False,
        label='Nota',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class ExpenseCategoryForm(forms.Form):
    name = forms.CharField(
        max_length=80,
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Meta Ads, arriendo, etc.'}),
    )
    kind = forms.ChoiceField(
        choices=ExpenseCategory.Kind.choices,
        label='Grupo',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class ShipmentForm(forms.Form):
    order_number = forms.CharField(
        max_length=32,
        label='Número de pedido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MM-...'}),
    )
    actual_cost = forms.IntegerField(
        min_value=0,
        label='Costo real courier (CLP)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
    )
    assumed_cost = forms.IntegerField(
        required=False,
        min_value=0,
        label='Costo asumido (margen)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'Igual al real si se omite'}),
    )
    account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.filter(is_active=True).order_by('name'),
        required=False,
        label='Cuenta que paga el flete',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    carrier = forms.CharField(
        required=False,
        max_length=120,
        label='Courier',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    tracking_code = forms.CharField(
        required=False,
        max_length=80,
        label='Seguimiento',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    occurred_on = forms.DateField(
        label='Fecha',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    notes = forms.CharField(
        required=False,
        label='Nota',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class RefundLookupForm(forms.Form):
    order_number = forms.CharField(
        max_length=32,
        label='Número de pedido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MM-...'}),
    )


