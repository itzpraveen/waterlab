from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_customuser_signature'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='labprofile',
            name='signatory_solutions_manager',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='default_solutions_manager_profiles',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Default Chief of Solutions - Water Quality',
            ),
        ),
    ]
