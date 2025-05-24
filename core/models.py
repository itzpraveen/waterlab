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
