from django.db import migrations, models


def update_home_promo_modal_copy(apps, schema_editor):
    HomePromoModal = apps.get_model("shop", "HomePromoModal")
    HomePromoModal.objects.update(
        headline="Seguridad garantizada al mejor precio siempre.",
        tagline="Descuentos sobre descuentos",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0017_homepromomodal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="homepromomodal",
            name="headline",
            field=models.CharField(
                default="Seguridad garantizada al mejor precio siempre.",
                max_length=120,
                verbose_name="Título principal",
            ),
        ),
        migrations.AlterField(
            model_name="homepromomodal",
            name="tagline",
            field=models.CharField(
                default="Descuentos sobre descuentos",
                help_text='Se muestra junto a "CyberDay" tachado en el modal.',
                max_length=200,
                verbose_name="Subtítulo",
            ),
        ),
        migrations.RunPython(update_home_promo_modal_copy, migrations.RunPython.noop),
    ]
