from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_customuser_role_index'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('display_order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.AddField(
            model_name='testparameter',
            name='category_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='parameters', to='core.testcategory', verbose_name='Category'),
        ),
    ]
