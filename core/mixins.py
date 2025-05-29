from django.contrib.auth.mixins import LoginRequiredMixin
# from django.core.exceptions import PermissionDenied # Not used
from django.shortcuts import redirect
from django.contrib import messages
# from django.forms.models import model_to_dict # Not used

class RoleRequiredMixin(LoginRequiredMixin):
    """
    Mixin that restricts access to users with specific roles
    Usage in class-based views:
    class MyView(RoleRequiredMixin, View):
        allowed_roles = ['admin', 'lab']
    """
    allowed_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Allow superuser to bypass role check
        if not request.user.is_superuser:
            if self.allowed_roles and request.user.role not in self.allowed_roles:
                messages.error(request, f'Access denied. Required roles: {", ".join(self.allowed_roles)} or Superuser status.')
                return redirect('core:dashboard')
        
        return super().dispatch(request, *args, **kwargs)

class AdminRequiredMixin(RoleRequiredMixin):
    """Mixin that restricts access to admin users only"""
    allowed_roles = ['admin']

class LabRequiredMixin(RoleRequiredMixin):
    """Mixin that restricts access to lab technicians and admins"""
    allowed_roles = ['admin', 'lab']

class FrontDeskRequiredMixin(RoleRequiredMixin):
    """Mixin that restricts access to front desk staff and admins"""
    allowed_roles = ['admin', 'frontdesk']

class ConsultantRequiredMixin(RoleRequiredMixin):
    """Mixin that restricts access to consultants and admins"""
    allowed_roles = ['admin', 'consultant']

class AuditMixin:
    """Mixin to automatically log changes to models"""
    
    def form_valid(self, form):
        from .models import AuditTrail
        
        # Get old values if this is an update
        old_values = {}
        if hasattr(self, 'object') and self.object and self.object.pk:
            # This is an update
            old_instance = self.model.objects.get(pk=self.object.pk)
            old_values = self._get_field_values(old_instance)
            action = 'UPDATE'
        else:
            # This is a create
            action = 'CREATE'
        
        # Save the form
        response = super().form_valid(form)
        
        # Get new values
        new_values = self._get_field_values(self.object)
        
        # Log the change
        AuditTrail.log_change(
            user=self.request.user,
            action=action,
            instance=self.object,
            old_values=old_values,
            new_values=new_values,
            request=self.request
        )
        
        return response
    
    def _get_field_values(self, instance):
        """Get field values from model instance for audit logging"""
        values = {}
        for field in instance._meta.fields:
            if not field.name.endswith('_id') and field.name not in ['password']:  # Skip relation IDs and passwords
                value = getattr(instance, field.name)
                if hasattr(value, 'isoformat'):  # Handle datetime objects
                    value = value.isoformat()
                elif hasattr(value, '__str__'):
                    value = str(value)
                values[field.name] = value
        return values
