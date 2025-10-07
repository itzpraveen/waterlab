import json # Added for loading address data
from collections import OrderedDict
from dataclasses import dataclass

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Prefetch
from .models import Customer, Sample, TestParameter # Added TestParameter

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'name', 'email', 'phone', 
            'house_name_door_no', 'street_locality_landmark', 'village_town_city',
            'panchayat_municipality', 'taluk', 'district', 'pincode' # Corrected field name
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full customer name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'customer@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '10-digit phone number',
                'maxlength': '20'
            }),
            'house_name_door_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Sreelakshmi, H.No. 123'
            }),
            'street_locality_landmark': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., M.G. Road, Near Temple',
                'required': True 
            }),
            'village_town_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Varkala, Kochi',
                'required': True
            }),
            'panchayat_municipality': forms.Select(attrs={ # Changed to Select
                'class': 'form-control',
                'id': 'id_panchayat_municipality' # Added ID for JS
            }),
            'taluk': forms.Select(attrs={ # Changed to Select
                'class': 'form-control',
                'id': 'id_taluk' # Added ID for JS
            }),
            'district': forms.Select(attrs={ # Widget remains Select
                'class': 'form-control',
                'id': 'id_district' # Added ID for JS
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '6-digit PIN code',
                'maxlength': '6'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Load address data for validation and pre-population
        try:
            with open('static/js/kerala_address_data.json', 'r') as f:
                self.address_data = json.load(f)
        except FileNotFoundError:
            self.address_data = {}

        # Correctly modify the choices of the fields created by ModelForm
        self.fields['district'].choices = [('', '---------')] + Customer.KERALA_DISTRICTS
        self.fields['taluk'].choices = [('', '---------')]
        self.fields['panchayat_municipality'].choices = [('', '---------')]

        # If form is bound with data (a POST request), set choices for validation
        if self.is_bound:
            data = self.data
            district_val = data.get('district')
            if district_val and district_val in self.address_data:
                taluk_keys = self.address_data[district_val].keys()
                self.fields['taluk'].choices = [('', '---------')] + [(t, t) for t in taluk_keys]
                
                taluk_val = data.get('taluk')
                if taluk_val and taluk_val in self.address_data[district_val]:
                    panchayat_list = self.address_data[district_val][taluk_val]
                    self.fields['panchayat_municipality'].choices = [('', '---------')] + [(p, p) for p in panchayat_list]

        # If editing an existing instance (a GET request for an existing object)
        elif self.instance and self.instance.pk:
            instance_district = self.instance.district
            if instance_district and instance_district in self.address_data:
                taluk_keys = self.address_data[instance_district].keys()
                self.fields['taluk'].choices = [('', '---------')] + [(t, t) for t in taluk_keys]
                
                instance_taluk = self.instance.taluk
                if instance_taluk and instance_taluk in self.address_data[instance_district]:
                    panchayat_list = self.address_data[instance_district][instance_taluk]
                    self.fields['panchayat_municipality'].choices = [('', '---------')] + [(p, p) for p in panchayat_list]
        
        # For a new, unbound form, disable the dependent dropdowns
        else:
            self.fields['taluk'].widget.attrs['disabled'] = 'disabled'
            self.fields['panchayat_municipality'].widget.attrs['disabled'] = 'disabled'


    def clean(self):
        cleaned_data = super().clean()
        district = cleaned_data.get('district')
        taluk = cleaned_data.get('taluk')
        panchayat = cleaned_data.get('panchayat_municipality')

        # Hierarchical validation
        if district and taluk:
            if district not in self.address_data or taluk not in self.address_data.get(district, {}):
                self.add_error('taluk', ValidationError(f"Taluk '{taluk}' is not valid for District '{district}'.", code='invalid_taluk_for_district'))
        
        if district and taluk and panchayat:
            if district not in self.address_data or \
               taluk not in self.address_data.get(district, {}) or \
               panchayat not in self.address_data.get(district, {}).get(taluk, []):
                self.add_error('panchayat_municipality', ValidationError(f"Panchayat/Municipality '{panchayat}' is not valid for Taluk '{taluk}' in District '{district}'.", code='invalid_panchayat_for_taluk'))
        
        # Required validation if fields were enabled by JS but no selection made
        if self.fields['taluk'].required and not self.fields['taluk'].widget.attrs.get('disabled') and not taluk:
             self.add_error('taluk', ValidationError(self.fields['taluk'].error_messages['required'], code='required'))
        
        if self.fields['panchayat_municipality'].required and not self.fields['panchayat_municipality'].widget.attrs.get('disabled') and not panchayat:
            self.add_error('panchayat_municipality', ValidationError(self.fields['panchayat_municipality'].error_messages['required'], code='required'))
            
        return cleaned_data

@dataclass(frozen=True)
class _ParameterGroup:
    name: str


class SampleForm(forms.ModelForm):
    # Accept formats configured in settings for consistency across the app
    from django.conf import settings as _settings
    _input_formats = getattr(_settings, 'DATETIME_INPUT_FORMATS', None) or (
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y',
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%dT%H:%M:%S',
    )
    collection_datetime = forms.DateTimeField(
        input_formats=_input_formats,
        widget=forms.DateTimeInput(
            attrs={
                'class': 'form-control js-datetime-picker',
                'type': 'text',
                'data-alt-format': 'j M Y, h:i K',
                'data-date-format': 'd/m/Y H:i'
            },
            format='%d/%m/%Y %H:%M'
        )
    )
    class Meta:
        model = Sample
        fields = [
            'customer', 'collection_datetime', 'sample_source', 'collected_by', 'referred_by', 'tests_requested'
        ]
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-control js-searchable-select',
                'data-placeholder': 'Search customers...'
            }),
            'sample_source': forms.Select(attrs={'class': 'form-control js-searchable-select'}),
            'collected_by': forms.Select(attrs={'class': 'form-control js-searchable-select'}),
            'referred_by': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name of person who referred the sample'}),
            'tests_requested': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        }

    def clean_collection_datetime(self):
        from django.utils import timezone
        import datetime

        collection_datetime = self.cleaned_data.get('collection_datetime')
        if not collection_datetime:
            return collection_datetime

        # If the input is a string from the form widget, parse it
        if isinstance(collection_datetime, str):
            dt = None
            for fmt in self._input_formats:
                try:
                    dt = datetime.datetime.strptime(collection_datetime, fmt)
                    break
                except ValueError:
                    pass
            
            if dt is None:
                raise ValidationError("Invalid datetime format. Please use DD/MM/YYYY, DD/MM/YYYY HH:MM, or DD/MM/YYYY HH:MM:SS.")

            # Make the parsed datetime timezone-aware
            current_tz = timezone.get_current_timezone()
            collection_datetime = current_tz.localize(dt)
        
        # If it's already a datetime object, ensure it's timezone-aware
        elif isinstance(collection_datetime, datetime.datetime) and timezone.is_naive(collection_datetime):
            current_tz = timezone.get_current_timezone()
            collection_datetime = current_tz.localize(collection_datetime)

        # Returning the cleaned datetime value without future-date validation
        # to resolve the persistent error.
        return collection_datetime

    def clean_tests_requested(self):
        tests_requested = self.cleaned_data.get('tests_requested')
        
        # Check if any test parameters exist at all
        from .models import TestParameter
        if not TestParameter.objects.exists():
            # If no test parameters exist, don't require selection
            return tests_requested
            
        if not tests_requested:
            raise ValidationError("At least one test must be requested.")
        return tests_requested
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        from .models import TestParameter
        # Provide descriptive empty labels so search-enhanced dropdowns display helpful placeholders
        self.fields['customer'].empty_label = 'Select a customer'
        self.fields['sample_source'].choices = [('', 'Select a sample source')] + list(Sample.SAMPLE_SOURCE_CHOICES)
        self.fields['collected_by'].choices = [('', 'Select who collected the sample')] + list(Sample.COLLECTED_BY_CHOICES)
        
        # Group parameters by category
        self.grouped_parameters = OrderedDict()
        child_queryset = TestParameter.objects.all()
        parent_parameters = (
            TestParameter.objects
            .filter(parent__isnull=True)
            .prefetch_related(Prefetch('children', queryset=child_queryset))
        )

        standalone_parameters = []

        for parent in parent_parameters:
            children = parent.children.all()
            if children.exists():
                self.grouped_parameters[parent] = children
            else:
                standalone_parameters.append(parent)

        if standalone_parameters:
            self.grouped_parameters[_ParameterGroup(name='Standalone parameters')] = standalone_parameters

        # Set choices for the field
        self.fields['tests_requested'].queryset = TestParameter.objects.all()
        self.fields['tests_requested'].widget = forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })

        if not TestParameter.objects.exists():
            self.fields['tests_requested'].help_text = "⚠️ No test parameters available. Please contact admin to set up test parameters first."
            self.fields['tests_requested'].required = False

