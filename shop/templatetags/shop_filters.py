import re

from django import template
from django.templatetags.static import static

register = template.Library()


def _absolute_url_for_email(path, site_base=None):
    """Une path (/media/..., /static/...) con base pública o devuelve path si ya es absoluta."""
    if path is None:
        return ''
    from django.conf import settings

    path = str(path).strip()
    if not path:
        return ''
    if path.startswith('http://') or path.startswith('https://'):
        return path
    base = (site_base or getattr(settings, 'SITE_PUBLIC_URL', '') or '').rstrip('/')
    if base and path.startswith('/'):
        return f'{base}{path}'
    return path


@register.filter(name='email_absolute_url')
def email_absolute_url(path):
    """Convierte /media/... o rutas relativas en URL absoluta para clientes de correo."""
    return _absolute_url_for_email(path)


@register.filter(name='static_absolute_url')
def static_absolute_url(relative_path):
    """URL absoluta a un archivo en static/ (p. ej. logo en emails)."""
    if not relative_path:
        return ''
    url = static(relative_path)
    if url.startswith('http://') or url.startswith('https://'):
        return url
    return _absolute_url_for_email(url)


@register.simple_tag(takes_context=True)
def email_resolved_url(context, path):
    """
    Igual que email_absolute_url / static, pero si el contexto trae email_site_base
    (vista previa en local), usa esa base para que las imágenes carguen en el navegador.
    """
    if path is None:
        return ''
    path = str(path).strip()
    if not path:
        return ''
    if path.startswith('http://') or path.startswith('https://'):
        return path
    site_base = context.get('email_site_base')
    return _absolute_url_for_email(path, site_base=site_base)


@register.simple_tag(takes_context=True)
def email_static_url(context, relative_path):
    """URL absoluta a static/; respeta email_site_base en preview."""
    if not relative_path:
        return ''
    url = static(relative_path)
    if url.startswith('http://') or url.startswith('https://'):
        return url
    site_base = context.get('email_site_base')
    return _absolute_url_for_email(url, site_base=site_base)


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


@register.filter(name='whatsapp_wa_url')
def whatsapp_wa_url(phone):
    """
    Devuelve https://wa.me/<solo dígitos> para enlaces en correos.
    Normaliza números chilenos (+56 9..., 569..., 9XXXXXXXX).
    Cadena vacía si no hay dígitos útiles.
    """
    if not phone:
        return ''
    digits = re.sub(r'\D', '', str(phone).strip())
    if not digits:
        return ''
    if digits.startswith('56'):
        return f'https://wa.me/{digits}'
    if len(digits) == 9 and digits.startswith('9'):
        return f'https://wa.me/56{digits}'
    if len(digits) == 8 and digits.startswith('9'):
        return f'https://wa.me/569{digits}'
    return f'https://wa.me/{digits}'


@register.filter(name='brand_image')
def brand_image(brand_slug):
    """
    Construye la URL de la imagen de una marca basada en su slug.
    Las imágenes están en media/brands/
    Ejemplo: 'hro' -> '/media/brands/hro.webp'
    """
    if not brand_slug:
        return ''
    from django.conf import settings
    return f"{settings.MEDIA_URL}brands/{brand_slug}.webp"

