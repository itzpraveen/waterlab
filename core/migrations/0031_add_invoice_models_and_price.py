import decimal
import uuid

from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0030_make_customer_email_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='testparameter',
            name='price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=decimal.Decimal('0.00'),
                help_text='Default price used when generating invoices.',
                max_digits=12,
                verbose_name='Unit Price',
            ),
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('invoice_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('invoice_number', models.CharField(blank=True, max_length=50, null=True, verbose_name='Invoice Number')),
                ('issued_on', models.DateField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('ISSUED', 'Issued'), ('PAID', 'Paid'), ('VOID', 'Void')], default='ISSUED', max_length=20)),
                ('subtotal', models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12)),
                ('tax_rate', models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), help_text='Tax rate (%)', max_digits=5)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12)),
                ('total', models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sample', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='invoice', to='core.sample')),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceLineItem',
            fields=[
                ('line_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=255)),
                ('quantity', models.DecimalField(decimal_places=2, default=decimal.Decimal('1.00'), max_digits=10)),
                ('unit_price', models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12)),
                ('amount', models.DecimalField(decimal_places=2, default=decimal.Decimal('0.00'), max_digits=12)),
                ('position', models.PositiveIntegerField(default=0)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='line_items', to='core.invoice')),
                ('parameter', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.testparameter')),
            ],
            options={
                'ordering': ['position', 'description'],
            },
        ),
        migrations.AddConstraint(
            model_name='invoice',
            constraint=models.UniqueConstraint(
                fields=('invoice_number',),
                condition=Q(invoice_number__isnull=False) & ~Q(invoice_number=''),
                name='unique_invoice_number',
            ),
        ),
    ]
