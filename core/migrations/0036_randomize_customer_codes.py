import secrets

from django.db import migrations
from django.db.models import Q


ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
RANDOM_LENGTH = 6


def generate_code(existing_codes):
    for _ in range(50):
        suffix = ''.join(secrets.choice(ALPHABET) for _ in range(RANDOM_LENGTH))
        candidate = f"C-{suffix}"
        if candidate not in existing_codes:
            existing_codes.add(candidate)
            return candidate
    raise RuntimeError("Could not generate a unique customer code.")


def randomize_sequential_customer_codes(apps, schema_editor):
    Customer = apps.get_model('core', 'Customer')
    existing_codes = set(
        Customer.objects
        .exclude(customer_code__isnull=True)
        .exclude(customer_code='')
        .exclude(customer_code__startswith='CUST')
        .values_list('customer_code', flat=True)
    )

    customers = Customer.objects.filter(
        Q(customer_code__startswith='CUST') | Q(customer_code__isnull=True) | Q(customer_code='')
    ).order_by('name', 'customer_id')

    for customer in customers:
        customer.customer_code = generate_code(existing_codes)
        customer.save(update_fields=['customer_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_customer_customer_code'),
    ]

    operations = [
        migrations.RunPython(randomize_sequential_customer_codes, migrations.RunPython.noop),
    ]
