from django.db import models
import uuid
import json
from django.conf import settings # Recommended way to import User model
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('lab', 'Lab Technician'),
        ('frontdesk', 'Front Desk'),
        ('consultant', 'Consultant'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='frontdesk')
    phone = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_lab_tech(self):
        return self.role == 'lab'
    
    def is_frontdesk(self):
        return self.role == 'frontdesk'
    
    def is_consultant(self):
        return self.role == 'consultant'

class KeralaLocation(models.Model):
    """Model to store Kerala administrative divisions"""
    LOCATION_TYPES = [
        ('district', 'District'),
        ('taluk', 'Taluk'),
        ('village', 'Village'),
        ('panchayat', 'Panchayat'),
        ('municipality', 'Municipality'),
        ('corporation', 'Corporation'),
    ]
    
    name = models.CharField(max_length=100)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    district_code = models.CharField(max_length=10, blank=True, null=True)
    
    class Meta:
        unique_together = ('name', 'location_type', 'parent')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"

class Customer(models.Model):
    KERALA_DISTRICTS = [
        ('thiruvananthapuram', 'Thiruvananthapuram'),
        ('kollam', 'Kollam'),
        ('pathanamthitta', 'Pathanamthitta'),
        ('alappuzha', 'Alappuzha'),
        ('kottayam', 'Kottayam'),
        ('idukki', 'Idukki'),
        ('ernakulam', 'Ernakulam'),
        ('thrissur', 'Thrissur'),
        ('palakkad', 'Palakkad'),
        ('malappuram', 'Malappuram'),
        ('kozhikode', 'Kozhikode'),
        ('wayanad', 'Wayanad'),
        ('kannur', 'Kannur'),
        ('kasaragod', 'Kasaragod'),
    ]
    
    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    
    # Detailed Kerala address fields following standard format
    house_name_door_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="House Name / Door Number")
    street_locality_landmark = models.CharField(max_length=200, blank=True, default='', verbose_name="Street / Locality / Landmark")
    village_town_city = models.CharField(max_length=100, blank=True, default='', verbose_name="Village / Town / City")
    panchayat_municipality = models.CharField(max_length=100, blank=True, default='', verbose_name="Panchayat / Municipality / Corporation")
    taluk = models.CharField(max_length=100, blank=True, default='', verbose_name="Taluk")
    district = models.CharField(max_length=50, choices=KERALA_DISTRICTS, blank=True, default='thiruvananthapuram', verbose_name="District")
    pincode = models.CharField(max_length=6, blank=True, default='', verbose_name="PIN Code")
    
    # Keep old address field for backward compatibility
    address = models.TextField(blank=True, null=True, help_text="Complete address (auto-populated)")

    def save(self, *args, **kwargs):
        # Auto-populate the address field from detailed components
        address_parts = []
        if self.house_name_door_no:
            address_parts.append(self.house_name_door_no)
        address_parts.extend([
            self.street_locality_landmark,
            self.village_town_city,
            self.panchayat_municipality,
            f"{self.taluk} Taluk",
            f"{self.get_district_display()} District",
            f"Kerala - {self.pincode}"
        ])
        self.address = ", ".join([part for part in address_parts if part])
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Sample(models.Model):
    SAMPLE_SOURCE_CHOICES = [
        ('WELL', 'Well'),
        ('BOREWELL', 'Borewell'),
        ('TAP', 'Tap'),
        ('RIVER', 'River'),
        ('POND', 'Pond'),
        ('OTHER', 'Other'),
    ]
    SAMPLE_STATUS_CHOICES = [
        ('RECEIVED_FRONT_DESK', 'Received at Front Desk'),
        ('SENT_TO_LAB', 'Sent to Lab'),
        ('TESTING_IN_PROGRESS', 'Testing in Progress'),
        ('RESULTS_ENTERED', 'Results Entered'),
        ('REVIEW_PENDING', 'Review Pending'),
        ('REPORT_APPROVED', 'Report Approved'),
        ('REPORT_SENT', 'Report Sent'),
        ('CANCELLED', 'Cancelled'),
    ]

    sample_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='samples')
    collection_datetime = models.DateTimeField()
    sample_source = models.CharField(max_length=50, choices=SAMPLE_SOURCE_CHOICES)
    collected_by = models.CharField(max_length=255) # Could be customer or lab personnel
    # tests_requested will likely be a ManyToManyField to a TestParameter model
    tests_requested = models.ManyToManyField('TestParameter', blank=True, related_name='samples')
    date_received_at_lab = models.DateTimeField(null=True, blank=True)
    current_status = models.CharField(max_length=50, choices=SAMPLE_STATUS_CHOICES, default='RECEIVED_FRONT_DESK')

    def __str__(self):
        return f"{self.sample_id} - {self.customer.name}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        
        # Validate collection datetime is not in the future
        if self.collection_datetime and self.collection_datetime > timezone.now():
            raise ValidationError("Collection date cannot be in the future.")
        
        # Validate date received at lab is after collection
        if self.date_received_at_lab and self.collection_datetime:
            if self.date_received_at_lab < self.collection_datetime:
                raise ValidationError("Date received at lab cannot be before collection date.")
    
    def can_transition_to(self, new_status):
        """Check if sample can transition to new status based on business rules"""
        valid_transitions = {
            'RECEIVED_FRONT_DESK': ['SENT_TO_LAB', 'CANCELLED'],
            'SENT_TO_LAB': ['TESTING_IN_PROGRESS', 'CANCELLED'],
            'TESTING_IN_PROGRESS': ['RESULTS_ENTERED', 'CANCELLED'],
            'RESULTS_ENTERED': ['REVIEW_PENDING'],
            'REVIEW_PENDING': ['REPORT_APPROVED', 'TESTING_IN_PROGRESS'],  # Can send back for retesting
            'REPORT_APPROVED': ['REPORT_SENT'],
            'REPORT_SENT': [],  # Final status
            'CANCELLED': [],  # Final status
        }
        return new_status in valid_transitions.get(self.current_status, [])
    
    def update_status(self, new_status, user=None):
        """Safely update sample status with validation"""
        from django.core.exceptions import ValidationError
        
        if not self.can_transition_to(new_status):
            raise ValidationError(f"Cannot transition from {self.current_status} to {new_status}")
        
        # Additional business rule validations
        if new_status == 'RESULTS_ENTERED':
            if not self.has_all_test_results():
                raise ValidationError("Cannot mark as results entered - missing test results for some parameters")
        
        if new_status == 'REVIEW_PENDING':
            if not self.has_all_test_results():
                raise ValidationError("Cannot send for review - missing test results")
        
        # Update status and related fields
        old_status = self.current_status
        self.current_status = new_status
        
        # Auto-update related timestamps
        if new_status == 'SENT_TO_LAB' and not self.date_received_at_lab:
            from django.utils import timezone
            self.date_received_at_lab = timezone.now()
        
        self.save()
        
        # Log the status change
        if user:
            from .models import AuditTrail
            AuditTrail.log_change(
                user=user,
                action='UPDATE',
                instance=self,
                old_values={'current_status': old_status},
                new_values={'current_status': new_status}
            )
    
    def has_all_test_results(self):
        """Check if all requested tests have results"""
        requested_count = self.tests_requested.count()
        results_count = self.results.count()
        return requested_count > 0 and requested_count == results_count
    
    def get_missing_test_results(self):
        """Get list of test parameters that don't have results yet"""
        completed_params = self.results.values_list('parameter_id', flat=True)
        return self.tests_requested.exclude(parameter_id__in=completed_params)
    
    def can_be_reviewed(self):
        """Check if sample is ready for consultant review"""
        return (self.current_status == 'RESULTS_ENTERED' and 
                self.has_all_test_results())
    
    @property
    def is_completed(self):
        """Check if sample processing is completed"""
        return self.current_status in ['REPORT_APPROVED', 'REPORT_SENT']

