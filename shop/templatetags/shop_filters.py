from django import template

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

