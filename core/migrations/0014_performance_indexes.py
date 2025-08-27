from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_auto_populate_results'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['name'], name='customer_name_idx'),
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['phone'], name='customer_phone_idx'),
        ),
        migrations.AddIndex(
            model_name='sample',
            index=models.Index(fields=['current_status'], name='sample_status_idx'),
        ),
        migrations.AddIndex(
            model_name='sample',
            index=models.Index(fields=['collection_datetime'], name='sample_collected_at_idx'),
        ),
    ]

