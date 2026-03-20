"""
Utilidades para el envío de correos electrónicos y carga de datos
"""
import json
import unicodedata
from pathlib import Path
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags


def send_order_confirmation_email(order):
    """
    Envía email de confirmación al cliente cuando se crea un pedido
    
    Args:
        order: Instancia del modelo Order
        
    Returns:
        bool: True si el email se envió correctamente, False en caso contrario
    """
    if not order.customer_email:
        return False
    
    try:
        # Renderizar template de email HTML
        html_message = render_to_string('shop/emails/order_confirmation.html', {
            'order': order,
            'order_items': order.items.all(),
        })
        
        # Versión de texto plano (sin HTML)
        plain_message = strip_tags(html_message)
        
        # Enviar email
        send_mail(
            subject=f'Confirmación de Pedido #{order.order_number} - MotoMoto',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        # Log del error (en producción podrías usar logging)
        print(f'Error al enviar email de confirmación: {str(e)}')
        return False


def send_order_notification_to_admin(order):
    """
    Envía notificación al administrador cuando se crea un nuevo pedido
    
    Args:
        order: Instancia del modelo Order
        
    Returns:
        bool: True si el email se envió correctamente, False en caso contrario
    """
    admin_email = getattr(settings, 'ADMIN_EMAIL', None)
    if not admin_email:
        return False
    
    try:
        # Renderizar template de email HTML
        html_message = render_to_string('shop/emails/order_notification_admin.html', {
            'order': order,
            'order_items': order.items.all(),
        })
        
        # Versión de texto plano
        plain_message = strip_tags(html_message)
        
        # Enviar email
        send_mail(
            subject=f'Nuevo Pedido #{order.order_number} - MotoMoto',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        # Log del error
        print(f'Error al enviar notificación al admin: {str(e)}')
        return False


# =========================
# Envío por región (Chile)
# =========================
# Debe coincidir con el nombre en shop/data/regiones_comunas.json y el formulario de checkout.
CHILE_METRO_REGION_NAME = 'Metropolitana de Santiago'
SHIPPING_PRICE_METRO_REGION_DEFAULT = 3000
SHIPPING_PRICE_OTHER_REGIONS_DEFAULT = 5000


def normalize_shipping_match_string(value: str) -> str:
    """Normaliza espacios y Unicode (ej. tildes) para comparar región/comuna con reglas."""
    if not value:
        return ''
    return unicodedata.normalize('NFKC', str(value)).strip()


# =========================
# Utilidades para Regiones y Comunas de Chile
# =========================

def get_regiones_comunas_data():
    """
    Carga los datos de regiones y comunas desde el archivo JSON
    
    Returns:
        dict: Diccionario con la estructura de regiones y comunas
        None: Si hay error al cargar el archivo
    """
    try:
        # Obtener la ruta del archivo JSON
        base_dir = Path(__file__).resolve().parent
        json_path = base_dir / 'data' / 'regiones_comunas.json'
        
        if not json_path.exists():
            print(f'Advertencia: No se encontró el archivo {json_path}')
            return None
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f'Error al cargar regiones y comunas: {str(e)}')
        return None


def get_regiones_choices():
    """
    Obtiene las opciones de regiones para usar en formularios
    
    Returns:
        list: Lista de tuplas (valor, etiqueta) para ChoiceField
    """
    data = get_regiones_comunas_data()
    if not data:
        return []
    
    choices = []
    
    # Estructura del JSON: {"name": "Chile", "regions": [{"name": "...", "communes": [...]}, ...]}
    if isinstance(data, dict):
        if 'regions' in data:
            for region in data['regions']:
                if isinstance(region, dict):
                    nombre = region.get('name')
                    if nombre:
                        choices.append((nombre, nombre))
        # Estructura alternativa: {"regiones": [...]}
        elif 'regiones' in data:
            for region in data['regiones']:
                if isinstance(region, dict):
                    nombre = region.get('nombre') or region.get('name')
                    if nombre:
                        choices.append((nombre, nombre))
    
    return sorted(choices, key=lambda x: x[1])


def get_comunas_choices(region=None):
    """
    Obtiene las opciones de comunas para una región específica
    
    Args:
        region: Nombre de la región (opcional)
    
    Returns:
        list: Lista de tuplas (valor, etiqueta) para ChoiceField
    """
    data = get_regiones_comunas_data()
    if not data or not region:
        return []
    
    choices = []
    
    # Estructura del JSON: {"name": "Chile", "regions": [{"name": "...", "communes": [...]}, ...]}
    if isinstance(data, dict):
        if 'regions' in data:
            for reg in data['regions']:
                if isinstance(reg, dict):
                    region_name = reg.get('name')
                    if region_name == region and 'communes' in reg:
                        comunas = reg['communes']
                        if isinstance(comunas, list):
                            for comuna in comunas:
                                if isinstance(comuna, dict):
                                    comuna_name = comuna.get('name')
                                    if comuna_name:
                                        choices.append((comuna_name, comuna_name))
                                elif isinstance(comuna, str):
                                    choices.append((comuna, comuna))
        # Estructura alternativa: {"regiones": [...]}
        elif 'regiones' in data:
            for reg in data['regiones']:
                if isinstance(reg, dict):
                    region_name = reg.get('nombre') or reg.get('name')
                    if region_name == region and 'comunas' in reg:
                        comunas = reg['comunas']
                        if isinstance(comunas, list):
                            for comuna in comunas:
                                if isinstance(comuna, dict):
                                    comuna_name = comuna.get('nombre') or comuna.get('name')
                                    if comuna_name:
                                        choices.append((comuna_name, comuna_name))
                                elif isinstance(comuna, str):
                                    choices.append((comuna, comuna))
    
    return sorted(choices, key=lambda x: x[1])

