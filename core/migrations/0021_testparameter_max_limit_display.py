from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_labprofile_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='testparameter',
            name='max_limit_display',
            field=models.CharField(
                max_length=100,
                blank=True,
                null=True,
                help_text="Override displayed maximum limit text (e.g., 'Absent/ml').",
            ),
        ),
    ]
