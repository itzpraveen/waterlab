from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_performance_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='testparameter',
            name='display_order',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Lower numbers appear earlier in lists and reports',
            ),
        ),
        migrations.AlterModelOptions(
            name='testparameter',
            options={'ordering': ['display_order', 'name']},
        ),
    ]
