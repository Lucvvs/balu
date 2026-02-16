from django import template
from django.templatetags.static import static

register = template.Library()


@register.filter(name='currency_clp')
def currency_clp(value):
    """
    Formatea un valor numérico como moneda chilena (CLP).
    Ejemplos: 66990 -> $66.990, 10000000 -> $10.000.000
    Sin decimales.
    """
    if value is None:
        return '$0'
    
    try:
        # Convertir a entero
        amount = int(value)
        # Formatear con separador de miles (punto)
        formatted = f"${amount:,}".replace(',', '.')
        return formatted
    except (ValueError, TypeError):
        return '$0'


@register.filter(name='brand_image')
def brand_image(brand_slug):
    """
    Construye la URL de la imagen de una marca basada en su slug.
    Las imágenes están en media/brands/
    Ejemplo: 'hro' -> '/media/brands/hro.png'
    """
    if not brand_slug:
        return ''
    from django.conf import settings
    return f"{settings.MEDIA_URL}brands/{brand_slug}.png"

