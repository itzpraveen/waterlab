from django.db import migrations
from django.utils import timezone


def extract_sequence(report_number: str):
    try:
        return int(report_number.split('-')[-1])
    except (AttributeError, ValueError, IndexError):
        return None


def extract_year(report_number: str):
    try:
        return int(report_number[3:7])
    except (TypeError, ValueError):
        return None


def backfill_report_numbers(apps, schema_editor):
    Sample = apps.get_model('core', 'Sample')

    existing_numbers = Sample.objects.exclude(report_number__isnull=True).exclude(report_number__exact='')

    max_sequence_by_year = {}
    for sample in existing_numbers:
        year = extract_year(sample.report_number)
        seq = extract_sequence(sample.report_number)
        if year and seq:
            max_sequence_by_year[year] = max(max_sequence_by_year.get(year, 0), seq)

    eligible_statuses = ['RESULTS_ENTERED', 'REVIEW_PENDING', 'REPORT_APPROVED', 'REPORT_SENT']
    to_backfill = Sample.objects.filter(report_number__isnull=True, current_status__in=eligible_statuses).order_by('collection_datetime', 'pk')

    current_year = timezone.now().year
    for sample in to_backfill:
        year = current_year
        prefix = f'RPT{year}-'
        next_seq = max_sequence_by_year.get(year, 0) + 1
        sample.report_number = f'{prefix}{next_seq:04d}'
        sample.save(update_fields=['report_number'])
        max_sequence_by_year[year] = next_seq


def noop_reverse(apps, schema_editor):
    # No reverse action; historical report numbers should remain.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_labprofile_signatories'),
    ]

    operations = [
        migrations.RunPython(backfill_report_numbers, noop_reverse),
    ]
