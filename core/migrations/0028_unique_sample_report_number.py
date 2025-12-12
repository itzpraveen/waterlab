from django.db import migrations, models
from django.db.models import Count, Q
from django.utils import timezone


def normalize_and_deduplicate_report_numbers(apps, schema_editor):
    Sample = apps.get_model('core', 'Sample')

    # Normalize empty strings to NULL so they don't violate the unique constraint.
    Sample.objects.filter(report_number='').update(report_number=None)

    duplicates = (
        Sample.objects.exclude(report_number__isnull=True)
        .values('report_number')
        .annotate(count=Count('pk'))
        .filter(count__gt=1)
    )

    if not duplicates:
        return

    for dup in duplicates:
        report_number = dup['report_number']
        if not report_number:
            continue

        samples = list(
            Sample.objects.filter(report_number=report_number)
            .order_by('collection_datetime', 'pk')
        )
        if len(samples) <= 1:
            continue

        # Preserve the first occurrence; re-number the rest.
        try:
            year = int(str(report_number)[3:7])
        except Exception:
            year = timezone.now().year
        prefix = f'RPT{year}-'

        for sample in samples[1:]:
            last_with_number = (
                Sample.objects.exclude(pk=sample.pk)
                .exclude(report_number__isnull=True)
                .exclude(report_number__exact='')
                .filter(report_number__startswith=prefix)
                .order_by('report_number')
                .last()
            )
            sequence = 1
            if last_with_number and last_with_number.report_number:
                try:
                    sequence = int(str(last_with_number.report_number).split('-')[-1]) + 1
                except Exception:
                    sequence = 1

            candidate = f'{prefix}{sequence:04d}'
            while Sample.objects.filter(report_number=candidate).exists():
                sequence += 1
                candidate = f'{prefix}{sequence:04d}'

            sample.report_number = candidate
            sample.save(update_fields=['report_number'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_make_customer_address_optional'),
    ]

    operations = [
        migrations.RunPython(normalize_and_deduplicate_report_numbers, noop_reverse),
        migrations.AddConstraint(
            model_name='sample',
            constraint=models.UniqueConstraint(
                fields=['report_number'],
                condition=Q(report_number__isnull=False) & ~Q(report_number=''),
                name='unique_sample_report_number',
            ),
        ),
    ]

