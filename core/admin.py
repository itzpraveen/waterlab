from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Customer, Sample, TestParameter, TestResult, ConsultantReview, KeralaLocation, CustomUser, AuditTrail, TestCategory

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
            'fields': ('role', 'phone', 'department', 'employee_id')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role Information', {
            'fields': ('role', 'phone', 'department', 'employee_id')
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

admin.site.register(Sample)
admin.site.register(TestParameter)
admin.site.register(TestResult)
admin.site.register(ConsultantReview)
admin.site.register(TestCategory)
