from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import Order


@receiver(pre_delete, sender=Order)
def order_restore_stock_before_delete(sender, instance, **kwargs):
    """Al borrar un pedido (admin unitario, shell, etc.) devolver stock reservado."""
    instance.restore_committed_stock()