class TestParameter(models.Model):
    parameter_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=50)
    standard_method = models.CharField(max_length=255, blank=True, null=True)
    min_permissible_limit = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    max_permissible_limit = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    # descriptive_limit = models.CharField(max_length=255, blank=True, null=True, help_text="For text-based limits like 'Absent'")


    def __str__(self):
        return f"{self.name} ({self.unit})"

class TestResult(models.Model):
    result_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='results')
    parameter = models.ForeignKey(TestParameter, on_delete=models.PROTECT, related_name='results') # PROTECT to avoid deleting parameter if results exist
    result_value = models.CharField(max_length=255, help_text="Actual result value. Can be numeric or text (e.g., 'Present', 'Absent')")
    # For numeric results, consider a separate DecimalField and logic to use one or the other.
    # result_value_numeric = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    observation = models.TextField(blank=True, null=True)
    test_date = models.DateTimeField(auto_now_add=True) # Or DateField if time is not critical
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='test_results_entered')

    class Meta:
        unique_together = ('sample', 'parameter') # Ensure one result per parameter per sample

    def __str__(self):
        return f"Result for {self.sample.sample_id} - {self.parameter.name}: {self.result_value}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        import re
        
        # Validate that technician has appropriate role
        if self.technician and not self.technician.is_lab_tech() and not self.technician.is_admin():
            raise ValidationError("Only lab technicians and admins can enter test results.")
        
        # Validate result value format and limits
        if self.parameter:
            # Check if result should be numeric
            if self.parameter.min_permissible_limit is not None or self.parameter.max_permissible_limit is not None:
                try:
                    numeric_value = float(self.result_value)
                    
                    # Check against limits
                    if self.parameter.min_permissible_limit is not None and numeric_value < self.parameter.min_permissible_limit:
                        # Don't raise error, but could add warning flag
                        pass
                    if self.parameter.max_permissible_limit is not None and numeric_value > self.parameter.max_permissible_limit:
                        # Don't raise error, but could add warning flag  
                        pass
                        
                except ValueError:
                    # If limits are set but value is not numeric, it might be valid (e.g., "Absent")
                    pass
    
    def is_within_limits(self):
        """Check if result is within permissible limits"""
        if not self.parameter:
            return None
            
        try:
            numeric_value = float(self.result_value)
            
            within_min = (self.parameter.min_permissible_limit is None or 
                         numeric_value >= self.parameter.min_permissible_limit)
            within_max = (self.parameter.max_permissible_limit is None or 
                         numeric_value <= self.parameter.max_permissible_limit)
            
            return within_min and within_max
        except ValueError:
            # Non-numeric result, assume valid
            return True
    
    def get_limit_status(self):
        """Get status of result relative to limits"""
        if not self.parameter:
            return "UNKNOWN"
            
        try:
            numeric_value = float(self.result_value)
            
            if self.parameter.min_permissible_limit is not None and numeric_value < self.parameter.min_permissible_limit:
                return "BELOW_LIMIT"
            elif self.parameter.max_permissible_limit is not None and numeric_value > self.parameter.max_permissible_limit:
                return "ABOVE_LIMIT"
            else:
                return "WITHIN_LIMITS"
        except ValueError:
            return "NON_NUMERIC"

