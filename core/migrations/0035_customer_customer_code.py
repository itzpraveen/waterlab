from django.db import migrations, models
from django.utils import timezone


def assign_customer_codes(apps, schema_editor):
    Customer = apps.get_model('core', 'Customer')
    current_year = timezone.now().year
    prefix = f"CUST{current_year}-"

    for sequence, customer in enumerate(
        Customer.objects.filter(customer_code__isnull=True).order_by('name', 'customer_id'),
        start=1,
    ):
        customer.customer_code = f"{prefix}{sequence:04d}"
        customer.save(update_fields=['customer_code'])


def clear_customer_codes(apps, schema_editor):
    Customer = apps.get_model('core', 'Customer')
    Customer.objects.update(customer_code=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_customer_customer_district_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='customer_code',
            field=models.CharField(
                blank=True,
                editable=False,
                help_text='Privacy-safe code used to identify customer bottles in the lab.',
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(assign_customer_codes, clear_customer_codes),
        migrations.AlterField(
            model_name='customer',
            name='customer_code',
            field=models.CharField(
                blank=True,
                editable=False,
                help_text='Privacy-safe code used to identify customer bottles in the lab.',
                max_length=20,
                unique=True,
            ),
        ),
    ]