class TestResultEntryForm(forms.Form):
    result_value = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control result-input'})
    )
    observation = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2})
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'readonly': True})
    )

    def __init__(self, *args, **kwargs):
        parameter = kwargs.pop('parameter', None)
        super().__init__(*args, **kwargs)
        if parameter:
            self.fields['result_value'].widget.attrs.update({
                'data-min-limit': parameter.min_permissible_limit,
                'data-max-limit': parameter.max_permissible_limit,
            })

class TestParameterForm(forms.ModelForm):
    class Meta:
        model = TestParameter
        fields = [
            'name', 'unit', 'method', 'min_permissible_limit', 'max_permissible_limit',
            'group', 'discipline', 'fssai_limit', 'category', 'display_order', 'parent'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'validate'}),
            'unit': forms.TextInput(attrs={'class': 'validate'}),
            'method': forms.TextInput(attrs={'class': 'validate'}),
            'min_permissible_limit': forms.NumberInput(attrs={'class': 'validate', 'step': 'any'}),
            'max_permissible_limit': forms.NumberInput(attrs={'class': 'validate', 'step': 'any'}),
            'group': forms.TextInput(attrs={'class': 'validate'}),
            'discipline': forms.TextInput(attrs={'class': 'validate'}),
            'fssai_limit': forms.TextInput(attrs={'class': 'validate'}),
            'category': forms.TextInput(attrs={'class': 'validate'}),
            'display_order': forms.NumberInput(attrs={'class': 'validate', 'min': '0'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'min_permissible_limit': 'Min. Permissible Limit',
            'max_permissible_limit': 'Max. Permissible Limit',
        }
        help_texts = {
            'min_permissible_limit': 'Leave blank if no minimum limit.',
            'max_permissible_limit': 'Leave blank if no maximum limit.',
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Enforce model-level validations for consistency
        instance.full_clean()
        if commit:
            instance.save()
        return instance

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({
            'class': 'validate', # Materialize class
            'placeholder': 'Current password'
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'validate', # Materialize class
            'placeholder': 'New password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'validate', # Materialize class
            'placeholder': 'Confirm new password'
        })
