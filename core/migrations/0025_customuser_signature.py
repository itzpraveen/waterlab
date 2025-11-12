from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_backfill_report_numbers'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='signature',
            field=models.ImageField(blank=True, null=True, upload_to='signatures/'),
        ),
    ]
