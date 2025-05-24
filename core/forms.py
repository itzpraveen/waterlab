from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Customer, Sample

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'name', 'email', 'phone', 
            'house_name_door_no', 'street_locality_landmark', 'village_town_city',
            'panchayat_municipality', 'taluk', 'district', 'pincode'
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
            'panchayat_municipality': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Varkala Panchayat, Kochi Corporation'
            }),
            'taluk': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Chirayinkeezhu'
            }),
            'district': forms.Select(attrs={
                'class': 'form-control'
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '6-digit PIN code',
                'maxlength': '6'
            }),
        }

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

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Current password'
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'New password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })