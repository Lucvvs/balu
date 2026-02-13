"""
Utilidades para el envío de correos electrónicos
"""
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

