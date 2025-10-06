from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
# from .models import CustomUser # CustomUser not directly used here
# from django.http import Http404 # Http404 not explicitly used here

class UserLoginView(LoginView):
    """Unified login for all WaterLab roles"""
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Sign In'
        context['login_type'] = 'user'
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user

        role_name = {
            'admin': 'Administrator',
            'lab': 'Lab Technician',
            'frontdesk': 'Front Desk Staff',
            'consultant': 'Consultant'
        }.get(user.role, 'User')

        messages.success(self.request, f'Welcome {user.get_full_name() or user.username}! ({role_name})')
        return response
    
    def get_success_url(self):
        user = self.request.user
        
        # Role-based dashboard routing
        if user.is_admin():
            return reverse_lazy('core:admin_dashboard')
        elif user.is_lab_tech():
            return reverse_lazy('core:lab_dashboard')
        elif user.is_frontdesk():
            return reverse_lazy('core:frontdesk_dashboard')
        elif user.is_consultant():
            return reverse_lazy('core:consultant_dashboard')
        else:
            return reverse_lazy('core:dashboard')


class SecureLogoutView(LogoutView):
    """Enhanced logout with security logging"""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, f'Goodbye {request.user.username}! You have been logged out securely.')
        return super().dispatch(request, *args, **kwargs)
    
    # By removing get_next_page, it will use the LOGOUT_REDIRECT_URL from settings.
    # The next_page attribute is also not set, so settings.LOGOUT_REDIRECT_URL will be the fallback.


class DashboardView(LoginRequiredMixin, TemplateView):
    """Unified dashboard that redirects to role-specific dashboards."""

    # Default template for users without a specific role dashboard (if any)
    # Or this view could simply raise Http404 if no specific redirect is found.
    template_name = 'core/dashboard.html' 

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            # This should ideally be handled by LoginRequiredMixin redirecting to LOGIN_URL
            return redirect(reverse_lazy(settings.LOGIN_URL))

        user = request.user
        if user.is_admin():
            return redirect(reverse_lazy('core:admin_dashboard'))
        elif user.is_lab_tech():
            return redirect(reverse_lazy('core:lab_dashboard'))
        elif user.is_frontdesk():
            return redirect(reverse_lazy('core:frontdesk_dashboard'))
        elif user.is_consultant():
            return redirect(reverse_lazy('core:consultant_dashboard'))
        else:
            # Fallback for users with no specific role dashboard or an unknown role.
            # Render a generic dashboard page or raise an error/show a message.
            # If 'core/dashboard.html' is intended for such users, 
            # ensure its context is appropriately set in get_context_data.
            return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        # This context is for the fallback 'core/dashboard.html'
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update({
            'user': user,
            'user_role': getattr(user, 'role', 'N/A'), # getattr for safety
            'page_title': 'Dashboard' # Generic title
        })
        # Add any other generic context needed for 'core/dashboard.html'
        # For example, if it's supposed to show some basic info or links.
        # If it's not supposed to be reached by users with defined roles,
        # the dispatch method could raise Http404 in the else block.
        return context
