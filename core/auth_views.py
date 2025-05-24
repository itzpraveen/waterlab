from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from .models import CustomUser


class AdminLoginView(LoginView):
    """Dedicated admin login view with enhanced security"""
    template_name = 'auth/admin_login.html'
    redirect_authenticated_user = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Admin Login'
        context['login_type'] = 'admin'
        return context
    
    def form_valid(self, form):
        user = form.get_user()
        
        # Only allow admin users
        if not user.is_admin():
            messages.error(self.request, 'Admin access required.')
            return self.form_invalid(form)
        
        login(self.request, user)
        messages.success(self.request, f'Welcome back, {user.get_full_name() or user.username}!')
        return redirect('core:admin_dashboard')
    
    def get_success_url(self):
        return reverse_lazy('core:admin_dashboard')


class UserLoginView(LoginView):
    """Standard user login for staff members"""
    template_name = 'auth/user_login.html'
    redirect_authenticated_user = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Staff Login'
        context['login_type'] = 'user'
        return context
    
    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        
        # Role-based welcome message
        role_name = {
            'admin': 'Administrator',
            'lab': 'Lab Technician', 
            'frontdesk': 'Front Desk Staff',
            'consultant': 'Consultant'
        }.get(user.role, 'User')
        
        messages.success(self.request, f'Welcome {user.get_full_name() or user.username}! ({role_name})')
        return redirect(self.get_success_url())
    
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
    
    def get_next_page(self):
        # Redirect to appropriate login page based on user type
        if self.request.user.is_authenticated and self.request.user.is_admin():
            return reverse_lazy('core:admin_login')
        return reverse_lazy('core:user_login')


class DashboardView(LoginRequiredMixin, TemplateView):
    """Unified dashboard with role-based content"""
    template_name = 'core/dashboard.html'
    
    def get_template_names(self):
        """Return role-specific template"""
        user = self.request.user
        
        if user.is_admin():
            return ['core/dashboards/admin_dashboard.html']
        elif user.is_lab_tech():
            return ['core/dashboards/lab_dashboard.html']
        elif user.is_frontdesk():
            return ['core/dashboards/frontdesk_dashboard.html']
        elif user.is_consultant():
            return ['core/dashboards/consultant_dashboard.html']
        else:
            return ['core/dashboard.html']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Basic context for all users
        context.update({
            'user': user,
            'user_role': user.role,
            'page_title': f'{user.get_role_display()} Dashboard'
        })
        
        return context


def login_selector(request):
    """Landing page to choose login type"""
    return render(request, 'auth/login_selector.html', {
        'page_title': 'Water Lab LIMS - Login'
    })