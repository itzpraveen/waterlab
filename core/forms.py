import json # Added for loading address data
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.utils import timezone
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

class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = ['customer', 'collection_datetime', 'sample_source', 'collected_by', 'referred_by', 'tests_requested']
        widgets = {
            'collection_datetime': forms.TextInput(attrs={
                'class': 'form-control datepicker', # Changed type, added 'datepicker' class
                'placeholder': 'Select date, then type time (HH:MM:SS)' # Added placeholder
            }),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'sample_source': forms.Select(attrs={'class': 'form-control'}),
            'collected_by': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name of person who collected the sample'
            }),
            'referred_by': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name of person who referred the sample'
            }),
            'tests_requested': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_collection_datetime(self):
        collection_datetime = self.cleaned_data.get('collection_datetime')
        if collection_datetime and collection_datetime > timezone.now():
            raise ValidationError("Collection date cannot be in the future.")
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
        
        # Group parameters by category
        self.grouped_parameters = {}
        parameters = TestParameter.objects.filter(parent__isnull=True).prefetch_related('children')
        
        for parent in parameters:
            self.grouped_parameters[parent] = parent.children.all()
            
        # Also get parameters that have no parent and no category (standalone)
        standalone_params = TestParameter.objects.filter(parent__isnull=True, category__isnull=True)
        if standalone_params.exists():
            self.grouped_parameters['Standalone'] = standalone_params

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
        widget=forms.TextInput(attrs={'class': 'form-control'}) # Materialize uses 'validate' not 'form-control'
    )
    observation = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'materialize-textarea', 'rows': 2}) # Materialize specific class
    )

class TestParameterForm(forms.ModelForm):
    class Meta:
        model = TestParameter
        fields = ['name', 'unit', 'standard_method', 'min_permissible_limit', 'max_permissible_limit']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'validate'}),
            'unit': forms.TextInput(attrs={'class': 'validate'}),
            'standard_method': forms.TextInput(attrs={'class': 'validate'}),
            'min_permissible_limit': forms.NumberInput(attrs={'class': 'validate', 'step': 'any'}),
            'max_permissible_limit': forms.NumberInput(attrs={'class': 'validate', 'step': 'any'}),
        }
        labels = {
            'min_permissible_limit': 'Min. Permissible Limit',
            'max_permissible_limit': 'Max. Permissible Limit',
        }
        help_texts = {
            'min_permissible_limit': 'Leave blank if no minimum limit.',
            'max_permissible_limit': 'Leave blank if no maximum limit.',
        }

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
