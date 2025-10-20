from django.conf import settings
from django.db import migrations, models


def create_default_lab_profile(apps, schema_editor):
    LabProfile = apps.get_model('core', 'LabProfile')
    if LabProfile.objects.exists():
        return

    defaults = getattr(settings, 'WATERLAB_SETTINGS', {})
    LabProfile.objects.create(
        name=defaults.get('LAB_NAME', 'Biofix Laboratory'),
        address_line1=defaults.get('LAB_ADDRESS', ''),
        phone=defaults.get('LAB_PHONE', ''),
        email=defaults.get('LAB_EMAIL', ''),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_testcategory_and_parameter_fk'),
    ]

    operations = [
        migrations.CreateModel(
            name='LabProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Biofix Laboratory', max_length=150)),
                ('address_line1', models.CharField(blank=True, default='', max_length=255)),
                ('address_line2', models.CharField(blank=True, default='', max_length=255)),
                ('city', models.CharField(blank=True, default='', max_length=100)),
                ('state', models.CharField(blank=True, default='', max_length=100)),
                ('postal_code', models.CharField(blank=True, default='', max_length=20)),
                ('phone', models.CharField(blank=True, default='', max_length=50)),
                ('email', models.EmailField(blank=True, default='', max_length=254)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Lab profile',
                'verbose_name_plural': 'Lab profile',
            },
        ),
        migrations.RunPython(create_default_lab_profile, migrations.RunPython.noop),
    ]
