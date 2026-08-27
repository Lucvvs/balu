from django.db import migrations, models
from django.utils import timezone


def _build_order_number(order):
    created = order.created_at or timezone.now()
    if timezone.is_naive(created):
        created = timezone.make_aware(created, timezone.get_current_timezone())
    dt = timezone.localtime(created)
    user = order.user
    if user:
        name_init = user.first_name[0].upper() if user.first_name else 'A'
        email_init = user.email[0].upper() if user.email else 'A'
    else:
        name_init = order.customer_name[0].upper() if order.customer_name else 'A'
        email_init = order.customer_email[0].upper() if order.customer_email else 'A'
    year_code = dt.year - (dt.day + dt.month)
    return f"{order.id}{name_init}{email_init}{year_code}"


def forwards_fill_order_numbers(apps, schema_editor):
    Order = apps.get_model('shop', 'Order')
    for order in Order.objects.select_related('user').iterator():
        if order.order_number:
            continue
        Order.objects.filter(pk=order.pk).update(order_number=_build_order_number(order))


def backwards_clear_order_numbers(apps, schema_editor):
    Order = apps.get_model('shop', 'Order')
    Order.objects.update(order_number=None)


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0023_product_special_shipping'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='order_number',
            field=models.CharField(
                blank=True,
                help_text='Se genera una sola vez al crear el pedido y no cambia.',
                max_length=32,
                null=True,
                unique=True,
                verbose_name='Número de pedido',
            ),
        ),
        migrations.RunPython(forwards_fill_order_numbers, backwards_clear_order_numbers),
    ]
