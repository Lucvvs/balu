from django import forms
from django.contrib.auth.forms import (
    BaseUserCreationForm,
    SetUnusablePasswordMixin,
    UserChangeForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV3
from .models import Product, ProductVariant, Coupon, ContactMessage, ShippingMethod, PaymentMethod, CustomUser
from .utils import get_regiones_choices


class CustomUserChangeForm(UserChangeForm):
    """Admin: evita field_classes de `username` del UserChangeForm stock (CustomUser no lo tiene en BD)."""

    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = "__all__"
        field_classes = {}


class CustomAdminUserCreationForm(SetUnusablePasswordMixin, BaseUserCreationForm):
    """Admin: equivalente a AdminUserCreationForm pero con email en lugar de username (evita clean_username stock)."""

    usable_password = SetUnusablePasswordMixin.create_usable_password_field()

    class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name")
        field_classes = {"email": forms.EmailField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].required = False
        self.fields["password2"].required = False

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                _("Ya existe un usuario con este correo electrónico."),
                code="unique",
            )
        return email


class UserRegistrationForm(UserCreationForm):
    """Formulario de registro de usuario"""
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label="Nombre",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label="Apellido",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'})
    )
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label="Teléfono",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'})
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'})
    )
    captcha = ReCaptchaField(
        widget=ReCaptchaV3,
        label='',
        required=False  # No requerido por defecto, se hará requerido solo en producción
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'phone', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deshabilitar captcha en desarrollo (DEBUG=True)
        if settings.DEBUG:
            # Eliminar el campo captcha del formulario en desarrollo
            if 'captcha' in self.fields:
                del self.fields['captcha']
        else:
            # En producción, hacer el captcha requerido
            if 'captcha' in self.fields:
                self.fields['captcha'].required = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone = self.cleaned_data.get('phone', '')
        if commit:
            user.save()
        return user


class VariantOptionSelect(forms.Select):
    """Select de variantes con data-stock en cada <option> para limitar cantidad en el cliente."""

    def __init__(self, variant_stocks=None, attrs=None):
        super().__init__(attrs)
        self.variant_stocks = variant_stocks or {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value is not None and value != '':
            key = str(value)
            if key in self.variant_stocks:
                option.setdefault('attrs', {})
                stock = int(self.variant_stocks[key])
                option['attrs']['data-stock'] = str(stock)
                if stock <= 0:
                    option['attrs']['disabled'] = True
        return option


class AddToCartForm(forms.Form):
    """Formulario para agregar producto al carrito"""
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'id': 'id_quantity'})
    )
    size = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    variant = forms.ModelChoiceField(
        queryset=ProductVariant.objects.none(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        if product and product.uses_variant_stock():
            qs = product.variants.all().order_by('sort_order', 'name', 'id')
            stocks = {str(v.id): v.stock for v in qs}
            self.fields['variant'].empty_label = 'Seleccione talla / color'
            self.fields['variant'].label = 'Talla / color'
            self.fields['variant'].label_from_instance = lambda obj: obj.name
            # El widget debe asignarse ANTES que queryset: si no, el setter de queryset
            # deja las choices en el widget por defecto y el Select nuevo queda vacío.
            self.fields['variant'].widget = VariantOptionSelect(
                variant_stocks=stocks,
                attrs={'class': 'form-control form-select', 'id': 'id_variant'},
            )
            self.fields['variant'].queryset = qs
            self.fields['variant'].required = any(v.stock > 0 for v in qs)
            self.fields['size'].widget = forms.HiddenInput()
            self.fields['size'].required = False
        else:
            self.fields['size'].widget = forms.HiddenInput()
            self.fields['variant'].widget = forms.HiddenInput()
            self.fields['variant'].required = False


class UpdateCartItemForm(forms.Form):
    """Formulario para actualizar cantidad en carrito"""
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )


class CouponForm(forms.Form):
    """Formulario para aplicar cupón"""
    code = forms.CharField(
        max_length=50,
        label="Código de cupón",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: CUPON2025',
            'style': 'text-transform: uppercase;'
        })
    )

    def clean_code(self):
        code = self.cleaned_data.get('code', '').upper().strip()
        return code


class CheckoutForm(forms.Form):
    """Formulario de checkout"""
    shipping_method = forms.ModelChoiceField(
        queryset=ShippingMethod.objects.filter(is_active=True),
        label="Método de entrega",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.filter(is_active=True),
        label="Método de pago",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    shipping_region = forms.ChoiceField(
        choices=[('', 'Seleccione una región')] + get_regiones_choices(),
        required=False,
        label="Región",
        widget=forms.Select(attrs={
            'class': 'form-control form-select', 
            'id': 'shipping-region',
            'style': 'max-height: 200px; overflow-y: auto;'
        })
    )
    shipping_comuna = forms.CharField(
        max_length=100,
        required=False,
        label="Comuna",
        # No usar widget aquí, el select se maneja directamente en el template
    )
    shipping_address = forms.CharField(
        required=False,
        label="Dirección",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Calle, número, departamento, etc.'})
    )
    shipping_notes = forms.CharField(
        required=False,
        label="Indicaciones adicionales",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ej: Llamar antes de llegar, dejar en recepción, etc.'})
    )
    customer_name = forms.CharField(
        max_length=200,
        required=False,
        label="Nombre completo",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    customer_email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    customer_phone = forms.CharField(
        max_length=20,
        required=True,
        label="Teléfono",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    accept_terms = forms.BooleanField(
        required=True,
        label='',
        error_messages={
            'required': 'Debes aceptar los términos y condiciones para continuar.',
        },
    )

    def clean(self):
        cleaned_data = super().clean()
        shipping_method = cleaned_data.get('shipping_method')
        shipping_region = cleaned_data.get('shipping_region')
        shipping_comuna = cleaned_data.get('shipping_comuna')
        shipping_address = cleaned_data.get('shipping_address')

        # Solo validar campos de dirección si el método de envío tiene costo (envío a domicilio)
        # Si base_price es 0, es retiro y no requiere dirección
        if shipping_method and shipping_method.base_price > 0:
            if not shipping_region or shipping_region == '':
                raise forms.ValidationError("Debe seleccionar la región para envío a domicilio.")
            if not shipping_comuna or shipping_comuna == '':
                raise forms.ValidationError("Debe seleccionar la comuna para envío a domicilio.")
            if not shipping_address or shipping_address.strip() == '':
                raise forms.ValidationError("Debe ingresar la dirección para envío a domicilio.")

        return cleaned_data


class ContactForm(forms.ModelForm):
    """Formulario de contacto"""
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control contact-form-input', 'placeholder': 'Tu nombre'}),
            'email': forms.EmailInput(attrs={'class': 'form-control contact-form-input', 'placeholder': 'correo@ejemplo.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control contact-form-input', 'placeholder': 'Teléfono (opcional)'}),
            'message': forms.Textarea(attrs={'class': 'form-control contact-form-input', 'rows': 6, 'placeholder': '¿En qué podemos ayudarte?'}),
        }
        labels = {
            'name': 'Nombre',
            'email': 'Email',
            'phone': 'Teléfono',
            'message': 'Mensaje',
        }

