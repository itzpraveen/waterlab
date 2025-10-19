import logging
from collections import OrderedDict
from html import escape

from django.shortcuts import render, get_object_or_404, redirect, resolve_url
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.views.decorators.http import require_POST
from django.db.models.deletion import ProtectedError
from django.forms.models import model_to_dict

from django.conf import settings

from .models import Customer, Sample, TestParameter, TestResult, ConsultantReview, CustomUser, AuditTrail, TestCategory
from .forms import (
    CustomerForm,
    SampleForm,
    CustomPasswordChangeForm,
    TestResultEntryForm,
    TestParameterForm,
    AdminUserCreateForm,
    AdminUserUpdateForm,
)
from .decorators import admin_required, lab_required, frontdesk_required, consultant_required
from .mixins import AdminRequiredMixin, LabRequiredMixin, FrontDeskRequiredMixin, ConsultantRequiredMixin, RoleRequiredMixin, AuditMixin

# Health check endpoint for deployment monitoring
from django.http import HttpResponse, FileResponse, HttpResponseNotFound, JsonResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from io import BytesIO


logger = logging.getLogger(__name__)


def _format_error_message(base_message, exc):
    """Return debug-friendly error text without leaking details in production."""
    if settings.DEBUG:
        return f"{base_message} Details: {exc}"
    return base_message

def health_check(request):
    """Health check endpoint for load balancers and monitoring systems"""
    return HttpResponse("healthy", content_type="text/plain")

def debug_admin(request):
    """Debug endpoint to check admin user - REMOVE IN PRODUCTION"""
    if not settings.DEBUG:
        return HttpResponseNotFound()

    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        admin_users = User.objects.filter(is_superuser=True)
        user_info = []
        for user in admin_users:
            user_info.append(f"Username: {user.username}, Email: {user.email}, Role: {user.role}")
        
        if admin_users.exists():
            return HttpResponse(f"Admin users found: {'; '.join(user_info)}", content_type="text/plain")
        else:
            return HttpResponse("No admin users found", content_type="text/plain")
    except Exception as exc:
        logger.exception("Failed to gather admin user debug info")
        return HttpResponse(
            _format_error_message("Error retrieving admin users.", exc),
            content_type="text/plain",
            status=500,
        )

def create_admin_web(request):
    """Web endpoint to create admin user - REMOVE IN PRODUCTION"""
    if not settings.DEBUG:
        return HttpResponseNotFound()

    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        if User.objects.filter(username='admin').exists():
            return HttpResponse("Admin user already exists", content_type="text/plain")
        
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@waterlab.com',
            password='WaterLab2024!',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        return HttpResponse("Admin user created successfully! Username: admin, Password: WaterLab2024!", content_type="text/plain")
    except Exception as exc:
        logger.exception("Failed to create admin user via debug endpoint")
        return HttpResponse(
            _format_error_message("Error creating admin user.", exc),
            content_type="text/plain",
            status=500,
        )

