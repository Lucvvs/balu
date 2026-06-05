from django.db import migrations, models


def create_default_home_promo_modal(apps, schema_editor):
    HomePromoModal = apps.get_model("shop", "HomePromoModal")
    if not HomePromoModal.objects.exists():
        HomePromoModal.objects.create(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0016_product_show_variant_badges"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomePromoModal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "is_active",
                    models.BooleanField(
                        default=False,
                        help_text="Muestra el modal emergente al entrar a la página de inicio.",
                        verbose_name="Activo",
                    ),
                ),
                (
                    "headline",
                    models.CharField(
                        default="Los mejores precios, siempre",
                        max_length=120,
                        verbose_name="Título principal",
                    ),
                ),
                (
                    "tagline",
                    models.CharField(
                        default="No esperes al CyberDay. En MotoMoto los buenos precios son todos los días.",
                        max_length=200,
                        verbose_name="Subtítulo",
                    ),
                ),
                (
                    "body_text",
                    models.TextField(
                        default=(
                            "Síguenos en Instagram y escríbenos un mensaje. "
                            "Te enviamos un cupón exclusivo para tu próxima compra."
                        ),
                        verbose_name="Texto descriptivo",
                    ),
                ),
                (
                    "discount_percent",
                    models.PositiveSmallIntegerField(default=10, verbose_name="Porcentaje de descuento"),
                ),
                (
                    "instagram_url",
                    models.URLField(
                        default="https://www.instagram.com/motomotochile.cl/",
                        max_length=255,
                        verbose_name="URL de Instagram",
                    ),
                ),
                (
                    "instagram_handle",
                    models.CharField(
                        default="@motomotochile.cl",
                        max_length=80,
                        verbose_name="Usuario de Instagram",
                    ),
                ),
                (
                    "cta_label",
                    models.CharField(
                        default="Ir a Instagram",
                        max_length=60,
                        verbose_name="Texto del botón principal",
                    ),
                ),
                (
                    "show_delay_ms",
                    models.PositiveIntegerField(
                        default=1400,
                        help_text="Tiempo de espera tras cargar la página antes de abrir el modal.",
                        verbose_name="Retardo antes de mostrar (ms)",
                    ),
                ),
                (
                    "dismiss_days",
                    models.PositiveIntegerField(
                        default=7,
                        help_text="Si el visitante cierra el modal, no se vuelve a mostrar durante este período.",
                        verbose_name="Días sin mostrar tras cerrar",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Última actualización")),
            ],
            options={
                "verbose_name": "Modal promocional (inicio)",
                "verbose_name_plural": "Modal promocional (inicio)",
            },
        ),
        migrations.RunPython(create_default_home_promo_modal, migrations.RunPython.noop),
    ]
