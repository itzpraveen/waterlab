from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Customer,
    Sample,
    TestParameter,
    TestResult,
    ConsultantReview,
    KeralaLocation,
    CustomUser,
    AuditTrail,
    TestCategory,
    LabProfile,
    ResultStatusOverride,
    Invoice,
    InvoiceLineItem,
)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'district', 'village_town_city']
    list_filter = ['district', 'taluk']
    search_fields = ['name', 'email', 'phone', 'village_town_city']
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Address Details', {
            'fields': ('house_name_door_no', 'street_locality_landmark', 'village_town_city', 
                      'panchayat_municipality', 'taluk', 'district', 'pincode')
        }),
        ('Auto-Generated', {
            'fields': ('address',),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ['address']

@admin.register(KeralaLocation)
class KeralaLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'location_type', 'parent']
    list_filter = ['location_type']
    search_fields = ['name']

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Role Information', {
            'fields': ('role', 'phone', 'department', 'employee_id', 'signature')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role Information', {
            'fields': ('role', 'phone', 'department', 'employee_id', 'signature')
        }),
    )

@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'model_name', 'object_id', 'ip_address']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__username', 'object_id', 'model_name']
    readonly_fields = ['audit_id', 'user', 'action', 'model_name', 'object_id', 'changes', 'old_values', 'new_values', 'timestamp', 'ip_address']
    ordering = ['-timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(LabProfile)
class LabProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'address_line1',
                'address_line2',
                ('city', 'state', 'postal_code'),
                'phone',
                'email',
                'logo',
            )
        }),
        ('Authorised Signatories', {
            'fields': (
                'signatory_food_analyst',
                'signatory_bio_manager',
                'signatory_chem_manager',
                'signatory_solutions_manager',
            )
        }),
        ('Metadata', {
            'fields': ('updated_at',),
        })
    )
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        if LabProfile.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ResultStatusOverride)
class ResultStatusOverrideAdmin(admin.ModelAdmin):
    list_display = ('text_value', 'status', 'parameter', 'is_active', 'updated_at')
    list_filter = ('status', 'is_active', 'parameter')
    search_fields = ('text_value', 'parameter__name')
    readonly_fields = ('normalized_value', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': (
                'parameter',
                'text_value',
                'status',
                'is_active',
            )
        }),
        ('Metadata', {
            'fields': ('normalized_value', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

admin.site.register(Sample)
admin.site.register(TestParameter)
admin.site.register(TestResult)
admin.site.register(ConsultantReview)
admin.site.register(TestCategory)


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    readonly_fields = ('amount',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'sample', 'status', 'issued_on', 'total')
    list_filter = ('status', 'issued_on')
    search_fields = ('invoice_number', 'sample__display_id', 'sample__customer__name')
    readonly_fields = ('subtotal', 'tax_amount', 'total', 'created_at', 'updated_at')
    inlines = [InvoiceLineItemInline]