class ConsultantReview(models.Model):
    REVIEW_STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sample = models.OneToOneField(Sample, on_delete=models.CASCADE, related_name='review') # Each sample has one review
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='reviews_conducted')
    comments = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=REVIEW_STATUS_CHOICES, default='PENDING')
    review_date = models.DateTimeField(auto_now_add=True) # Or auto_now=True if it should update on every save

    def __str__(self):
        return f"Review for {self.sample.sample_id} by {self.reviewer.username if self.reviewer else 'N/A'}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate that reviewer has consultant role
        if self.reviewer and not self.reviewer.is_consultant() and not self.reviewer.is_admin():
            raise ValidationError("Only consultants and admins can review samples.")
        
        # Validate that sample is ready for review
        if self.sample and not self.sample.can_be_reviewed():
            raise ValidationError("Sample is not ready for review - missing test results or incorrect status.")
    
    def save(self, *args, **kwargs):
        # Update sample status based on review status
        is_new = self.pk is None
        old_status = None
        
        if not is_new:
            try:
                old_review = ConsultantReview.objects.get(pk=self.pk)
                old_status = old_review.status
            except ConsultantReview.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Only update sample status if review status actually changed
        if not is_new and old_status != self.status:
            if self.status == 'APPROVED':
                try:
                    self.sample.update_status('REPORT_APPROVED', self.reviewer)
                except Exception as e:
                    # Log the error but don't fail the save
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to update sample status to REPORT_APPROVED: {e}")
            elif self.status == 'REJECTED':
                try:
                    self.sample.update_status('TESTING_IN_PROGRESS', self.reviewer)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to update sample status to TESTING_IN_PROGRESS: {e}")

class AuditTrail(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
        ('VIEW', 'Viewed'),
    ]
    
    audit_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)  # Store UUID as string for flexibility
    object_repr = models.CharField(max_length=200)  # String representation of the object
    
    # Store the changes as JSON
    changes = models.JSONField(default=dict, blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} {self.model_name} by {self.user.username if self.user else 'System'} at {self.timestamp}"
    
    @classmethod
    def log_change(cls, user, action, instance, old_values=None, new_values=None, request=None):
        """
        Helper method to log changes
        """
        changes = {}
        if old_values and new_values:
            for field, new_value in new_values.items():
                old_value = old_values.get(field)
                if old_value != new_value:
                    changes[field] = {
                        'old': old_value,
                        'new': new_value
                    }
        
        audit_log = cls.objects.create(
            user=user,
            action=action,
            model_name=instance.__class__.__name__,
            object_id=str(instance.pk),
            object_repr=str(instance),
            changes=changes,
            old_values=old_values or {},
            new_values=new_values or {},
            ip_address=cls._get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )
        return audit_log
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

# Create your models here.
