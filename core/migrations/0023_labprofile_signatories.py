from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_resultstatusoverride'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='labprofile',
            name='signatory_bio_manager',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='default_bio_manager_profiles',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Default Deputy Technical Manager – Biological',
            ),
        ),
        migrations.AddField(
            model_name='labprofile',
            name='signatory_chem_manager',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='default_chem_manager_profiles',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Default Technical Manager – Chemical',
            ),
        ),
        migrations.AddField(
            model_name='labprofile',
            name='signatory_food_analyst',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='default_food_analyst_profiles',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Default Food Analyst',
            ),
        ),
    ]
