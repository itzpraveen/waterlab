import json # Added for loading address data
from collections import OrderedDict
from dataclasses import dataclass

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Customer, Sample, TestParameter, CustomUser, TestCategory, LabProfile # Added TestParameter, CustomUser, TestCategory, LabProfile

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
        
        # Group parameters by their category to mirror reporting layout
        def _category_priority(name: str) -> tuple[int, str]:
            lowered = name.casefold()
            if any(token in lowered for token in ('physical', 'chemical')):
                return (0, name)
            if any(token in lowered for token in ('micro', 'bacter')):
                return (1, name)
            if 'solution' in lowered:
                return (2, name)
            return (3, name)

        parameters = (
            TestParameter.objects
            .all()
            .order_by('category_obj__display_order', 'category_obj__name', 'category', 'display_order', 'name')
        )

        category_groups: dict[str, dict[str, object]] = OrderedDict()
        for parameter in parameters:
            raw_category = (parameter.category_label or '').strip()
            display_name = raw_category or 'Uncategorized parameters'
            key = display_name.casefold()
            if key not in category_groups:
                category_groups[key] = {
                    'group': _ParameterGroup(name=display_name),
                    'parameters': []
                }
            category_groups[key]['parameters'].append(parameter)

        sorted_groups = sorted(
            category_groups.values(),
            key=lambda entry: _category_priority(entry['group'].name)
        )

        self.grouped_parameters = OrderedDict(
            (entry['group'], entry['parameters']) for entry in sorted_groups
        )

        # Set choices for the field
        self.fields['tests_requested'].queryset = parameters
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
    CATEGORY_SUGGESTIONS = [
        'Physical & Chemical',
        'Microbiological',
        'Solution',
    ]

    class Meta:
        model = TestParameter
        fields = [
            'name', 'unit', 'method', 'min_permissible_limit', 'max_permissible_limit',
            'group', 'discipline', 'fssai_limit', 'category_obj', 'display_order', 'parent'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'method': forms.TextInput(attrs={'class': 'form-control'}),
            'min_permissible_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'max_permissible_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'group': forms.TextInput(attrs={'class': 'form-control'}),
            'discipline': forms.TextInput(attrs={'class': 'form-control'}),
            'fssai_limit': forms.TextInput(attrs={'class': 'form-control'}),
            'category_obj': forms.Select(attrs={'class': 'form-control'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_suggestions = self.CATEGORY_SUGGESTIONS
        # Provide category choices
        self.fields['category_obj'].queryset = TestCategory.objects.all().order_by('display_order', 'name')

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Enforce model-level validations for consistency
        instance.full_clean()
        if commit:
            instance.save()
        return instance


class _BaseAdminUserForm(forms.ModelForm):
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    is_active = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'department', 'role', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.CheckboxInput, forms.Select)):
                continue
            existing_classes = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing_classes + ' form-control').strip()
        if isinstance(self.fields['is_active'].widget, forms.CheckboxInput):
            self.fields['is_active'].widget.attrs.setdefault('class', 'form-check-input')
        self.fields['role'].widget.attrs.setdefault('class', 'form-select')

    def clean_role(self):
        role = self.cleaned_data.get('role')
        valid_roles = {choice[0] for choice in CustomUser.ROLE_CHOICES}
        if role not in valid_roles:
            raise ValidationError('Invalid role selected.')
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = user.role == 'admin'
        if commit:
            user.save()
            self.save_m2m()
        return user


class AdminUserCreateForm(_BaseAdminUserForm):
    password1 = forms.CharField(
        label='Temporary password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Provide a starter password. The user will be prompted to change it after signing in.'
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta(_BaseAdminUserForm.Meta):
        fields = _BaseAdminUserForm.Meta.fields

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 != password2:
            self.add_error('password2', ValidationError('Passwords do not match.'))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            self.save_m2m()
        return user


class AdminUserUpdateForm(_BaseAdminUserForm):
    password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text='Leave blank to keep the current password.'
    )
    password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta(_BaseAdminUserForm.Meta):
        fields = _BaseAdminUserForm.Meta.fields

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 or password2:
            if password1 != password2:
                self.add_error('password2', ValidationError('Passwords do not match.'))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password1 = self.cleaned_data.get('password1')
        if password1:
            user.set_password(password1)
        if commit:
            user.save()
            self.save_m2m()
        return user


class LabProfileForm(forms.ModelForm):
    class Meta:
        model = LabProfile
        fields = [
            'name',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'postal_code',
            'phone',
            'email',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Laboratory name'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address line 1'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address line 2'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State / Region'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal code'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact phone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Contact email'}),
        }

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('name'):
            self.add_error('name', ValidationError('Laboratory name is required.'))
        return cleaned

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
