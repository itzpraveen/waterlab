from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_customer_sample_created_by'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
    ]