def debug_view(request):
    """Debug endpoint to check configuration and functionality"""
    if not settings.DEBUG:
        return HttpResponseNotFound()
    import os
    
    debug_info = []
    debug_info.append("=== Django Configuration Debug ===")
    debug_info.append(f"DEBUG: {settings.DEBUG}")
    debug_info.append(f"STATIC_URL: {settings.STATIC_URL}")
    debug_info.append(f"STATIC_ROOT: {settings.STATIC_ROOT}")
    debug_info.append(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    
    # Check static files
    debug_info.append("\n=== Static Files Check ===")
    static_css_path = os.path.join(settings.STATIC_ROOT, 'css', 'style.css')
    debug_info.append(f"CSS file exists: {os.path.exists(static_css_path)}")
    
    # Check database
    debug_info.append("\n=== Database Check ===")
    try:
        from core.models import Customer, Sample, CustomUser
        debug_info.append(f"Customers: {Customer.objects.count()}")
        debug_info.append(f"Samples: {Sample.objects.count()}")
        debug_info.append(f"Users: {CustomUser.objects.count()}")
        debug_info.append(f"Admin users: {CustomUser.objects.filter(role='admin').count()}")
    except Exception as exc:
        logger.exception("Database check failed in debug_view")
        debug_info.append(
            _format_error_message("Database error encountered while generating debug info.", exc)
        )
    
    # Check user session
    debug_info.append("\n=== User Session ===")
    debug_info.append(f"User authenticated: {request.user.is_authenticated}")
    if request.user.is_authenticated:
        debug_info.append(f"Username: {request.user.username}")
        debug_info.append(f"Role: {request.user.role}")
        debug_info.append(f"Is admin: {request.user.is_admin()}")
    
    # Environment variables
    debug_info.append("\n=== Environment Variables ===")
    debug_info.append(f"DATABASE_URL set: {'DATABASE_URL' in os.environ}")
    debug_info.append(f"SECRET_KEY set: {'SECRET_KEY' in os.environ}")
    
    return HttpResponse("\n".join(debug_info), content_type="text/plain")

def form_test(request):
    """Simple form test to debug form submission issues"""
    if not settings.DEBUG:
        return HttpResponseNotFound()
    if request.method == 'POST':
        name = request.POST.get('name', 'No name provided')
        return HttpResponse(f"Form submitted successfully! Name: {name}", content_type="text/plain")
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Form Test</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body style="padding: 20px;">
        <h1>🧪 Water Lab LIMS - Form Test</h1>
        <form method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}">
            <div class="form-group">
                <label for="name">Test Name:</label>
                <input type="text" name="name" id="name" class="form-control" placeholder="Enter test name" required>
            </div>
            <button type="submit" class="btn btn-primary">Test Submit</button>
        </form>
        <p><a href="/debug/">View Debug Info</a></p>
    </body>
    </html>
    '''
    
    from django.template import Template, Context
    from django.middleware.csrf import get_token
    
    template = Template(html)
    context = Context({'csrf_token': get_token(request)})
    return HttpResponse(template.render(context))

def fix_admin_role_web(request):
    """Web endpoint to fix admin role case sensitivity - REMOVE IN PRODUCTION"""
    if not settings.DEBUG:
        return HttpResponseNotFound()
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        # Find users with uppercase ADMIN role and fix them
        admin_users = User.objects.filter(role='ADMIN')
        fixed_count = 0
        
        for user in admin_users:
            user.role = 'admin'  # Change to lowercase
            user.save()
            fixed_count += 1
        
        # Verify admin users now work
        admin_users_correct = User.objects.filter(role='admin')
        
        result = f"Fixed {fixed_count} users with ADMIN role.\n"
        result += f"Found {admin_users_correct.count()} admin users with correct role.\n\n"
        
        for user in admin_users_correct:
            result += f"- {user.username}: is_admin()={user.is_admin()}, role='{user.role}'\n"
        
        return HttpResponse(result, content_type="text/plain")
        
    except Exception as exc:
        logger.exception("Failed to normalize admin roles via debug endpoint")
        return HttpResponse(
            _format_error_message("Error normalizing admin roles.", exc),
            content_type="text/plain",
            status=500,
        )

def simple_home(request):
    """Simple home page to avoid redirect loops"""
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    return HttpResponse('<h1>Water Lab LIMS</h1><p><a href="/admin/">Admin Login</a></p><p><a href="/accounts/login/">User Login</a></p>', content_type="text/html")

# Create your views here.

# Authentication Views
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return '/dashboard/'

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'registration/password_change.html'
    success_url = reverse_lazy('core:password_change_done')
    
    def form_valid(self, form):
        messages.success(self.request, 'Your password has been successfully updated!')
        return super().form_valid(form)

@login_required
def password_change_done(request):
    """Simple view to show password change success"""
    return render(request, 'registration/password_change_done.html')

# Dashboard Views
def simple_dashboard(request):
    """Simple dashboard that works without redirect loops"""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')
    
    # Simple dashboard content
    context = {
        'user': request.user,
        'user_role': getattr(request.user, 'role', 'USER'),
        'total_customers': Customer.objects.count() if 'Customer' in globals() else 0,
        'total_samples': Sample.objects.count() if 'Sample' in globals() else 0,
    }
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Water Lab LIMS - Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ background: #007cba; color: white; padding: 20px; border-radius: 5px; }}
            .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
            .stat-box {{ background: #f5f5f5; padding: 15px; border-radius: 5px; flex: 1; }}
            .nav {{ margin: 20px 0; }}
            .nav a {{ background: #007cba; color: white; padding: 10px 15px; text-decoration: none; border-radius: 3px; margin-right: 10px; }}
            .nav a:hover {{ background: #005a87; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Water Lab LIMS Dashboard</h1>
            <p>Welcome, {request.user.username}! ({context['user_role']})</p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <h3>Total Customers</h3>
                <p style="font-size: 24px; margin: 0;">{context['total_customers']}</p>
            </div>
            <div class="stat-box">
                <h3>Total Samples</h3>
                <p style="font-size: 24px; margin: 0;">{context['total_samples']}</p>
            </div>
        </div>
        
        <div class="nav">
            <a href="/admin/">Django Admin</a>
            <a href="/customers/">Customers</a>
            <a href="/samples/">Samples</a>
            <a href="/accounts/logout/">Logout</a>
        </div>
        
        <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin-top: 20px;">
            <h3>✅ Dashboard Working!</h3>
            <p>Your Water Lab LIMS is now running successfully. You can access all features through Django Admin or the navigation links above.</p>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html_content)

class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = 'core/dashboards/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Initialize context with default values for resilience
        context.update({
            'total_customers': 0,
            'total_samples': 0,
            'total_users': 0,
            'pending_samples_count': 0, # Renamed from pending_samples to avoid clash if we list them
            'testing_samples_count': 0, # Renamed from testing_samples
            'review_pending_count': 0,  # Renamed from review_pending
            'completed_samples_count': 0, # Renamed from completed_samples
            'recent_customers': [],
            'recent_samples': [],
            'recent_users': [],
            'user_stats': [],
            'today_samples_count': 0, # Renamed from today_samples
            'week_samples_count': 0,  # Renamed from week_samples
            'samples_in_lab': [],
            'samples_awaiting_review': [],
            'data_load_error': False
        })

        try:
            # Admin gets comprehensive system overview
            context['total_customers'] = Customer.objects.count()
            context['total_samples'] = Sample.objects.count()
            context['total_users'] = CustomUser.objects.count()
            context['pending_samples_count'] = Sample.objects.filter(current_status='RECEIVED_FRONT_DESK').count()
            context['testing_samples_count'] = Sample.objects.filter(current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']).count()
            context['review_pending_count'] = Sample.objects.filter(current_status='REVIEW_PENDING').count()
            context['completed_samples_count'] = Sample.objects.filter(current_status='REPORT_APPROVED').count()
            
            # Recent activity
            context['recent_customers'] = Customer.objects.order_by('-customer_id')[:5]
            context['recent_samples'] = Sample.objects.select_related('customer').order_by('-collection_datetime')[:10]
            context['recent_users'] = CustomUser.objects.order_by('-date_joined')[:5]
            
            # User statistics by role
            context['user_stats'] = CustomUser.objects.values('role').annotate(count=Count('pk'))
            
            # Daily statistics
            context['today_samples_count'] = Sample.objects.filter(collection_datetime__date=timezone.now().date()).count()
            context['week_samples_count'] = Sample.objects.filter(collection_datetime__gte=timezone.now() - timedelta(days=7)).count()

            # Lab workflow specific data
            context['samples_in_lab'] = Sample.objects.filter(
                current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']
            ).select_related('customer').order_by('collection_datetime')[:5]
            
            context['samples_awaiting_review'] = Sample.objects.filter(
                current_status='RESULTS_ENTERED' # Samples with results entered, but not yet in 'REVIEW_PENDING'
            ).select_related('customer').order_by('-collection_datetime')[:5]

        except Exception as exc:
            logger.exception("Failed to build admin dashboard context")
            context['data_load_error'] = True
            messages.error(
                self.request,
                _format_error_message(
                    "There was an error loading some dashboard data. Please try again later.",
                    exc,
                ),
            )

        return context

class LabDashboardView(LabRequiredMixin, TemplateView):
    template_name = 'core/dashboards/lab_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Lab technicians see testing-related data
        context.update({
            'pending_tests': Sample.objects.filter(current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']).count(),
            'completed_tests': Sample.objects.filter(current_status='RESULTS_ENTERED').count(),
            'my_tests': TestResult.objects.filter(technician=self.request.user).count(),
            
            # Today's work
            'today_tests': TestResult.objects.filter(
                test_date__date=timezone.now().date(),
                technician=self.request.user
            ).count(),
            
            # Samples needing attention
            'samples_for_testing': Sample.objects.filter(
                current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']
            ).select_related('customer').order_by('collection_datetime')[:10],
            
            # Recently completed samples by this technician
            'recently_completed_samples': Sample.objects.filter(
                results__technician=self.request.user,
                current_status__in=['RESULTS_ENTERED', 'REVIEW_PENDING', 'REPORT_APPROVED']
            ).distinct().select_related('customer').order_by('-collection_datetime')[:10],
            
            # Recent test results
            'recent_results': TestResult.objects.filter(
                technician=self.request.user
            ).select_related('sample', 'parameter').order_by('-test_date')[:10],
            
            # Test parameters
            'total_parameters': TestParameter.objects.count(),
        })
        return context

class FrontDeskDashboardView(FrontDeskRequiredMixin, TemplateView):
    template_name = 'core/dashboards/frontdesk_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Front desk sees customer and sample registration data
        context.update({
            'total_customers': Customer.objects.count(),
            'pending_samples': Sample.objects.filter(current_status='RECEIVED_FRONT_DESK').count(),
            'today_samples': Sample.objects.filter(collection_datetime__date=timezone.now().date()).count(),
            'ready_reports': Sample.objects.filter(current_status='REPORT_APPROVED').count(),
            
            # Recent registrations
            'recent_customers': Customer.objects.order_by('-customer_id')[:8],
            'recent_samples': Sample.objects.select_related('customer').order_by('-collection_datetime')[:10],
            
            # Samples by status for front desk tracking
            'samples_by_status': Sample.objects.values('current_status').annotate(count=Count('sample_id')),
            
            # Weekly statistics
            'week_customers': Customer.objects.filter(customer_id__in=Customer.objects.order_by('-customer_id')[:50].values_list('customer_id', flat=True)).count(),  # Recent customers
            'week_samples': Sample.objects.filter(collection_datetime__gte=timezone.now() - timedelta(days=7)).count(),
        })
        return context

class ConsultantDashboardView(ConsultantRequiredMixin, TemplateView):
    template_name = 'core/dashboards/consultant_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Consultants see review-related data
        context.update({
            'pending_reviews': Sample.objects.filter(current_status='REVIEW_PENDING').count(),
            'my_reviews': ConsultantReview.objects.filter(reviewer=self.request.user).count(),
            'approved_reports': ConsultantReview.objects.filter(
                reviewer=self.request.user,
                status='APPROVED'
            ).count(),
            
            # Today's reviews
            'today_reviews': ConsultantReview.objects.filter(
                review_date__date=timezone.now().date(),
                reviewer=self.request.user
            ).count(),
            
            # Samples needing review
            'samples_for_review': Sample.objects.filter(
                current_status='REVIEW_PENDING'
            ).select_related('customer').order_by('collection_datetime')[:10],
            
            # Recent reviews
            'recent_reviews': ConsultantReview.objects.filter(
                reviewer=self.request.user
            ).select_related('sample').order_by('-review_date')[:10],
            
            # Recently reviewed samples for better visibility
            'recently_reviewed_samples': Sample.objects.filter(
                review__reviewer=self.request.user,  # Corrected: consultantreview -> review
                review__status__in=['APPROVED', 'REJECTED']  # Corrected: consultantreview -> review
            ).select_related('customer').order_by('-review__review_date')[:10], # Corrected: consultantreview -> review
            
            # Review statistics
            'review_stats': ConsultantReview.objects.filter(reviewer=self.request.user).values('status').annotate(count=Count('review_id')),
        })
        return context

class AuditTrailView(AdminRequiredMixin, ListView):
    model = AuditTrail
    template_name = 'core/audit_trail.html'
    context_object_name = 'audit_trails'
    paginate_by = 50

    def get_queryset(self):
        qs = AuditTrail.objects.select_related('user').order_by('-timestamp')
        model = self.request.GET.get('model')
        action = self.request.GET.get('action')
        user_id = self.request.GET.get('user')
        object_id = self.request.GET.get('object_id')

        if model:
            qs = qs.filter(model_name=model)
        if action:
            qs = qs.filter(action=action)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if object_id:
            qs = qs.filter(object_id__icontains=object_id.strip())
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        filters = {
            'model': request.GET.get('model', ''),
            'action': request.GET.get('action', ''),
            'user': request.GET.get('user', ''),
            'object_id': request.GET.get('object_id', ''),
        }

        model_choices = AuditTrail.objects.values_list('model_name', flat=True).order_by('model_name').distinct()
        action_choices = [choice[0] for choice in AuditTrail.ACTION_CHOICES]
        users = CustomUser.objects.filter(audit_logs__isnull=False).distinct().order_by('first_name', 'username')

        querystring_without_page = ''
        if request.GET:
            qs = request.GET.copy()
            qs.pop('page', None)
            filtered = qs.urlencode()
            if filtered:
                querystring_without_page = '&' + filtered

        context.update({
            'model_choices': model_choices,
            'action_choices': action_choices,
            'users': users,
            'filters': filters,
            'querystring_without_page': querystring_without_page,
        })
        return context

class AdminUserListView(AdminRequiredMixin, ListView):
    model = CustomUser
    template_name = 'core/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        queryset = CustomUser.objects.all().order_by('-is_active', 'first_name', 'username')
        search_term = self.request.GET.get('q', '').strip()
        role_filter = self.request.GET.get('role', 'all').strip()
        status_filter = self.request.GET.get('status', 'all').strip()

        if search_term:
            queryset = queryset.filter(
                Q(username__icontains=search_term)
                | Q(first_name__icontains=search_term)
                | Q(last_name__icontains=search_term)
                | Q(email__icontains=search_term)
                | Q(phone__icontains=search_term)
            )

        valid_roles = {choice[0] for choice in CustomUser.ROLE_CHOICES}
        if role_filter in valid_roles:
            queryset = queryset.filter(role=role_filter)

        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_term = self.request.GET.get('q', '').strip()
        role_filter = self.request.GET.get('role', 'all').strip()
        status_filter = self.request.GET.get('status', 'all').strip()

        context.update({
            'page_title': 'User management',
            'search_term': search_term,
            'role_filter': role_filter,
            'status_filter': status_filter,
            'role_choices': CustomUser.ROLE_CHOICES,
            'active_count': CustomUser.objects.filter(is_active=True).count(),
            'inactive_count': CustomUser.objects.filter(is_active=False).count(),
            'role_counts': CustomUser.objects.values('role').annotate(count=Count('pk')).order_by('role'),
            'query_string': self._build_query_string(exclude_keys=['page'])
        })
        return context

    def _build_query_string(self, exclude_keys=None):
        exclude_keys = set(exclude_keys or [])
        params = self.request.GET.copy()
        for key in list(params.keys()):
            if key in exclude_keys:
                params.pop(key)
        encoded = params.urlencode()
        return f'&{encoded}' if encoded else ''


class AdminUserCreateView(AuditMixin, AdminRequiredMixin, CreateView):
    model = CustomUser
    form_class = AdminUserCreateForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"User '{self.object.username}' created successfully.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Add team member'
        context['is_create'] = True
        return context


class AdminUserUpdateView(AuditMixin, AdminRequiredMixin, UpdateView):
    model = CustomUser
    form_class = AdminUserUpdateForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_list')

    def form_valid(self, form):
        original = CustomUser.objects.get(pk=self.object.pk)
        new_role = form.cleaned_data.get('role')
        new_active = form.cleaned_data.get('is_active')

        if original.role == 'admin' and (new_role != 'admin' or not new_active):
            remaining_admins = CustomUser.objects.filter(role='admin', is_active=True).exclude(pk=original.pk)
            if not remaining_admins.exists():
                if new_role != 'admin':
                    form.add_error('role', 'At least one active administrator must remain.')
                else:
                    form.add_error('is_active', 'At least one active administrator must remain active.')
                return self.form_invalid(form)

        response = super().form_valid(form)
        if form.cleaned_data.get('password1'):
            messages.success(self.request, f"User '{self.object.username}' updated and password reset.")
        else:
            messages.success(self.request, f"User '{self.object.username}' updated successfully.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Edit: {self.object.get_full_name() or self.object.username}"
        context['is_create'] = False
        return context


@login_required
@admin_required
@require_POST
def toggle_user_active(request, pk):
    user_to_toggle = get_object_or_404(CustomUser, pk=pk)

    redirect_target = request.POST.get('next') or resolve_url('core:user_list')

    if user_to_toggle == request.user:
        messages.error(request, 'You cannot change your own activation status.')
        return redirect(redirect_target)

    if user_to_toggle.role == 'admin' and user_to_toggle.is_active:
        remaining_admins = CustomUser.objects.filter(role='admin', is_active=True).exclude(pk=user_to_toggle.pk)
        if not remaining_admins.exists():
            messages.error(request, 'At least one active administrator must remain. Promote another admin before deactivating this account.')
            return redirect(redirect_target)

    try:
        with transaction.atomic():
            old_values = {'is_active': user_to_toggle.is_active}
            user_to_toggle.is_active = not user_to_toggle.is_active
            user_to_toggle.save(update_fields=['is_active'])
            new_values = {'is_active': user_to_toggle.is_active}
            AuditTrail.log_change(
                user=request.user,
                action='UPDATE',
                instance=user_to_toggle,
                old_values=old_values,
                new_values=new_values,
                request=request,
            )
        status_text = 'activated' if user_to_toggle.is_active else 'deactivated'
        messages.success(request, f"User '{user_to_toggle.username}' has been {status_text}.")
    except Exception as exc:
        logger.exception('Failed to toggle activation for user %s', pk)
        messages.error(request, _format_error_message('Unable to change user status.', exc))

    return redirect(redirect_target)


from django.db.models import Max

class TestResultListView(LoginRequiredMixin, ListView):
    model = Sample
    template_name = 'core/test_result_list.html'
    context_object_name = 'samples_with_results'
    paginate_by = 20

    def get_queryset(self):
        queryset = Sample.objects.annotate(
            latest_test_date=Max('results__test_date')
        ).filter(
            results__isnull=False
        ).select_related(
            'customer'
        ).prefetch_related(
            'results',
            'tests_requested'
        ).distinct().order_by('-latest_test_date', '-collection_datetime')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Samples with Test Results'
        return context

class TestResultDetailView(LoginRequiredMixin, DetailView):
    model = Sample
    template_name = 'core/test_result_detail.html'
    context_object_name = 'sample'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['results'] = TestResult.objects.filter(sample=self.object).select_related('parameter').order_by('parameter__category', 'parameter__name')
        return context

class CustomerListView(ListView):
    model = Customer
    template_name = 'core/customer_list.html'
    context_object_name = 'customers'
    # LoginRequiredMixin should be added to views that require a logged-in user.
    # For CustomerListView, assuming it's a public or semi-public list, 
    # it might not need login. If it does, LoginRequiredMixin should be added.
    # For now, leaving as is, as the primary issue is with SampleListView.
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Dashboard statistics
        context['stats'] = {
            'total_customers': Customer.objects.count(),
            'total_samples': Sample.objects.count(),
            'pending_samples': Sample.objects.filter(current_status='RECEIVED_FRONT_DESK').count(),
            'completed_samples': Sample.objects.filter(current_status='REPORT_APPROVED').count(),
        }
        
        # Recent samples
        context['recent_samples'] = Sample.objects.select_related('customer').order_by('-collection_datetime')[:5]
        
        return context

class CustomerDetailView(DetailView): # New DetailView for Customer
    model = Customer
    template_name = 'core/customer_detail.html'
    context_object_name = 'customer'

class CustomerCreateView(AuditMixin, FrontDeskRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'core/customer_form.html' 
    success_url = reverse_lazy('core:customer_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Customer "{form.instance.name}" has been created successfully!')
        return super().form_valid(form)

class CustomerUpdateView(AuditMixin, FrontDeskRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'core/customer_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:customer_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Customer "{form.instance.name}" has been updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context

class SampleListView(LoginRequiredMixin, ListView):  # Added LoginRequiredMixin
    model = Sample
    template_name = 'core/sample_list.html'
    context_object_name = 'samples'
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Sample.objects
            .select_related('customer')
            .prefetch_related('tests_requested')
            .order_by('-collection_datetime')
        )
        status_param = self.request.GET.get('status')
        if status_param:
            status_key = status_param.upper()
            status_map = {
                'PENDING': ['RECEIVED_FRONT_DESK'],
                'IN_LAB': ['SENT_TO_LAB', 'TESTING_IN_PROGRESS'],
                'AWAITING_REVIEW': ['REVIEW_PENDING'],
                'COMPLETED': ['REPORT_APPROVED', 'REPORT_SENT'],
            }
            if status_key in status_map:
                qs = qs.filter(current_status__in=status_map[status_key])
            else:
                qs = qs.filter(current_status=status_key)

        collected_scope = self.request.GET.get('collected')
        if collected_scope == 'today':
            qs = qs.filter(collection_datetime__date=timezone.now().date())
        elif collected_scope == 'week':
            qs = qs.filter(collection_datetime__gte=timezone.now() - timedelta(days=7))
        return qs

class SampleDetailView(DetailView): # New DetailView for Sample
    model = Sample
    template_name = 'core/sample_detail.html'
    context_object_name = 'sample'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sample = context['sample']
        tests_qs = sample.tests_requested.all().order_by('category_obj__display_order', 'category_obj__name', 'category', 'display_order', 'name')
        results_qs = sample.results.select_related('parameter').order_by('parameter__category_obj__display_order', 'parameter__category_obj__name', 'parameter__category', 'parameter__display_order', 'parameter__name')

        def _category_key(label: str) -> tuple[int, str]:
            lowered = label.casefold()
            if any(token in lowered for token in ('physical', 'chemical')):
                return (0, label)
            if any(token in lowered for token in ('micro', 'bacter')):
                return (1, label)
            if 'solution' in lowered:
                return (2, label)
            return (3, label)

        def _group_by_category(items, get_category):
            buckets = {}
            counter = 1
            for item in items:
                raw_category = (get_category(item) or '').strip()
                label = raw_category or 'Uncategorized'
                buckets.setdefault(label, []).append({
                    'index': counter,
                    'item': item,
                })
                counter += 1
            ordered_labels = sorted(buckets.keys(), key=_category_key)
            return OrderedDict((label, buckets[label]) for label in ordered_labels)

        context['ordered_tests'] = tests_qs
        context['tests_by_category'] = _group_by_category(tests_qs, lambda param: param.category_label)
        context['ordered_results'] = results_qs
        context['results_by_category'] = _group_by_category(results_qs, lambda result: result.parameter.category_label)
        return context

class SampleCreateView(AuditMixin, FrontDeskRequiredMixin, CreateView):
    model = Sample
    form_class = SampleForm
    template_name = 'core/sample_form.html'
    success_url = reverse_lazy('core:sample_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Sample has been registered successfully!')
        return super().form_valid(form)

class SampleUpdateView(AuditMixin, FrontDeskRequiredMixin, UpdateView):
    model = Sample
    form_class = SampleForm
    template_name = 'core/sample_form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:sample_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Get the sample before saving to check status
        sample = self.get_object()
        
        # Check if sample can be edited based on current status
        if sample.current_status not in ['RECEIVED_FRONT_DESK', 'SENT_TO_LAB']:
            messages.error(self.request, 
                f'Cannot edit sample in status "{sample.get_current_status_display()}". '
                f'Only samples that are "Received at Front Desk" or "Sent to Lab" can be modified.')
            return redirect('core:sample_detail', pk=sample.sample_id)
        
        # Check if tests_requested is being modified after lab work has started
        if sample.current_status == 'SENT_TO_LAB':
            original_tests = set(sample.tests_requested.all())
            new_tests = set(form.cleaned_data.get('tests_requested', []))
            
            if original_tests != new_tests:
                messages.error(self.request,
                    'Cannot modify test requests after sample has been sent to lab. '
                    'Contact lab staff if changes are needed.')
                return redirect('core:sample_detail', pk=sample.sample_id)
        
        
        
        messages.success(self.request, f'Sample has been updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        
        # Add status information to help users understand edit limitations
        sample = self.get_object()
        context['sample_status'] = sample.current_status
        context['can_edit_tests'] = sample.current_status == 'RECEIVED_FRONT_DESK'
        context['can_edit_datetime'] = sample.current_status == 'RECEIVED_FRONT_DESK'
        context['status_display'] = sample.get_current_status_display()
        
        return context

@lab_required
def test_result_entry(request, sample_id):
    sample = get_object_or_404(Sample, sample_id=sample_id)
    
    # Check if sample is in correct status for testing
    allowed_statuses_for_entry = ['SENT_TO_LAB', 'TESTING_IN_PROGRESS', 'RESULTS_ENTERED']
    if request.user.is_admin and sample.current_status == 'REVIEW_PENDING': # Admins can correct results in REVIEW_PENDING
        allowed_statuses_for_entry.append('REVIEW_PENDING')

    if sample.current_status not in allowed_statuses_for_entry:
        messages.error(request, f'Sample is not available for result entry/correction. Current status: {sample.get_current_status_display()}')
        return redirect('core:sample_detail', pk=sample.sample_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                original_status_was_review_pending = (sample.current_status == 'REVIEW_PENDING')

                if sample.current_status == 'SENT_TO_LAB':
                    sample.update_status('TESTING_IN_PROGRESS', request.user)
                
                results_entered_count = 0
                results_updated_count = 0
                all_forms_valid = True
                form_errors = {} # Not currently used to re-render, but good for debugging

                for test_param_model in sample.tests_requested.all().order_by('display_order', 'name'):
                    form_prefix = f'param_{test_param_model.parameter_id}'
                    form = TestResultEntryForm(request.POST, prefix=form_prefix)

                    if form.is_valid():
                        result_value = form.cleaned_data['result_value']
                        observation = form.cleaned_data['observation']
                        remarks = form.cleaned_data.get('remarks')

                        if result_value and result_value.strip(): # Ensure result_value is not just whitespace
                            test_result, created = TestResult.objects.get_or_create(
                                sample=sample,
                                parameter=test_param_model,
                                defaults={
                                    'result_value': result_value.strip(),
                                    'observation': observation,
                                    'remarks': remarks,
                                    'technician': request.user
                                }
                            )
                            if created:
                                AuditTrail.log_change(user=request.user, action='CREATE', instance=test_result, request=request)
                                test_result.full_clean()
                                results_entered_count += 1
                            else:
                                old_values = {'result_value': test_result.result_value, 'observation': test_result.observation, 'remarks': test_result.remarks}
                                test_result.result_value = result_value.strip()
                                test_result.observation = observation
                                test_result.remarks = remarks
                                test_result.full_clean()
                                test_result.save()
                                AuditTrail.log_change(user=request.user, action='UPDATE', instance=test_result, old_values=old_values, new_values=form.cleaned_data, request=request)
                                results_updated_count += 1
                    else:
                        all_forms_valid = False
                        form_errors[test_param_model.parameter_id] = form.errors
                        # We might want to re-render the form with errors instead of just a message
                        # For now, just collect errors and show a generic message.

                if not all_forms_valid:
                    # If any form is invalid, we should probably re-render the page with errors.
                    # For simplicity now, just show an error message and don't proceed with status updates.
                    messages.error(request, "There were errors in your submission. Please correct them and try again.")
                    # To re-render with errors, we'd need to reconstruct form_data as in GET and pass form_errors
                    # This part needs more robust error handling if we want to show specific field errors.
                    # For now, we'll let the transaction rollback if an exception occurs or just show a generic message.
                    # messages.error(request, f"Validation errors for {test_param_model.name}: {form.errors.as_json()}")
                    raise ValidationError(f"Form validation failed for {test_param_model.name}. Please check your input.")


                if original_status_was_review_pending:
                    # If admin edited while it was review pending, keep it review pending.
                    # Consultant needs to be aware that results might have changed.
                    # The sample status remains 'REVIEW_PENDING'.
                    messages.info(request, f"Results for sample (ID: {sample.sample_id}) updated by admin. The sample remains in 'Review Pending' status.")
                else:
                    # Check if all required tests have results
                    total_tests = sample.tests_requested.count()
                    completed_tests = sample.results.count()
                    
                    if completed_tests >= total_tests and total_tests > 0:
                        sample.update_status('RESULTS_ENTERED', request.user)
                        messages.success(request, f'All test results entered for sample {sample.sample_id}. Sample moved to "Results Entered" status.')
                    else:
                        messages.info(request, f'Results saved. {completed_tests}/{total_tests} tests completed.')
                
                if results_entered_count > 0:
                    messages.success(request, f'{results_entered_count} new test results entered.')
                if results_updated_count > 0:
                    messages.info(request, f'{results_updated_count} test results updated.')
                
                return redirect('core:sample_detail', pk=sample.sample_id)
                
        except Exception as exc:
            logger.exception("Failed to save test results for sample %s", sample.sample_id)
            messages.error(request, _format_error_message('Error saving test results.', exc))
            return redirect('core:sample_detail', pk=sample.sample_id)
    
    # GET request - show form
    form_data = {}
    for test_param_model in sample.tests_requested.all().order_by('display_order', 'name'):
        form_prefix = f'param_{test_param_model.parameter_id}'
        
        # Check if result already exists
        try:
            existing_result = TestResult.objects.get(sample=sample, parameter=test_param_model)
            initial_data = {
                'result_value': existing_result.result_value,
                'observation': existing_result.observation,
                'remarks': existing_result.remarks
            }
        except TestResult.DoesNotExist:
            initial_data = {}
            existing_result = None
        
        form_data[test_param_model.parameter_id] = {
            'form': TestResultEntryForm(prefix=form_prefix, initial=initial_data, parameter=test_param_model),
            'parameter': test_param_model,
            'existing_result': existing_result
        }
        
        # Clear existing_result for next iteration
        if 'existing_result' in locals():
            del existing_result
    
    context = {
        'sample': sample,
        'form_data': form_data,
        'can_edit': sample.current_status in ['SENT_TO_LAB', 'TESTING_IN_PROGRESS', 'RESULTS_ENTERED'] or (request.user.is_admin() and sample.current_status == 'REVIEW_PENDING')
    }
    
    return render(request, 'core/test_result_entry.html', context)

@consultant_required
def consultant_review(request, sample_id):
    sample = get_object_or_404(Sample, sample_id=sample_id)
    
    # If sample is in 'RESULTS_ENTERED', try to move it to 'REVIEW_PENDING'
    if sample.current_status == 'RESULTS_ENTERED':
        if request.user.is_consultant() or request.user.is_admin():
            try:
                sample.update_status('REVIEW_PENDING', request.user)
                messages.info(request, f"Sample {sample.sample_id} moved to 'Review Pending' status.")
                # Important: redirect to refresh the page and sample object,
                # or at least re-fetch sample if not redirecting.
                # For simplicity, redirecting ensures clean state.
                return redirect('core:consultant_review', sample_id=sample.sample_id)
            except ValidationError as e:
                error_message = str(e.message_dict) if hasattr(e, 'message_dict') else str(e)
                messages.error(request, f"Could not move sample to review: {error_message}")
                return redirect('core:sample_detail', pk=sample.sample_id)
            except Exception as exc:
                logger.exception(
                    "Unexpected error while moving sample %s to review pending",
                    sample.sample_id,
                )
                messages.error(
                    request,
                    _format_error_message(
                        "An unexpected error occurred while updating status.",
                        exc,
                    ),
                )
                return redirect('core:sample_detail', pk=sample.sample_id)
        else:
            # This case should ideally not be hit if template logic is correct
            messages.error(request, "You do not have permission to move this sample to review.")
            return redirect('core:sample_detail', pk=sample.sample_id)

    # Check if sample is ready for review (now it should be REVIEW_PENDING or error occurred)
    if sample.current_status != 'REVIEW_PENDING':
        # This message will show if the above status update failed or if accessed directly with wrong status
        messages.error(request, f'Sample is not available for review. Current status: {sample.get_current_status_display()}')
        return redirect('core:sample_detail', pk=sample.sample_id)
    
    # Check if review already exists
    try:
        review = ConsultantReview.objects.get(sample=sample)
    except ConsultantReview.DoesNotExist:
        review = None
    
    if request.method == 'POST':
        action = request.POST.get('status') # Changed from 'action' to 'status'
        comments = request.POST.get('comments', '').strip()
        recommendations = request.POST.get('recommendations', '').strip()
        
        if action in ['APPROVED', 'REJECTED']:
            try:
                with transaction.atomic():
                    if review:
                        # Update existing review
                        old_values = {
                            'status': review.status,
                            'comments': review.comments,
                            'recommendations': review.recommendations
                        }
                        review.status = action
                        review.comments = comments
                        review.recommendations = recommendations
                        review.reviewer = request.user
                        review.review_date = timezone.now()
                        review.save()
                        AuditTrail.log_change(user=request.user, action='UPDATE', instance=review, old_values=old_values, new_values=request.POST.dict(), request=request)
                    else:
                        # Create new review
                        review = ConsultantReview.objects.create(
                            sample=sample,
                            reviewer=request.user,
                            status=action,
                            comments=comments,
                            recommendations=recommendations
                        )
                        AuditTrail.log_change(user=request.user, action='CREATE', instance=review, request=request)
                    
                    # The ConsultantReview.save() method now handles updating the sample status.
                    # So, no need to call sample.update_status() here directly.
                    # Messages will be based on the review action.
                    if action == 'APPROVED':
                        messages.success(request, f'Review for sample {sample.sample_id} saved as Approved. Sample status updated accordingly.')
                    elif action == 'REJECTED':
                        messages.warning(request, f'Review for sample {sample.sample_id} saved as Rejected. Sample status updated accordingly.')
                    else: # Should not happen if action is validated, but as a fallback
                        messages.info(request, f'Review for sample {sample.sample_id} saved with status {action}.')

                    return redirect('core:sample_detail', pk=sample.sample_id)
                    
            except Exception as exc:
                logger.exception("Failed to process consultant review for sample %s", sample.sample_id)
                messages.error(request, _format_error_message('Error processing review.', exc))
                return redirect('core:sample_detail', pk=sample.sample_id)
        else:
            messages.error(request, 'Invalid action specified.')
    
    # GET request - show review form
    context = {
        'sample': sample,
        'review': review,
        'test_results': sample.results.all().select_related('parameter'),
        'can_review': sample.current_status == 'REVIEW_PENDING'
    }
    
    return render(request, 'core/consultant_review.html', context)

@login_required
def download_sample_report_view(request, pk):
    sample = get_object_or_404(Sample, pk=pk)

    if sample.current_status not in ['REPORT_APPROVED', 'REPORT_SENT']:
        messages.error(request, "Report is not yet approved or available for download.")
        return redirect('core:sample_detail', pk=sample.pk)

    import os
    from django.conf import settings
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.utils import ImageReader

    buffer = BytesIO()

    class ReportDocTemplate(BaseDocTemplate):
        def __init__(self, filename, **kwargs):
            super().__init__(filename, **kwargs)
            self.addPageTemplates([
                PageTemplate(id='ReportPage',
                             frames=[Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='main_frame')],
                             onPage=self.header,
                             onPageEnd=self.footer)
            ])

        def header(self, canvas, doc):
            canvas.saveState()
            page_width, page_height = doc.pagesize
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'biofix_logo.png')
            top_band_y = page_height - 25*mm

            if os.path.exists(logo_path):
                logo = ImageReader(logo_path)
                canvas.drawImage(
                    logo,
                    doc.leftMargin,
                    page_height - 38*mm,
                    width=45*mm,
                    height=17*mm,
                    preserveAspectRatio=True,
                )

            canvas.setFont('Helvetica-Bold', 11)
            canvas.setFillColor(colors.HexColor('#0F172A'))
            canvas.drawRightString(page_width - doc.rightMargin, page_height - 28*mm, 'Biofix Laboratory')
            canvas.setFont('Helvetica', 9)
            canvas.drawRightString(page_width - doc.rightMargin, page_height - 32*mm, '123 Science Avenue, Research City, 12345')
            canvas.drawRightString(page_width - doc.rightMargin, page_height - 36*mm, 'Phone: (123) 456-7890  |  Email: contact@biofixlab.com')

            canvas.setFont('Helvetica-Bold', 16)
            canvas.setFillColor(colors.HexColor('#0F766E'))
            canvas.drawCentredString(page_width / 2, page_height - 52*mm, 'WATER QUALITY ANALYSIS REPORT')

            canvas.restoreState()

        def footer(self, canvas, doc):
            canvas.saveState()
            styles = getSampleStyleSheet()
            
            footer_text = f"Page {doc.page} | Report ID: {sample.display_id}"
            p = Paragraph(footer_text, styles['Normal'])
            p.wrapOn(canvas, doc.width, doc.bottomMargin)
            p.drawOn(canvas, doc.leftMargin, 10*mm)
            
            canvas.restoreState()

    doc = ReportDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18*mm,
        leftMargin=18*mm,
        topMargin=60*mm,
        bottomMargin=22*mm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='ReportTitle', parent=styles['h1'], alignment=TA_CENTER, spaceAfter=14, fontSize=18))
    styles.add(ParagraphStyle(name='SectionTitle', parent=styles['h2'], spaceAfter=10, fontSize=12, leading=14))
    styles.add(ParagraphStyle(name='Label', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#6B7280')))
    styles.add(ParagraphStyle(name='Value', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#0F172A')))
    styles.add(ParagraphStyle(name='TableHead', parent=styles['Normal'], fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.white, fontSize=9))
    styles.add(ParagraphStyle(name='TableCell', parent=styles['Normal'], alignment=TA_LEFT, leading=12, fontSize=9))

    surface = colors.HexColor('#F8FAFC')
    primary = colors.HexColor('#0F766E')
    text_color = colors.HexColor('#0F172A')

    styles.add(ParagraphStyle(
        name='CategoryHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=text_color,
        spaceBefore=10,
        spaceAfter=6,
    ))

    styles['ReportTitle'].textColor = primary
    styles['SectionTitle'].textColor = primary
    styles['Normal'].textColor = text_color

    elements = []
    elements.append(Spacer(1, 8))

    meta_rows = [
        [Paragraph('<b>Sample Code</b>', styles['Label']), Paragraph(sample.display_id or 'N/A', styles['Value']),
         Paragraph('<b>ULR Number</b>', styles['Label']), Paragraph(sample.ulr_number or 'N/A', styles['Value'])],
        [Paragraph('<b>Customer</b>', styles['Label']), Paragraph(sample.customer.name or 'N/A', styles['Value']),
         Paragraph('<b>Report Number</b>', styles['Label']), Paragraph(sample.report_number or 'N/A', styles['Value'])],
        [Paragraph('<b>Sample Source</b>', styles['Label']), Paragraph(sample.get_sample_source_display() or 'N/A', styles['Value']),
         Paragraph('<b>Collected On</b>', styles['Label']), Paragraph(sample.collection_datetime.strftime('%d %b %Y %H:%M') if sample.collection_datetime else 'N/A', styles['Value'])],
        [Paragraph('<b>Received At Lab</b>', styles['Label']), Paragraph(sample.date_received_at_lab.strftime('%d %b %Y %H:%M') if sample.date_received_at_lab else 'N/A', styles['Value']),
         Paragraph('<b>Location</b>', styles['Label']), Paragraph(sample.sampling_location or 'N/A', styles['Value'])],
        [Paragraph('<b>Test Commenced</b>', styles['Label']), Paragraph(sample.test_commenced_on.strftime('%d %b %Y') if sample.test_commenced_on else 'N/A', styles['Value']),
         Paragraph('<b>Test Completed</b>', styles['Label']), Paragraph(sample.test_completed_on.strftime('%d %b %Y') if sample.test_completed_on else 'N/A', styles['Value'])]
    ]
    meta_table = Table(meta_rows, colWidths=[32*mm, 55*mm, 32*mm, doc.width - 119*mm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), surface),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 16))

    address_table = Table([
        [Paragraph('<b>Customer Address</b>', styles['Label'])],
        [Paragraph(sample.customer.address or 'N/A', styles['Value'])]
    ], colWidths=[doc.width])
    address_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#E2E8F0')),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
    ]))
    elements.append(address_table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("TEST OUTCOMES", styles['SectionTitle']))
    elements.append(Spacer(1, 6))

    # Respect configured display order within categories
    results_queryset = sample.results.select_related('parameter').order_by('parameter__category_obj__display_order', 'parameter__display_order', 'parameter__name')
    results = list(results_queryset)

    section_templates = OrderedDict([
        ('physical', {'title': 'Physical Parameters', 'categories': OrderedDict()}),
        ('chemical', {'title': 'Chemical Parameters', 'categories': OrderedDict()}),
        ('microbiological', {'title': 'Microbiological Parameters', 'categories': OrderedDict()}),
        ('other', {'title': 'Other Parameters', 'categories': OrderedDict()}),
    ])

    def _section_for_category(label: str) -> str:
        lowered = label.casefold()
        if 'physical' in lowered:
            return 'physical'
        if 'chemical' in lowered:
            return 'chemical'
        if any(token in lowered for token in ('micro', 'bacter', 'pathogen')):
            return 'microbiological'
        return 'other'

    for result in results:
        # Prefer structured category; fallback to legacy text
        display_label = (getattr(result.parameter, 'category_label', '') or '').strip() or 'Uncategorized'
        section_key = _section_for_category(display_label)
        categories = section_templates[section_key]['categories']
        if display_label not in categories:
            categories[display_label] = []
        categories[display_label].append(result)

    available_width = doc.width
    column_widths = [
        available_width * 0.06,  # Sl. No
        available_width * 0.24,  # Parameter
        available_width * 0.14,  # Method
        available_width * 0.09,  # Result
        available_width * 0.08,  # Unit
        available_width * 0.17,  # Limits
        available_width * 0.10,  # Status
        available_width * 0.12,  # Observation
    ]

    def _build_results_table(category_results, start_index):
        header = [
            Paragraph('Sl. No', styles['TableHead']),
            Paragraph('Parameter', styles['TableHead']),
            Paragraph('Method', styles['TableHead']),
            Paragraph('Result', styles['TableHead']),
            Paragraph('Unit', styles['TableHead']),
            Paragraph('Limits', styles['TableHead']),
            Paragraph('Status', styles['TableHead']),
            Paragraph('Test outcomes', styles['TableHead'])
        ]
        table_data = [header]

        def format_limits(param):
            if param.min_permissible_limit is None and param.max_permissible_limit is None:
                return '—'
            if param.min_permissible_limit is None:
                return f"≤ {param.max_permissible_limit} {param.unit or ''}".strip()
            if param.max_permissible_limit is None:
                return f"≥ {param.min_permissible_limit} {param.unit or ''}".strip()
            return f"{param.min_permissible_limit} – {param.max_permissible_limit} {param.unit or ''}".strip()

        running_index = start_index
        for result in category_results:
            param = result.parameter
            limits_text = format_limits(param)
            status = getattr(result, 'get_limit_status', lambda: None)()
            if status == 'WITHIN_LIMITS':
                status_label = '<font color="#0F766E">Within limits</font>'
            elif status == 'BELOW_LIMIT':
                status_label = '<font color="#B45309">Below minimum</font>'
            elif status == 'ABOVE_LIMIT':
                status_label = '<font color="#DC2626">Above maximum</font>'
            elif status == 'NON_NUMERIC':
                status_label = 'Non-numeric'
            else:
                status_label = '—'

            table_data.append([
                Paragraph(str(running_index), styles['TableCell']),
                Paragraph(param.name or '—', styles['TableCell']),
                Paragraph(param.method or '—', styles['TableCell']),
                Paragraph(result.result_value or '—', styles['TableCell']),
                Paragraph(param.unit or '—', styles['TableCell']),
                Paragraph(limits_text, styles['TableCell']),
                Paragraph(status_label, styles['TableCell']),
                Paragraph(result.observation or result.remarks or '—', styles['TableCell'])
            ])
            running_index += 1

        table = Table(table_data, colWidths=column_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), (colors.white, colors.HexColor('#F1F5F9'))),
            ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#E2E8F0')),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        return table, running_index

    def _render_section(section_key: str, heading: str):
        section = section_templates[section_key]
        elements.append(Paragraph(heading, styles['SectionTitle']))
        elements.append(Spacer(1, 6))
        if section['categories']:
            serial_counter = 1
            for category_label, category_results in section['categories'].items():
                elements.append(Paragraph(category_label, styles['CategoryHeading']))
                table, serial_counter = _build_results_table(category_results, serial_counter)
                elements.append(table)
                elements.append(Spacer(1, 12))
        else:
            elements.append(Paragraph("No parameters recorded for this category.", styles['Normal']))
            elements.append(Spacer(1, 12))

    _render_section('physical', 'Physical Parameters')
    elements.append(PageBreak())
    _render_section('chemical', 'Chemical Parameters')
    elements.append(PageBreak())
    _render_section('microbiological', 'Microbiological Parameters')

    review = getattr(sample, 'review', None)
    if review:
        recommendations_text = (review.recommendations or '').strip()
    else:
        recommendations_text = ''

    elements.append(Paragraph("Consultant Recommendations", styles['SectionTitle']))
    if recommendations_text:
        safe_text = escape(recommendations_text).replace('\n', '<br/>')
        elements.append(Paragraph(safe_text, styles['Normal']))
    else:
        elements.append(Paragraph("No consultant recommendations recorded for this sample.", styles['Normal']))
    elements.append(Spacer(1, 18))

    elements.append(Paragraph("REMARKS", styles['SectionTitle']))
    elements.append(Paragraph(
        "The sample has been analysed in accordance with IS 10500:2012 guidelines. Outcomes above include automated compliance status for each parameter.",
        styles['Normal']
    ))
    elements.append(Spacer(1, 18))

    elements.append(Paragraph("AUTHORISED SIGNATORIES", styles['SectionTitle']))
    signatory_names = [
        sample.food_analyst.get_full_name() if sample.food_analyst else 'Food Analyst',
        sample.reviewed_by.get_full_name() if sample.reviewed_by else 'Deputy Technical Manager – Biological',
        sample.lab_manager.get_full_name() if sample.lab_manager else 'Technical Manager – Chemical'
    ]
    signatory_roles = ['Food Analyst', 'Deputy Technical Manager – Biological', 'Technical Manager – Chemical']

    sign_rows = [[
        Paragraph(f"<b>{signatory_names[0]}</b><br/>{signatory_roles[0]}", styles['Center']),
        Paragraph(f"<b>{signatory_names[1]}</b><br/>{signatory_roles[1]}", styles['Center']),
        Paragraph(f"<b>{signatory_names[2]}</b><br/>{signatory_roles[2]}", styles['Center'])
    ]]
    sign_table = Table(sign_rows, colWidths=[58*mm, 58*mm, 58*mm])
    sign_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 12)
    ]))
    elements.append(sign_table)

    doc.build(elements)

    buffer.seek(0)
    response = FileResponse(buffer, as_attachment=True, filename=f'WaterQualityReport_{sample.display_id}.pdf')
    
    if sample.current_status == 'REPORT_APPROVED':
        try:
            sample.update_status('REPORT_SENT', request.user)
            messages.info(request, f"Report for sample {sample.display_id} downloaded and status updated to 'Report Sent'.")
        except Exception as exc:
            logger.exception(
                "Failed to update sample %s status after report download",
                sample.sample_id,
            )
            messages.warning(
                request,
                _format_error_message(
                    "Report downloaded, but failed to update sample status.",
                    exc,
                ),
            )

    return response

@login_required
def sample_status_update(request, sample_id):
    sample = get_object_or_404(Sample, sample_id=sample_id)

    if request.method == 'POST':
        # Check permissions: Front Desk, Lab Tech or Admin
        if not (request.user.is_frontdesk() or request.user.is_admin() or request.user.is_lab_tech()):
            messages.error(request, "You do not have permission to perform this action.")
            return redirect('core:sample_detail', pk=sample.sample_id)

        new_status = request.POST.get('new_status')
        
        # Validate new_status
        valid_status_codes = [s[0] for s in Sample.SAMPLE_STATUS_CHOICES]
        if not new_status or new_status not in valid_status_codes:
            messages.error(request, "Invalid target status provided.")
            return redirect('core:sample_detail', pk=sample.sample_id)

        try:
            sample.update_status(new_status, request.user)
            
            new_status_display_tuple = next((s for s in Sample.SAMPLE_STATUS_CHOICES if s[0] == new_status), None)
            new_status_display_name = new_status_display_tuple[1] if new_status_display_tuple else new_status
            
            messages.success(request, f"Sample {sample.sample_id} status successfully updated to '{new_status_display_name}'.")
        
        except ValidationError as e:
            # The ValidationError from update_status can be a list of messages or a single one.
            error_message = str(e.message_dict) if hasattr(e, 'message_dict') else str(e)
            messages.error(request, f"Error updating status: {error_message}")
        
        except Exception as exc:
            # Catch any other unexpected errors
            logger.exception("Unexpected error in sample_status_update for sample %s", sample.sample_id)
            messages.error(
                request,
                _format_error_message("An unexpected error occurred while updating sample status.", exc),
            )

        return redirect('core:sample_detail', pk=sample.sample_id)

    # For GET requests: redirect to detail page. 
    # Status changes should only occur via POST.
    # Optionally, add a message or return HttpResponseNotAllowed for GET.
    return redirect('core:sample_detail', pk=sample.sample_id)

@login_required
@admin_required  # Or specific role required for managing test parameters
def setup_test_parameters(request):
    """Admin view to seed and manage TestParameter records.

    The page shows a one-click action to create a standard set of parameters.
    Previously, the POST tried to validate an empty TestParameterForm which
    resulted in a generic "Error in form submission" message. Here we detect
    the seed action explicitly and create parameters programmatically
    (skipping any that already exist by name).
    """

    # Helpers
    def _next_order_for(_: TestCategory | None) -> int:
        last = TestParameter.objects.order_by('-display_order').first()
        base = (last.display_order if last and last.display_order else 0)
        # Step by 10 to leave room for inserts
        return (base // 10 + 1) * 10 if base else 10

    # Filters and data
    categories = TestCategory.objects.all().order_by('display_order', 'name')
    selected_category_id = request.GET.get('category') or request.POST.get('category')
    selected_category = None
    if selected_category_id:
        try:
            selected_category = categories.get(pk=selected_category_id)
        except Exception:
            selected_category = None

    # List existing parameters and show a form for manual add/edit
    parameters_qs = TestParameter.objects.all()
    if selected_category:
        parameters_qs = parameters_qs.filter(category_obj=selected_category)
    parameters = parameters_qs.order_by('display_order', 'name')
    form = TestParameterForm()
    # Pre-fill recommended order if a category is chosen
    if selected_category:
        form.fields['category_obj'].initial = selected_category.pk
        form.fields['display_order'].initial = _next_order_for(selected_category)

    if request.method == 'POST':
        # If the POST is from the "Create Standard Parameters" button, it won't
        # include model fields. Detect that and seed defaults instead of
        # attempting to validate an empty form.
        action = request.POST.get('action')
        if action == 'create_standard' or not any(request.POST.get(k) for k in ['name', 'unit']):
            try:
                from core.services.parameters import seed_standard_parameters
                created_count, skipped = seed_standard_parameters(user=request.user)
                messages.success(
                    request,
                    f"Standard parameters processed. Created {created_count} new parameter(s); {skipped} existing."
                )
                return redirect('core:setup_test_parameters')
            except Exception as exc:
                logger.exception("Failed to seed standard test parameters")
                messages.error(
                    request,
                    _format_error_message("Error creating standard parameters.", exc),
                )
        else:
            # Manual single-parameter creation via form
            form = TestParameterForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        # If no order provided, place at the end of the selected (or global) list
                        if not form.cleaned_data.get('display_order'):
                            form.instance.display_order = _next_order_for(form.cleaned_data.get('category_obj'))
                        parameter = form.save()
                        AuditTrail.log_change(user=request.user, action='CREATE', instance=parameter, request=request)
                        messages.success(request, f"Test parameter '{parameter.name}' created successfully.")
                        if selected_category:
                            return redirect(f"{reverse_lazy('core:setup_test_parameters')}?category={selected_category.pk}")
                        return redirect('core:setup_test_parameters')
                except Exception as exc:
                    logger.exception("Failed to create test parameter via setup view")
                    messages.error(
                        request,
                        _format_error_message("Error creating test parameter.", exc),
                    )
            else:
                messages.error(request, "Error in form submission. Please check the details.")

    context = {
        'existing_params': parameters,
        'parameters': parameters,
        'categories': categories,
        'selected_category': selected_category,
        'next_order': _next_order_for(selected_category) if selected_category or parameters.exists() else 10,
        'form': form,
        'page_title': 'Setup Test Parameters',
    }
    return render(request, 'core/setup_test_parameters.html', context)


@login_required
@admin_required
@require_POST
def reorder_test_parameters(request):
    """Reorder parameters via drag-and-drop.

    Body: JSON { "order": [parameter_id, ...], "category": <optional category pk> }
    Only reorders the provided list, assigning display_order = 10,20,... in
    the sequence received. If a category is provided, we validate that every
    ID belongs to that category.
    """
    import json
    from django.http import JsonResponse

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        payload = request.POST

    groups = payload.get('groups')
    if groups:
        updated_total = 0
        with transaction.atomic():
            for group in groups:
                ids = group.get('order') or []
                category_id = group.get('category')
                # Accept null category (uncategorised)
                qs = TestParameter.objects.filter(parameter_id__in=ids)
                if category_id:
                    try:
                        cat = TestCategory.objects.get(pk=category_id)
                    except TestCategory.DoesNotExist:
                        return JsonResponse({"ok": False, "error": f"Invalid category {category_id}"}, status=400)
                    qs = qs.filter(category_obj=cat)
                else:
                    qs = qs.filter(category_obj__isnull=True)

                found_ids = set(str(x) for x in qs.values_list('parameter_id', flat=True))
                missing = [i for i in ids if str(i) not in found_ids]
                if missing:
                    return JsonResponse({"ok": False, "error": f"Unknown parameter ids: {', '.join(missing)}"}, status=400)

                obj_by_id = {str(obj.parameter_id): obj for obj in qs}
                running = 10
                changed = []
                for pid in ids:
                    obj = obj_by_id[str(pid)]
                    if obj.display_order != running:
                        obj.display_order = running
                        changed.append(obj)
                    running += 10
                if changed:
                    TestParameter.objects.bulk_update(changed, ['display_order'])
                    updated_total += len(changed)
        return JsonResponse({"ok": True, "updated": updated_total})
    else:
        order_payload = payload.get('order')
        if not isinstance(order_payload, list) or not order_payload:
            return JsonResponse({"ok": False, "error": "No order provided."}, status=400)

        def _normalise(item):
            if isinstance(item, dict):
                value = item.get('id')
            else:
                value = item
            return str(value) if value else None

        ids = [pid for pid in (_normalise(item) for item in order_payload) if pid]
        if not ids:
            return JsonResponse({"ok": False, "error": "Invalid IDs."}, status=400)

        raw_category = payload.get('category')
        if raw_category not in (None, '', 'null', 'None'):
            mode = 'category'
            try:
                category_obj = TestCategory.objects.get(pk=raw_category)
            except TestCategory.DoesNotExist:
                return JsonResponse({"ok": False, "error": f"Invalid category {raw_category}"}, status=400)
        elif raw_category in ('null', 'None'):
            mode = 'uncategorized'
            category_obj = None
        else:
            mode = 'global'
            category_obj = None

        def apply_global_sequence(sequence):
            objs = list(TestParameter.objects.filter(parameter_id__in=sequence))
            if len(objs) != len(sequence):
                found = {str(obj.parameter_id) for obj in objs}
                missing = [pid for pid in sequence if pid not in found]
                return None, JsonResponse({"ok": False, "error": f"Unknown parameter ids: {', '.join(missing)}"}, status=400)
            obj_by_id = {str(obj.parameter_id): obj for obj in objs}
            running = 10
            changed = []
            for pid in sequence:
                obj = obj_by_id[str(pid)]
                if obj.display_order != running:
                    obj.display_order = running
                    changed.append(obj)
                running += 10
            if changed:
                TestParameter.objects.bulk_update(changed, ['display_order'])
            return len(changed), None

        if mode == 'global':
            total = TestParameter.objects.count()
            if len(ids) != total:
                return JsonResponse({"ok": False, "error": "Full order required for global reorder."}, status=400)
            updated, error_response = apply_global_sequence(ids)
            if error_response:
                return error_response
            return JsonResponse({"ok": True, "updated": updated})

        # Category-specific reorder, rebuild the full sequence preserving other categories.
        def matches(cat_id):
            if mode == 'category':
                return cat_id == category_obj.pk
            return cat_id is None  # uncategorized

        all_rows = list(TestParameter.objects.order_by('display_order', 'name').values_list('parameter_id', 'category_obj_id'))
        current_subset = [str(pid) for pid, cat_id in all_rows if matches(cat_id)]
        if len(current_subset) != len(ids) or set(current_subset) != set(ids):
            return JsonResponse({"ok": False, "error": "Provided IDs do not match the selected category contents."}, status=400)

        ids_iter = iter(ids)
        rebuilt_sequence = []
        for pid, cat_id in all_rows:
            if matches(cat_id):
                rebuilt_sequence.append(next(ids_iter))
            else:
                rebuilt_sequence.append(str(pid))

        updated, error_response = apply_global_sequence(rebuilt_sequence)
        if error_response:
            return error_response
        return JsonResponse({"ok": True, "updated": updated})

class TestParameterUpdateView(AdminRequiredMixin, UpdateView):
    model = TestParameter
    form_class = TestParameterForm
    template_name = 'core/test_parameter_form.html' # Assuming a generic form template
    success_url = reverse_lazy('core:setup_test_parameters')

    def form_valid(self, form):
        try:
            with transaction.atomic():
                old_values = TestParameter.objects.filter(pk=self.object.pk).values().first()
                parameter = form.save()
                # Fetch DB-serializable field values for audit logging to avoid JSON serialization errors
                new_values = TestParameter.objects.filter(pk=parameter.pk).values().first()
                AuditTrail.log_change(
                    user=self.request.user,
                    action='UPDATE',
                    instance=parameter,
                    old_values=old_values,
                    new_values=new_values,
                    request=self.request,
                )
                messages.success(self.request, f"Test parameter '{parameter.name}' updated successfully.")
        except Exception as exc:
            logger.exception("Failed to update test parameter %s", self.object.pk)
            messages.error(
                self.request,
                _format_error_message("Error updating test parameter.", exc),
            )
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit Test Parameter: {self.object.name}'
        context['is_edit'] = True # For template to adapt if needed
        return context


@login_required
@admin_required
def setup_test_categories(request):
    categories = TestCategory.objects.all().order_by('display_order', 'name')
    from django import forms

    class TestCategoryForm(forms.ModelForm):
        class Meta:
            model = TestCategory
            fields = ['name', 'display_order']
            widgets = {
                'name': forms.TextInput(attrs={'class': 'form-control'}),
                'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            }

    form = TestCategoryForm()
    if request.method == 'POST':
        form = TestCategoryForm(request.POST)
        if form.is_valid():
            obj = form.save()
            AuditTrail.log_change(user=request.user, action='CREATE', instance=obj, request=request)
            messages.success(request, f"Category '{obj.name}' created.")
            return redirect('core:setup_test_categories')
        else:
            messages.error(request, "Error in form submission.")

    return render(request, 'core/setup_test_categories.html', {
        'form': form,
        'categories': categories,
        'page_title': 'Setup Categories',
    })


class TestCategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = TestCategory
    fields = ['name', 'display_order']
    template_name = 'core/test_category_form.html'
    success_url = reverse_lazy('core:setup_test_categories')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit Category: {self.object.name}'
        context['is_edit'] = True
        return context


@login_required
@admin_required
@require_POST
def delete_test_category(request, pk):
    category = get_object_or_404(TestCategory, pk=pk)
    name = category.name
    try:
        with transaction.atomic():
            old_values = {'name': name, 'display_order': category.display_order}
            AuditTrail.log_change(user=request.user, action='DELETE', instance=category, old_values=old_values, new_values={}, request=request)
            category.delete()
            messages.success(request, f"Category '{name}' deleted.")
    except Exception as exc:
        logger.exception("Failed to delete category %s", pk)
        messages.error(request, _format_error_message("Error deleting category.", exc))
    return redirect('core:setup_test_categories')


@login_required
def kerala_locations_json(request):
    """Return district -> taluk -> local body names from the DB.

    If no KeralaLocation rows exist, respond with 204 so the client falls
    back to the bundled static JSON.
    """
    from .models import KeralaLocation
    if not KeralaLocation.objects.exists():
        return JsonResponse({}, status=204)

    data = {}
    districts = KeralaLocation.objects.filter(location_type='district').order_by('name')
    taluks = KeralaLocation.objects.filter(location_type='taluk').select_related('parent')
    local_bodies = KeralaLocation.objects.exclude(location_type__in=['district','taluk']).select_related('parent')

    taluks_by_district = {}
    for t in taluks:
        taluks_by_district.setdefault(t.parent_id, []).append(t)

    locals_by_taluk = {}
    for lb in local_bodies:
        locals_by_taluk.setdefault(lb.parent_id, []).append(lb)

    for d in districts:
        data[d.name] = {}
        for t in sorted(taluks_by_district.get(d.id, []), key=lambda x: x.name):
            names = [x.name for x in sorted(locals_by_taluk.get(t.id, []), key=lambda x: x.name)]
            data[d.name][t.name] = names

    return JsonResponse(data)


@login_required
@admin_required
@require_POST
def delete_test_parameter(request, pk):
    parameter = get_object_or_404(TestParameter, pk=pk)
    parameter_name = parameter.name

    try:
        with transaction.atomic():
            old_values = model_to_dict(parameter)
            AuditTrail.log_change(
                user=request.user,
                action='DELETE',
                instance=parameter,
                old_values=old_values,
                new_values={},
                request=request,
            )
            parameter.delete()
            messages.success(request, f"Test parameter '{parameter_name}' deleted successfully.")
    except ProtectedError:
        messages.error(
            request,
            f"Cannot delete '{parameter_name}' because test results are linked to it.",
        )
    except Exception as exc:
        logger.exception("Failed to delete test parameter %s", pk)
        messages.error(
            request,
            _format_error_message("Error deleting test parameter.", exc),
        )

    return redirect('core:setup_test_parameters')
