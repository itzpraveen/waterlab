from django.db import migrations, models
import django.db.models.functions.text


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_performance_indexes'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='testparameter',
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower('name'), name='uq_testparameter_name_ci'
            ),
        ),
    ]

