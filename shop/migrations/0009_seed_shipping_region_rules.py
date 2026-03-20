# Datos iniciales: RM $3.000, resto $5.000 para "Envío a domicilio"

from django.db import migrations


def seed_shipping_rules(apps, schema_editor):
    ShippingMethod = apps.get_model('shop', 'ShippingMethod')
    ShippingRule = apps.get_model('shop', 'ShippingRule')
    metro_name = 'Metropolitana de Santiago'
    method = ShippingMethod.objects.filter(name='Envío a domicilio', base_price__gt=0).first()
    if not method:
        method = ShippingMethod.objects.filter(base_price__gt=0, is_active=True).first()
    if not method:
        return
    if ShippingRule.objects.filter(shipping_method=method).exists():
        return
    ShippingRule.objects.create(
        shipping_method=method,
        min_order_amount=0,
        region=metro_name,
        comuna='',
        price=3000,
        priority=10,
        is_active=True,
    )
    ShippingRule.objects.create(
        shipping_method=method,
        min_order_amount=0,
        region='',
        comuna='',
        price=5000,
        priority=0,
        is_active=True,
    )


def unseed_shipping_rules(apps, schema_editor):
    ShippingMethod = apps.get_model('shop', 'ShippingMethod')
    ShippingRule = apps.get_model('shop', 'ShippingRule')
    method = ShippingMethod.objects.filter(name='Envío a domicilio').first()
    if method:
        ShippingRule.objects.filter(shipping_method=method).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0008_shipping_rules'),
    ]

    operations = [
        migrations.RunPython(seed_shipping_rules, unseed_shipping_rules),
    ]
