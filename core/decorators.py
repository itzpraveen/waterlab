from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages

def role_required(roles):
    """
    Decorator that restricts access to users with specific roles
    Usage: @role_required(['admin', 'lab'])
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_superuser and request.user.role not in roles:
                messages.error(request, f'Access denied. Required roles: {", ".join(roles)} or Superuser status.')
                return redirect('core:dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def admin_required(view_func):
    """Decorator that restricts access to admin users only"""
    return role_required(['admin'])(view_func)

def lab_required(view_func):
    """Decorator that restricts access to lab technicians and admins"""
    return role_required(['admin', 'lab'])(view_func)

def frontdesk_required(view_func):
    """Decorator that restricts access to front desk staff and admins"""
    return role_required(['admin', 'frontdesk'])(view_func)

def consultant_required(view_func):
    """Decorator that restricts access to consultants and admins"""
    return role_required(['admin', 'consultant'])(view_func)
