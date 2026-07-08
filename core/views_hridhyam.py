from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .decorators import role_required
from .models import AuditTrail, Customer, Sample, TestCategory, TestParameter, TestResult
from .views_common import apply_user_scope


HRIDHYAM_SAMPLE_TYPE = 'HRIDHYAM'
HRIDHYAM_CATEGORY_NAME = 'Hridhyam Physical Water'
HRIDHYAM_ROLES = [
    'admin',
    'frontdesk',
    'lab',
    'bio_manager',
    'chem_manager',
    'solutions_manager',
]


@dataclass(frozen=True)
class HridhyamParameterSpec:
    key: str
    display_name: str
    parameter_name: str
    method: str
    unit: str
    limit_text: str
    min_value: Decimal | None
    max_value: Decimal | None
    placeholder: str
    print_top_mm: Decimal
    print_height_mm: Decimal

    @property
    def field_name(self) -> str:
        return f'result_{self.key}'


HRIDHYAM_PARAMETERS = [
    HridhyamParameterSpec('colour', 'Colour', 'Colour', 'Manual', 'Score', '0 - 5', Decimal('0'), Decimal('5'), '0-5', Decimal('119.6'), Decimal('10.8')),
    HridhyamParameterSpec('taste', 'Taste', 'Taste', 'Manual', 'Score', '0 - 5', Decimal('0'), Decimal('5'), '0-5', Decimal('130.4'), Decimal('10.4')),
    HridhyamParameterSpec('odor', 'Odor', 'Odor', 'Manual', 'Score', '0 - 5', Decimal('0'), Decimal('5'), '0-5', Decimal('140.8'), Decimal('11.4')),
    HridhyamParameterSpec('electrical_conductivity', 'Electrical Conductivity', 'Electrical Conductivity', 'E.C Meter', 'uS/cm', '50 - 500', Decimal('50'), Decimal('500'), '50-500', Decimal('152.2'), Decimal('11.6')),
    HridhyamParameterSpec('turbidity', 'Turbidity', 'Turbidity', 'Turbidity Meter', 'NTU', '0 - 5', Decimal('0'), Decimal('5'), '0-5', Decimal('163.8'), Decimal('11.5')),
    HridhyamParameterSpec('tds', 'TDS (Total Dissolved Solids)', 'TDS (Total Dissolved Solids)', 'TDS Meter', 'mg/L', '500', None, Decimal('500'), 'Max 500', Decimal('175.3'), Decimal('11.4')),
    HridhyamParameterSpec('ph', 'pH.', 'pH', 'pH Meter', 'pH', '6.5 - 8.5', Decimal('6.5'), Decimal('8.5'), '6.5-8.5', Decimal('186.7'), Decimal('11.6')),
]


def _as_decimal(value):
    cleaned = str(value or '').strip().lstrip('<>').replace(',', '')
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _result_remarks(spec: HridhyamParameterSpec, value: str) -> str:
    numeric_value = _as_decimal(value)
    if numeric_value is None:
        return ''
    if spec.min_value is not None and numeric_value < spec.min_value:
        return f'Below campaign reference range ({spec.limit_text})'
    if spec.max_value is not None and numeric_value > spec.max_value:
        return f'Above campaign reference range ({spec.limit_text})'
    return 'Within campaign reference range'


def _ensure_hridhyam_parameters() -> dict[str, TestParameter]:
    category, _ = TestCategory.objects.get_or_create(
        name=HRIDHYAM_CATEGORY_NAME,
        defaults={'display_order': 5},
    )

    parameters = {}
    for index, spec in enumerate(HRIDHYAM_PARAMETERS, start=1):
        parameter, created = TestParameter.objects.get_or_create(
            name=spec.parameter_name,
            defaults={
                'unit': spec.unit,
                'method': spec.method,
                'min_permissible_limit': spec.min_value,
                'max_permissible_limit': spec.max_value,
                'category_obj': category,
                'display_order': 500 + index,
            },
        )
        updates = {}
        if not parameter.unit:
            updates['unit'] = spec.unit
        if not parameter.method:
            updates['method'] = spec.method
        if parameter.min_permissible_limit is None and spec.min_value is not None:
            updates['min_permissible_limit'] = spec.min_value
        if parameter.max_permissible_limit is None and spec.max_value is not None:
            updates['max_permissible_limit'] = spec.max_value
        if not parameter.category_obj_id:
            updates['category_obj'] = category
        if updates:
            for field, value in updates.items():
                setattr(parameter, field, value)
            parameter.save(update_fields=list(updates.keys()))
        parameters[spec.key] = parameter
    return parameters


