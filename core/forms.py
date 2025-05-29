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
        
        # Load address data
        try:
            with open('static/js/kerala_address_data.json', 'r') as f:
                address_data = json.load(f)
        except FileNotFoundError:
            address_data = {}
            # Consider logging this error or raising a more specific exception if the file is critical
        
        # Use KERALA_DISTRICTS from the model for district choices to ensure consistency (value, display_name)
        # The first element is (value_to_store, display_name_in_dropdown)
        # The value_to_store (e.g., 'thiruvananthapuram') must match keys in kerala_address_data.json
        self.fields['district'] = forms.ChoiceField(
            choices=[('', '---------')] + Customer.KERALA_DISTRICTS, # Using model's choices
            widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_district'}),
            required=True 
        )
        # Taluk and Panchayat will be populated by JavaScript, so start with empty choices
        # but ensure they are ChoiceFields so the submitted value is validated against choices (dynamically set by JS)
        self.fields['taluk'] = forms.ChoiceField(
            choices=[('', '---------')],
            widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_taluk', 'disabled': 'disabled'}), # Initially disabled
            required=True 
        )
        self.fields['panchayat_municipality'] = forms.ChoiceField(
            choices=[('', '---------')],
            widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_panchayat_municipality', 'disabled': 'disabled'}),
            required=True 
        )
        
        self.address_data = address_data

        # If form is bound with data, update choices for taluk and panchayat
        # This ensures that the ChoiceField validation uses the correct dynamic choices.
        if self.is_bound:
            data = self.data or {} # Use self.data if available (POST), otherwise empty dict
            
            # Update Taluk choices based on submitted District
            district_val = data.get('district')
            if district_val and district_val in self.address_data:
                taluk_keys = self.address_data[district_val].keys()
                self.fields['taluk'].choices = [('', '---------')] + [(t, t) for t in taluk_keys]
                self.fields['taluk'].widget.attrs.pop('disabled', None) # Enable if it was disabled

                # Update Panchayat choices based on submitted District and Taluk
                taluk_val = data.get('taluk')
                if taluk_val and taluk_val in self.address_data[district_val]:
                    panchayat_list = self.address_data[district_val][taluk_val]
                    self.fields['panchayat_municipality'].choices = [('', '---------')] + [(p, p) for p in panchayat_list]
                    self.fields['panchayat_municipality'].widget.attrs.pop('disabled', None) # Enable
                elif not taluk_val : # No taluk selected, keep panchayat disabled with default choice
                    self.fields['panchayat_municipality'].choices = [('', '---------')]
                    self.fields['panchayat_municipality'].widget.attrs['disabled'] = 'disabled'

            elif not district_val: # No district selected, keep taluk and panchayat disabled
                self.fields['taluk'].choices = [('', '---------')]
                self.fields['taluk'].widget.attrs['disabled'] = 'disabled'
                self.fields['panchayat_municipality'].choices = [('', '---------')]
                self.fields['panchayat_municipality'].widget.attrs['disabled'] = 'disabled'

        # If editing an existing instance, pre-populate choices based on instance data
        elif self.instance and self.instance.pk:
            instance_district = self.instance.district
            if instance_district and instance_district in self.address_data:
                taluk_keys = self.address_data[instance_district].keys()
                self.fields['taluk'].choices = [('', '---------')] + [(t, t) for t in taluk_keys]
                self.fields['taluk'].widget.attrs.pop('disabled', None)

                instance_taluk = self.instance.taluk
                if instance_taluk and instance_taluk in self.address_data[instance_district]:
                    panchayat_list = self.address_data[instance_district][instance_taluk]
                    self.fields['panchayat_municipality'].choices = [('', '---------')] + [(p, p) for p in panchayat_list]
                    self.fields['panchayat_municipality'].widget.attrs.pop('disabled', None)


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
