from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_unique_sample_report_number'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text='Staff user who registered this customer.',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='customers_created',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='sample',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text='Staff user who registered this sample.',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='samples_created',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

