from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0019_remove_cyberday_tagline_help"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepromomodal",
            name="display_mode",
            field=models.CharField(
                choices=[
                    ("structured", "Contenido configurado (textos + Instagram)"),
                    ("image", "Solo imagen (pieza publicitaria)"),
                ],
                default="structured",
                help_text="Elige si se muestra el diseño con textos o solo una imagen a pantalla completa del modal.",
                max_length=20,
                verbose_name="Tipo de modal",
            ),
        ),
        migrations.AddField(
            model_name="homepromomodal",
            name="promo_image",
            field=models.ImageField(
                blank=True,
                help_text="Obligatoria en modo imagen. Debe cubrir todo el modal; se recomienda formato vertical.",
                null=True,
                upload_to="home_promo/",
                verbose_name="Imagen promocional",
            ),
        ),
        migrations.AddField(
            model_name="homepromomodal",
            name="link_url",
            field=models.URLField(
                default="https://www.instagram.com/motomotochile.cl/",
                help_text="Destino al tocar la imagen. Por defecto Instagram.",
                max_length=255,
                verbose_name="URL al hacer clic (modo imagen)",
            ),
        ),
        migrations.AlterField(
            model_name="homepromomodal",
            name="dismiss_days",
            field=models.PositiveIntegerField(
                default=7,
                help_text="Si el visitante marca “no volver a mostrar”, no se vuelve a mostrar durante este período.",
                verbose_name="Días sin mostrar tras cerrar",
            ),
        ),
    ]
