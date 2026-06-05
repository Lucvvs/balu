from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0018_update_homepromomodal_copy"),
    ]

    operations = [
        migrations.AlterField(
            model_name="homepromomodal",
            name="tagline",
            field=models.CharField(
                default="Descuentos sobre descuentos",
                help_text="Subtítulo que aparece debajo del título principal en el modal.",
                max_length=200,
                verbose_name="Subtítulo",
            ),
        ),
    ]
