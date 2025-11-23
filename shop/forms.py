from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product, Coupon, ContactMessage, ShippingMethod, PaymentMethod


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
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuario'})
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class AddToCartForm(forms.Form):
    """Formulario para agregar producto al carrito"""
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )
    size = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        if product and product.has_sizes():
            sizes = product.get_available_sizes_list()
            self.fields['size'].choices = [('', 'Seleccione talla')] + [(size, size) for size in sizes]
            self.fields['size'].required = True
        else:
            self.fields['size'].widget = forms.HiddenInput()


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
    shipping_region = forms.CharField(
        max_length=100,
        required=False,
        label="Región",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    shipping_comuna = forms.CharField(
        max_length=100,
        required=False,
        label="Comuna",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    shipping_address = forms.CharField(
        required=False,
        label="Dirección",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    customer_name = forms.CharField(
        max_length=200,
        required=False,
        label="Nombre completo",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    customer_email = forms.EmailField(
        required=False,
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    customer_phone = forms.CharField(
        max_length=20,
        required=False,
        label="Teléfono",
        widget=forms.TextInput(attrs={'class': 'form-control'})
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
            if not shipping_region:
                raise forms.ValidationError("Debe ingresar la región para envío a domicilio.")
            if not shipping_comuna:
                raise forms.ValidationError("Debe ingresar la comuna para envío a domicilio.")
            if not shipping_address:
                raise forms.ValidationError("Debe ingresar la dirección para envío a domicilio.")

        return cleaned_data


class ContactForm(forms.ModelForm):
    """Formulario de contacto"""
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono (opcional)'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Mensaje'}),
        }
        labels = {
            'name': 'Nombre',
            'email': 'Email',
            'phone': 'Teléfono',
            'message': 'Mensaje',
        }

