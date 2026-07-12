from django.db import migrations, models


def copy_promo_image_to_mobile_portrait(apps, schema_editor):
    HomePromoModal = apps.get_model("shop", "HomePromoModal")
    for row in HomePromoModal.objects.all():
        if row.promo_image and not row.image_mobile_portrait:
            row.image_mobile_portrait = row.promo_image
            row.save(update_fields=["image_mobile_portrait"])


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0020_homepromomodal_image_mode"),
    ]

    operations = [
        migrations.AlterField(
            model_name="homepromomodal",
            name="promo_image",
            field=models.ImageField(
                blank=True,
                help_text="Se usa si falta la imagen específica de alguna pantalla/orientación.",
                null=True,
                upload_to="home_promo/",
                verbose_name="Imagen de respaldo",
            ),
        ),
        migrations.AddField(
            model_name="homepromomodal",
            name="image_mobile_portrait",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="home_promo/",
                verbose_name="Móvil · vertical",
            ),
        ),
        migrations.AddField(
            model_name="homepromomodal",
            name="image_mobile_landscape",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="home_promo/",
                verbose_name="Móvil · horizontal",
            ),
        ),
        migrations.AddField(
            model_name="homepromomodal",
            name="image_tablet_portrait",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="home_promo/",
                verbose_name="Tablet · vertical",
            ),
        ),
        migrations.AddField(
            model_name="homepromomodal",
            name="image_tablet_landscape",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="home_promo/",
                verbose_name="Tablet · horizontal",
            ),
        ),
        migrations.AddField(
            model_name="homepromomodal",
            name="image_desktop_portrait",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="home_promo/",
                verbose_name="Escritorio · vertical",
            ),
        ),
        migrations.AddField(
            model_name="homepromomodal",
            name="image_desktop_landscape",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="home_promo/",
                verbose_name="Escritorio · horizontal",
            ),
        ),
        migrations.RunPython(copy_promo_image_to_mobile_portrait, migrations.RunPython.noop),
    ]
