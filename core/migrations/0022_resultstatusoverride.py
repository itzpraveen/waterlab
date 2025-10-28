import uuid

import django.db.models.deletion
from django.db import migrations, models


RESULT_STATUS_CHOICES = [
    ('WITHIN_LIMITS', 'Within limits'),
    ('ABOVE_LIMIT', 'Above maximum'),
    ('BELOW_LIMIT', 'Below minimum'),
    ('NON_NUMERIC', 'Non-numeric'),
    ('UNKNOWN', 'Unknown'),
]


def seed_default_overrides(apps, schema_editor):
    ResultStatusOverride = apps.get_model('core', 'ResultStatusOverride')
    ResultStatusOverride.objects.update_or_create(
        parameter=None,
        text_value='BDL',
        defaults={
            'status': 'WITHIN_LIMITS',
            'is_active': True,
            'normalized_value': 'bdl',
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_testparameter_max_limit_display'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResultStatusOverride',
            fields=[
                ('override_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('text_value', models.CharField(help_text='Result value (case-insensitive) that should trigger the selected status.', max_length=255)),
                ('normalized_value', models.CharField(db_index=True, editable=False, max_length=255)),
                ('status', models.CharField(choices=RESULT_STATUS_CHOICES, default='WITHIN_LIMITS', max_length=32)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parameter', models.ForeignKey(blank=True, help_text='Leave blank to apply this override to all parameters.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='status_overrides', to='core.testparameter')),
            ],
            options={
                'ordering': ['normalized_value', 'parameter__name'],
                'unique_together': {('parameter', 'normalized_value')},
            },
        ),
        migrations.AddIndex(
            model_name='resultstatusoverride',
            index=models.Index(fields=['normalized_value', 'parameter'], name='result_override_lookup_idx'),
        ),
        migrations.RunPython(seed_default_overrides, migrations.RunPython.noop),
    ]
