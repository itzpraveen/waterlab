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
                'placeholder': 'e.g., M.G. Road, Near Temple'
            }),
            'village_town_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Varkala, Kochi'
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
        
        # Load address data for district choices
        try:
            with open('static/js/kerala_address_data.json', 'r') as f:
                address_data = json.load(f)
            district_choices = [('', '---------')] + [(district, district) for district in address_data.keys()]
        except FileNotFoundError:
            # Fallback if JSON file is not found
            address_data = {}
            district_choices = [('', '---------'), ('Data not found', 'Data not found')]

        self.fields['district'] = forms.ChoiceField(
            choices=district_choices,
            widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_district'})
        )
        # Taluk and Panchayat will be populated by JavaScript, so start with empty choices
        # but ensure they are ChoiceFields so the submitted value is validated against choices (dynamically set by JS)
        self.fields['taluk'] = forms.ChoiceField(
            choices=[('', '---------')], 
            widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_taluk'}),
            required=True # Or False, depending on your model
        )
        self.fields['panchayat_municipality'] = forms.ChoiceField(
            choices=[('', '---------')],
            widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_panchayat_municipality'}),
            required=True # Or False, depending on your model
        )
        # Ensure the field name matches the model if it was 'panchayat_municipality'
        # If your model field is 'panchayat_municipality_corporation', adjust accordingly.
        # For now, assuming 'panchayat_municipality' is the correct field name in the model and form.

class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = ['customer', 'collection_datetime', 'sample_source', 'collected_by', 'tests_requested']
        widgets = {
            'collection_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'sample_source': forms.Select(attrs={'class': 'form-control'}),
            'collected_by': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name of person who collected the sample'
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
        
        # Check if test parameters exist
        from .models import TestParameter
        if not TestParameter.objects.exists():
            # Create a helpful message
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
