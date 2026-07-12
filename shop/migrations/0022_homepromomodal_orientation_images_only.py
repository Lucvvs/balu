from django.db import migrations, models


def migrate_images_to_orientation_only(apps, schema_editor):
    HomePromoModal = apps.get_model("shop", "HomePromoModal")
    for row in HomePromoModal.objects.all():
        portrait = (
            row.image_mobile_portrait
            or row.image_tablet_portrait
            or row.image_desktop_portrait
            or row.promo_image
        )
        landscape = (
            row.image_mobile_landscape
            or row.image_tablet_landscape
            or row.image_desktop_landscape
        )
        update_fields = []
        if portrait and not row.image_portrait:
            row.image_portrait = portrait
            update_fields.append("image_portrait")
        if landscape and not row.image_landscape:
            row.image_landscape = landscape
            update_fields.append("image_landscape")
        if update_fields:
            row.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0021_homepromomodal_responsive_images"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepromomodal",
            name="image_portrait",
            field=models.ImageField(
                blank=True,
                help_text="Se usa en pantallas en orientación vertical (móvil, tablet o escritorio).",
                null=True,
                upload_to="home_promo/",
                verbose_name="Imagen vertical",
            ),
        ),
        migrations.AddField(
            model_name="homepromomodal",
            name="image_landscape",
            field=models.ImageField(
                blank=True,
                help_text="Se usa en pantallas en orientación horizontal. Si falta, se usa la vertical.",
                null=True,
                upload_to="home_promo/",
                verbose_name="Imagen horizontal",
            ),
        ),
        migrations.RunPython(migrate_images_to_orientation_only, migrations.RunPython.noop),
        migrations.RemoveField(model_name="homepromomodal", name="promo_image"),
        migrations.RemoveField(model_name="homepromomodal", name="image_mobile_portrait"),
        migrations.RemoveField(model_name="homepromomodal", name="image_mobile_landscape"),
        migrations.RemoveField(model_name="homepromomodal", name="image_tablet_portrait"),
        migrations.RemoveField(model_name="homepromomodal", name="image_tablet_landscape"),
        migrations.RemoveField(model_name="homepromomodal", name="image_desktop_portrait"),
        migrations.RemoveField(model_name="homepromomodal", name="image_desktop_landscape"),
    ]