class HridhyamCampaignForm(forms.Form):
    name = forms.CharField(
        label='Name',
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
    )
    registration_number = forms.CharField(
        label='Reg.No.',
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Auto if blank'}),
    )
    place = forms.CharField(
        label='Place',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'address-level2'}),
    )
    contact = forms.CharField(
        label='Contact',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'tel', 'inputmode': 'tel'}),
    )
    source = forms.ChoiceField(
        label='Source',
        choices=Sample.SAMPLE_SOURCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    collection_datetime = forms.DateTimeField(
        label='Collected at',
        input_formats=('%Y-%m-%dT%H:%M', '%d/%m/%Y %H:%M'),
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
    )
    remarks = forms.CharField(
        label='Remarks',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.initial.get('collection_datetime'):
            self.initial['collection_datetime'] = timezone.localtime().strftime('%Y-%m-%dT%H:%M')
        for spec in HRIDHYAM_PARAMETERS:
            self.fields[spec.field_name] = forms.CharField(
                label=spec.display_name,
                max_length=255,
                widget=forms.TextInput(attrs={
                    'class': 'form-control hridhyam-result-input',
                    'inputmode': 'decimal',
                    'placeholder': spec.placeholder,
                    'data-min': '' if spec.min_value is None else str(spec.min_value),
                    'data-max': '' if spec.max_value is None else str(spec.max_value),
                    'data-limit': spec.limit_text,
                }),
            )

    def clean_registration_number(self):
        value = (self.cleaned_data.get('registration_number') or '').strip()
        if value and Sample.objects.filter(report_number__iexact=value).exists():
            raise forms.ValidationError('This registration number is already used.')
        return value

    def clean_collection_datetime(self):
        value = self.cleaned_data['collection_datetime']
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        if value > timezone.now() + timedelta(minutes=5):
            raise forms.ValidationError('Collection time cannot be in the future.')
        return value

    def clean(self):
        cleaned_data = super().clean()
        for spec in HRIDHYAM_PARAMETERS:
            value = (cleaned_data.get(spec.field_name) or '').strip()
            if not value:
                self.add_error(spec.field_name, 'Enter the test result.')
            else:
                cleaned_data[spec.field_name] = value
        return cleaned_data


def _form_result_fields(form: HridhyamCampaignForm):
    return [{'spec': spec, 'field': form[spec.field_name]} for spec in HRIDHYAM_PARAMETERS]


def _sample_source_label(sample: Sample) -> str:
    return dict(Sample.SAMPLE_SOURCE_CHOICES).get(sample.sample_source, sample.sample_source)


def _save_hridhyam_submission(form: HridhyamCampaignForm, user, request) -> Sample:
    cleaned = form.cleaned_data
    parameters = _ensure_hridhyam_parameters()
    collection_datetime = cleaned['collection_datetime']
    registration_number = cleaned.get('registration_number') or ''

    with transaction.atomic():
        customer = Customer.objects.filter(
            phone=cleaned['contact'],
            name__iexact=cleaned['name'],
        ).first()
        created_customer = False
        if not customer:
            customer = Customer.objects.create(
                name=cleaned['name'],
                phone=cleaned['contact'],
                village_town_city=cleaned['place'],
                district='Malappuram',
                created_by=user if user.is_authenticated else None,
            )
            created_customer = True
        else:
            customer.village_town_city = cleaned['place']
            if not customer.district:
                customer.district = 'Malappuram'
            if user.is_authenticated and not customer.created_by_id:
                customer.created_by = user
            customer.save(update_fields=['village_town_city', 'district', 'created_by', 'address'])

        sample = Sample(
            customer=customer,
            created_by=user if user.is_authenticated else None,
            collection_datetime=collection_datetime,
            date_received_at_lab=collection_datetime,
            sample_source=cleaned['source'],
            sampling_location=cleaned['place'],
            quantity_received='Field test',
            collected_by='LABORATORY_PERSON',
            referred_by='Hridhyam',
            current_status='REPORT_APPROVED',
            report_number=registration_number or None,
            sample_type=HRIDHYAM_SAMPLE_TYPE,
            sampling_procedure='Hridhyam campaign live field testing',
            deviations=cleaned.get('remarks') or '',
            test_commenced_on=collection_datetime.date(),
            test_completed_on=collection_datetime.date(),
        )
        sample.full_clean()
        sample.save()

        if not sample.report_number:
            sample.report_number = sample.display_id
            try:
                sample.save(update_fields=['report_number'])
            except IntegrityError:
                sample.report_number = f'H-{sample.display_id}'
                sample.save(update_fields=['report_number'])

        sample.tests_requested.set(parameters.values())

        technician = None
        if user.is_authenticated:
            is_lab_user = getattr(user, 'is_lab_tech', lambda: False)()
            is_admin_user = getattr(user, 'is_admin', lambda: False)()
            if is_lab_user or is_admin_user or user.is_superuser:
                technician = user

        for spec in HRIDHYAM_PARAMETERS:
            parameter = parameters[spec.key]
            value = cleaned[spec.field_name]
            result = TestResult(
                sample=sample,
                parameter=parameter,
                result_value=value,
                remarks=_result_remarks(spec, value),
                technician=technician,
            )
            result.full_clean()
            result.save()
            AuditTrail.log_change(user=user, action='CREATE', instance=result, request=request)

        AuditTrail.log_change(
            user=user,
            action='CREATE',
            instance=sample,
            new_values={
                'sample_type': sample.sample_type,
                'report_number': sample.report_number,
                'customer': customer.pk,
                'collection_datetime': collection_datetime,
            },
            request=request,
        )
        if created_customer:
            AuditTrail.log_change(user=user, action='CREATE', instance=customer, request=request)

        return sample


@role_required(HRIDHYAM_ROLES)
def hridhyam_campaign(request):
    if request.method == 'POST':
        form = HridhyamCampaignForm(request.POST)
        if form.is_valid():
            try:
                sample = _save_hridhyam_submission(form, request.user, request)
            except Exception as exc:
                messages.error(request, f'Unable to save Hridhyam report: {exc}')
            else:
                messages.success(request, f'Hridhyam report {sample.report_number} saved.')
                return redirect(f"{reverse('core:hridhyam_print', kwargs={'sample_id': sample.sample_id})}?auto=1")
    else:
        form = HridhyamCampaignForm()

    recent_samples = apply_user_scope(
        Sample.objects.filter(sample_type=HRIDHYAM_SAMPLE_TYPE)
        .select_related('customer')
        .order_by('-collection_datetime', '-display_id'),
        request.user,
    )[:10]

    return render(request, 'core/hridhyam_campaign.html', {
        'form': form,
        'result_fields': _form_result_fields(form),
        'recent_samples': recent_samples,
        'source_choices': dict(Sample.SAMPLE_SOURCE_CHOICES),
    })


@role_required(HRIDHYAM_ROLES)
def hridhyam_print(request, sample_id):
    sample = get_object_or_404(
        apply_user_scope(
            Sample.objects.filter(sample_type=HRIDHYAM_SAMPLE_TYPE).select_related('customer'),
            request.user,
        ),
        sample_id=sample_id,
    )
    results = {
        result.parameter.name: result
        for result in sample.results.select_related('parameter')
    }
    entries = []
    for spec in HRIDHYAM_PARAMETERS:
        result = results.get(spec.parameter_name)
        entries.append({
            'spec': spec,
            'result': result,
            'value': result.result_value if result else '',
            'remarks': result.remarks if result else '',
        })

    return render(request, 'core/hridhyam_print.html', {
        'sample': sample,
        'entries': entries,
        'reg_number': sample.report_number or sample.display_id,
        'place': sample.sampling_location or sample.customer.village_town_city,
        'source_label': _sample_source_label(sample),
        'remarks': sample.deviations or '',
        'autoprint': request.GET.get('auto') == '1',
    })
