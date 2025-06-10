from django.shortcuts import render, get_object_or_404, redirect
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

from .models import Customer, Sample, TestParameter, TestResult, ConsultantReview, CustomUser, AuditTrail
from .forms import CustomerForm, SampleForm, CustomPasswordChangeForm, TestResultEntryForm, TestParameterForm # Added TestParameterForm
from .decorators import admin_required, lab_required, frontdesk_required, consultant_required
from .mixins import AdminRequiredMixin, LabRequiredMixin, FrontDeskRequiredMixin, ConsultantRequiredMixin, RoleRequiredMixin, AuditMixin

# Health check endpoint for deployment monitoring
from django.http import HttpResponse, FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from io import BytesIO

def health_check(request):
    """Health check endpoint for load balancers and monitoring systems"""
    return HttpResponse("healthy", content_type="text/plain")

def debug_admin(request):
    """Debug endpoint to check admin user - REMOVE IN PRODUCTION"""
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
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", content_type="text/plain")

def create_admin_web(request):
    """Web endpoint to create admin user - REMOVE IN PRODUCTION"""
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
    except Exception as e:
        return HttpResponse(f"Error creating admin: {str(e)}", content_type="text/plain")

def debug_view(request):
    """Debug endpoint to check configuration and functionality"""
    from django.conf import settings
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
    except Exception as e:
        debug_info.append(f"Database error: {e}")
    
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
        
    except Exception as e:
        return HttpResponse(f"Error fixing admin role: {str(e)}", content_type="text/plain")

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

        except Exception as e:
            # Log the error (in a real application, use proper logging)
            print(f"Error loading admin dashboard data: {e}")
            context['data_load_error'] = True
            # Optionally, send an alert to admin or log to a file/service
            # messages.error(self.request, "There was an error loading some dashboard data. Please try again later.")

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
    paginate_by = 50 # Optional: Add pagination

    def get_queryset(self):
        return AuditTrail.objects.all().order_by('-timestamp')

from django.db.models import Max

class TestResultListView(LoginRequiredMixin, ListView):
    model = Sample # Changed model to Sample
    template_name = 'core/test_result_list.html'
    context_object_name = 'samples_with_results' # Changed to match template
    paginate_by = 20

    def get_queryset(self):
        # Get samples that have at least one test result
        # Annotate with the date of the latest test result for sorting
        queryset = Sample.objects.annotate(
            latest_test_date=Max('results__test_date')
        ).filter(
            results__isnull=False # Ensure there's at least one related TestResult
        ).select_related(
            'customer' # Optimize customer fetching
        ).prefetch_related(
            'results', # Optimize fetching of related results for counts
            'tests_requested' # Optimize fetching of tests_requested for counts
        ).distinct().order_by('-latest_test_date', '-collection_datetime') # Order by most recent results first
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Samples with Test Results' # Updated title to be more descriptive
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

class SampleListView(LoginRequiredMixin, ListView): # Added LoginRequiredMixin
    model = Sample
    template_name = 'core/sample_list.html'
    context_object_name = 'samples'

class SampleDetailView(DetailView): # New DetailView for Sample
    model = Sample
    template_name = 'core/sample_detail.html'
    context_object_name = 'sample'

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
        
        # Additional validation for collection datetime changes
        if sample.current_status != 'RECEIVED_FRONT_DESK':
            if sample.collection_datetime != form.cleaned_data.get('collection_datetime'):
                messages.error(self.request,
                    'Cannot modify collection date/time after sample processing has begun.')
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

                for test_param_model in sample.tests_requested.all():
                    form_prefix = f'param_{test_param_model.parameter_id}'
                    form = TestResultEntryForm(request.POST, prefix=form_prefix)

                    if form.is_valid():
                        result_value = form.cleaned_data['result_value']
                        observation = form.cleaned_data['observation']

                        if result_value and result_value.strip(): # Ensure result_value is not just whitespace
                            test_result, created = TestResult.objects.get_or_create(
                                sample=sample,
                                parameter=test_param_model,
                                defaults={
                                    'result_value': result_value.strip(),
                                    'observation': observation,
                                    'technician': request.user
                                }
                            )
                            if created:
                                AuditTrail.log_change(user=request.user, action='CREATE', instance=test_result, request=request)
                                test_result.full_clean()
                                results_entered_count += 1
                            else:
                                old_values = {'result_value': test_result.result_value, 'observation': test_result.observation}
                                test_result.result_value = result_value.strip()
                                test_result.observation = observation
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
                
        except Exception as e:
            messages.error(request, f'Error saving test results: {str(e)}')
            return redirect('core:sample_detail', pk=sample.sample_id)
    
    # GET request - show form
    form_data = {}
    for test_param_model in sample.tests_requested.all():
        form_prefix = f'param_{test_param_model.parameter_id}'
        
        # Check if result already exists
        try:
            existing_result = TestResult.objects.get(sample=sample, parameter=test_param_model)
            initial_data = {
                'result_value': existing_result.result_value,
                'observation': existing_result.observation
            }
        except TestResult.DoesNotExist:
            initial_data = {}
        
        form_data[test_param_model.parameter_id] = {
            'form': TestResultEntryForm(prefix=form_prefix, initial=initial_data),
            'parameter': test_param_model,
            'existing_result': existing_result if 'existing_result' in locals() else None
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
            except Exception as e:
                messages.error(request, f"An unexpected error occurred while updating status: {str(e)}")
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
                    
            except Exception as e:
                messages.error(request, f'Error processing review: {str(e)}')
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
    from reportlab.lib.utils import ImageReader
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    buffer = BytesIO()
    
    # Enhanced color scheme matching CSS variables
    primary_color = colors.HexColor("#00796B")  # Biofix Teal from CSS
    secondary_color = colors.HexColor("#004D40")  # Darker teal
    accent_color = colors.HexColor("#E0F2F1")  # Light teal accent
    success_color = colors.HexColor("#388E3C")  # Green for normal values
    warning_color = colors.HexColor("#FFA000")  # Orange for warnings
    error_color = colors.HexColor("#D32F2F")  # Red for out-of-limit values
    text_color = colors.HexColor("#212121")  # Dark text
    light_gray = colors.HexColor("#F5F5F5")
    medium_gray = colors.HexColor("#E0E0E0")
    
    # Create canvas with enhanced styling
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setTitle(f"Water Quality Test Report - {sample.sample_id}")
    
    # Page dimensions
    page_width, page_height = A4
    left_margin = 25 * mm
    right_margin = page_width - 25 * mm
    top_margin = page_height - 25 * mm
    bottom_margin = 25 * mm
    content_width = right_margin - left_margin
    
    # Start with header
    y_position = top_margin
    
    # Header background
    header_height = 35 * mm # Further Increased header height for more space
    p.setFillColor(accent_color)
    p.rect(left_margin - 10*mm, y_position - header_height, content_width + 20*mm, header_height, stroke=0, fill=1)
    
    # Logo
    logo_width_final = 0
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'biofix_logo.png')
    if os.path.exists(logo_path):
        try:
            logo = ImageReader(logo_path)
            img_width, img_height = logo.getSize()
            aspect_ratio = img_height / img_width
            
            logo_max_height = 22 * mm 
            logo_final_height = logo_max_height
            logo_width_final = logo_final_height / aspect_ratio

            if logo_width_final > 50 * mm: # Max width for logo
                logo_width_final = 50 * mm
                logo_final_height = logo_width_final * aspect_ratio

            p.drawImage(logo, left_margin, y_position - (header_height + logo_final_height)/2 , # Centered vertically
                       width=logo_width_final, height=logo_final_height, mask='auto')
        except Exception as e:
            print(f"Logo error: {e}")

    # Text block to the right of the logo
    text_block_x_start = left_margin + logo_width_final + 5*mm # Start text after logo + padding
    
    # Company Name
    # p.setFillColor(primary_color)
    # p.setFont("Helvetica-Bold", 18) 
    # company_name = "BIOFIX RESEARCH INSTITUTE"
    # p.drawString(text_block_x_start, y_position - 7*mm, company_name) # Y adjusted
    
    # Sub-details
    # p.setFont("Helvetica", 9) 
    # p.drawString(text_block_x_start, y_position - 15*mm, "Water Quality Testing Laboratory") # Y adjusted for spacing
    # p.drawString(text_block_x_start, y_position - 20*mm, "Kerala, India | ISO 17025 Accredited") # Y adjusted for spacing

    # Report Title (below company details, aligned right of text block)
    p.setFillColor(secondary_color)
    p.setFont("Helvetica-Bold", 16) 
    report_title_text = "WATER QUALITY TEST REPORT"
    report_title_width = p.stringWidth(report_title_text, "Helvetica-Bold", 16)
    p.drawString(right_margin - report_title_width, y_position - 28*mm, report_title_text) # Y adjusted for spacing
    
    y_position -= (header_height + 5*mm) # Space after header (uses new header_height)
    
    # Sample Information Section
    p.setFillColor(primary_color)
    p.rect(left_margin, y_position - 8*mm, content_width, 8*mm, stroke=0, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(left_margin + 3*mm, y_position - 6*mm, "SAMPLE INFORMATION")
    
    y_position -= 15*mm # Increased space after title bar
    
    # Information in two columns
    p.setFillColor(text_color)
    
    left_col_label_x = left_margin + 3*mm
    left_col_value_x = left_col_label_x + 32*mm # Start of value for left column
    right_col_label_x = left_margin + content_width/2 + 5*mm
    right_col_value_x = right_col_label_x + 32*mm # Start of value for right column
    
    # Define available width for values (important for paragraph wrapping)
    left_col_value_width = (content_width/2) - (left_col_value_x - left_col_label_x) - 5*mm # Max width for left value
    right_col_value_width = (content_width/2) - (right_col_value_x - right_col_label_x) - 5*mm # Max width for right value

    line_spacing = 7*mm # Increased line spacing to accommodate potential wrapping
    
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    value_style = getSampleStyleSheet()['Normal']
    value_style.fontName = 'Helvetica'
    value_style.fontSize = 10
    value_style.leading = 11 # Line height within paragraph

    # Row 1: Sample ID & Sample Source
    current_y = y_position

    p.setFont("Helvetica-Bold", 10)
    p.drawString(left_col_label_x, current_y, "Sample ID:")
    # Use the new display_id field
    sample_id_to_display = sample.display_id if sample.display_id else str(sample.sample_id)
    sample_id_paragraph = Paragraph(sample_id_to_display, value_style)
    w_id, h_id = sample_id_paragraph.wrapOn(p, left_col_value_width, line_spacing * 2) # Allow wrapping up to 2 lines height
    sample_id_paragraph.drawOn(p, left_col_value_x, current_y - (h_id - value_style.fontSize/2 - 1*mm) ) # Adjust Y for paragraph

    p.setFont("Helvetica-Bold", 10)
    p.drawString(right_col_label_x, current_y, "Sample Source:")
    p.setFont("Helvetica", 10)
    p.drawString(right_col_value_x, current_y, sample.get_sample_source_display())
    
    # Determine max height used by this row (primarily by Sample ID if it wraps)
    row1_height = max(h_id if 'h_id' in locals() else line_spacing, line_spacing)
    y_position -= row1_height

    # Row 2: Customer Name & Received Date
    current_y = y_position 
    p.setFont("Helvetica-Bold", 10)
    p.drawString(left_col_label_x, current_y, "Customer Name:")
    p.setFont("Helvetica", 10)
    p.drawString(left_col_value_x, current_y, sample.customer.name)

    p.setFont("Helvetica-Bold", 10)
    p.drawString(right_col_label_x, current_y, "Received Date:")
    p.setFont("Helvetica", 10)
    p.drawString(right_col_value_x, current_y, sample.date_received_at_lab.strftime('%d %B %Y, %H:%M') if sample.date_received_at_lab else 'N/A')
    y_position -= line_spacing

    # Row 3: Collection Date & Report Date
    current_y = y_position
    p.setFont("Helvetica-Bold", 10)
    p.drawString(left_col_label_x, current_y, "Collection Date:")
    p.setFont("Helvetica", 10)
    p.drawString(left_col_value_x, current_y, sample.collection_datetime.strftime('%d %B %Y, %H:%M'))

    p.setFont("Helvetica-Bold", 10)
    p.drawString(right_col_label_x, current_y, "Report Date:")
    p.setFont("Helvetica", 10)
    p.drawString(right_col_value_x, current_y, timezone.now().strftime('%d %B %Y'))
    y_position -= line_spacing
    
    y_position -= 5*mm # Extra padding after the section
    
    # Test Results Section
    p.setFillColor(primary_color)
    p.rect(left_margin, y_position - 8*mm, content_width, 8*mm, stroke=0, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(left_margin + 3*mm, y_position - 6*mm, "TEST RESULTS")
    
    y_position -= 12*mm
    
    # Table headers
    headers = ["Parameter", "Result", "Unit", "Permissible Limits", "Status"]
    col_widths = [50*mm, 25*mm, 30*mm, 40*mm, 20*mm]
    row_height = 8*mm
    
    # Header row
    p.setFillColor(medium_gray)
    p.rect(left_margin, y_position - row_height, content_width, row_height, stroke=1, fill=1)
    
    p.setFillColor(text_color)
    p.setFont("Helvetica-Bold", 10)
    
    x_pos = left_margin
    for i, header in enumerate(headers):
        p.drawString(x_pos + 2*mm, y_position - 5.5*mm, header) # Adjusted for vertical centering
        x_pos += col_widths[i]
    
    y_position -= row_height
    
    # Data rows
    results_data = sample.results.all().select_related('parameter')
    for i, result in enumerate(results_data):
        # Check if we need a new page
        if y_position < bottom_margin + 50*mm:
            p.showPage()
            y_position = top_margin - 50*mm
            
            # Redraw table header on new page
            p.setFillColor(primary_color)
            p.rect(left_margin, y_position - 8*mm, content_width, 8*mm, stroke=0, fill=1)
            p.setFillColor(colors.white)
            p.setFont("Helvetica-Bold", 12)
            p.drawString(left_margin + 3*mm, y_position - 6*mm, "TEST RESULTS (Continued)")
            y_position -= 12*mm
            
            # Table headers
            p.setFillColor(medium_gray)
            p.rect(left_margin, y_position - row_height, content_width, row_height, stroke=1, fill=1)
            p.setFillColor(text_color)
            p.setFont("Helvetica-Bold", 10)
            x_pos = left_margin
            for j, header in enumerate(headers):
                p.drawString(x_pos + 2*mm, y_position - 6*mm, header)
                x_pos += col_widths[j]
            y_position -= row_height
        
        # Alternating row colors
        row_color = colors.white if i % 2 == 0 else light_gray
        p.setFillColor(row_color)
        p.rect(left_margin, y_position - row_height, content_width, row_height, stroke=1, fill=1) # Changed stroke from 0.5 to 1
        
        # Check if result is within limits
        is_within_limits = result.is_within_limits()
        
        p.setFillColor(text_color)
        p.setFont("Helvetica", 9)
        
        x_pos = left_margin
        
        # Parameter name
        p.drawString(x_pos + 2*mm, y_position - 5.2*mm, result.parameter.name) # Adjusted for vertical centering
        x_pos += col_widths[0]
        
        # Result value (colored based on limits)
        if not is_within_limits:
            p.setFillColor(error_color)
            p.setFont("Helvetica-Bold", 9)
        else:
            p.setFillColor(success_color)
        
        p.drawString(x_pos + 2*mm, y_position - 5.2*mm, str(result.result_value)) # Adjusted for vertical centering
        x_pos += col_widths[1]
        
        # Reset color and font
        p.setFillColor(text_color)
        p.setFont("Helvetica", 9)
        
        # Unit
        p.drawString(x_pos + 2*mm, y_position - 5.2*mm, result.parameter.unit or "") # Adjusted for vertical centering
        x_pos += col_widths[2]
        
        # Limits
        min_limit = result.parameter.min_permissible_limit
        max_limit = result.parameter.max_permissible_limit
        if min_limit is not None and max_limit is not None:
            limit_text = f"{min_limit} - {max_limit}"
        elif min_limit is not None:
            limit_text = f"≥ {min_limit}"
        elif max_limit is not None:
            limit_text = f"≤ {max_limit}"
        else:
            limit_text = "Not specified"
        
        p.drawString(x_pos + 2*mm, y_position - 5.2*mm, limit_text) # Adjusted for vertical centering
        x_pos += col_widths[3]
        
        # Status indicator
        if is_within_limits:
            p.setFillColor(success_color)
            status_text = "✓ PASS"
        else:
            p.setFillColor(error_color)
            status_text = "✗ FAIL"
        
        p.setFont("Helvetica-Bold", 8)
        p.drawString(x_pos + 2*mm, y_position - 5.2*mm, status_text) # Adjusted for vertical centering
        
        y_position -= row_height
    
    # Consultant review section if available and has meaningful content
    if hasattr(sample, 'review') and sample.review and sample.review.status == 'APPROVED':
        review = sample.review
        
        meaningful_comments = review.comments and review.comments.strip() and review.comments.strip().lower() not in ['f', 'd', 'n/a', '-', '.', 'nil']
        meaningful_recommendations = review.recommendations and review.recommendations.strip() and review.recommendations.strip().lower() not in ['f', 'd', 'n/a', '-', '.', 'nil']

        if meaningful_comments or meaningful_recommendations:
            # Proceed to show section
            y_position -= 10*mm
            
            # Section header
            p.setFillColor(primary_color)
            p.rect(left_margin, y_position - 8*mm, content_width, 8*mm, stroke=0, fill=1)
            p.setFillColor(colors.white)
            p.setFont("Helvetica-Bold", 12)
            p.drawString(left_margin + 3*mm, y_position - 6*mm, "CONSULTANT'S REMARKS")
            
            y_position -= 12*mm
            
            p.setFillColor(text_color)
            p.setFont("Helvetica", 10)
            
            style = None # Initialize style variable
            if meaningful_comments:
                p.setFont("Helvetica-Bold", 10)
                p.drawString(left_margin + 3*mm, y_position, "Comments:")
                y_position -= 5*mm
                p.setFont("Helvetica", 10)
                
                from reportlab.platypus import Paragraph # Import here to avoid error if not used
                from reportlab.lib.styles import getSampleStyleSheet
                if not style: # Ensure style is initialized only once if needed for both
                    style = getSampleStyleSheet()['Normal']
                    style.fontName = 'Helvetica'
                    style.fontSize = 10
                    style.leading = 12 
                
                comment_paragraph = Paragraph(review.comments.strip(), style)
                comment_width, comment_height = comment_paragraph.wrapOn(p, content_width - 6*mm, 50*mm) 
                comment_paragraph.drawOn(p, left_margin + 3*mm, y_position - comment_height)
                y_position -= (comment_height + 3*mm) 
            
            if meaningful_recommendations:
                p.setFont("Helvetica-Bold", 10)
                p.drawString(left_margin + 3*mm, y_position, "Recommendations:")
                y_position -= 5*mm
                p.setFont("Helvetica", 10)

                if not style: # Ensure style is initialized if not done by comments
                    from reportlab.platypus import Paragraph
                    from reportlab.lib.styles import getSampleStyleSheet
                    style = getSampleStyleSheet()['Normal']
                    style.fontName = 'Helvetica'
                    style.fontSize = 10
                    style.leading = 12

                recommendation_paragraph = Paragraph(review.recommendations.strip(), style)
                rec_width, rec_height = recommendation_paragraph.wrapOn(p, content_width - 6*mm, 50*mm)
                recommendation_paragraph.drawOn(p, left_margin + 3*mm, y_position - rec_height)
                y_position -= (rec_height + 3*mm)
        # If no meaningful content, the 'else' for 'if meaningful_comments or meaningful_recommendations:' is implicitly to do nothing further for this section.
    
    # Footer with signature section
    y_position -= 15*mm
    
    # Signature line
    p.setFillColor(text_color)
    p.setFont("Helvetica", 10)
    p.drawRightString(right_margin, y_position, "Authorized Signatory")
    p.line(right_margin - 50*mm, y_position - 2*mm, right_margin, y_position - 2*mm)
    
    # Final footer
    p.setFont("Helvetica-Oblique", 8)
    p.setStrokeColor(medium_gray)
    p.line(left_margin, bottom_margin + 5*mm, right_margin, bottom_margin + 5*mm)
    p.drawString(left_margin, bottom_margin, f"Report Generated: {timezone.now().strftime('%d %B %Y, %H:%M:%S')}")
    p.drawRightString(right_margin, bottom_margin, f"Page {p.getPageNumber()}")
    
    p.showPage()
    p.save()

    buffer.seek(0)
    response = FileResponse(buffer, as_attachment=True, filename=f'WaterQualityReport_{sample.sample_id}.pdf')
    
    if sample.current_status == 'REPORT_APPROVED':
        try:
            sample.update_status('REPORT_SENT', request.user)
            messages.info(request, f"Report for sample {sample.sample_id} downloaded and status updated to 'Report Sent'.")
        except Exception as e:
            messages.warning(request, f"Report downloaded, but failed to update sample status: {str(e)}")
            # Log this error for admin attention

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
        
        except Exception as e:
            # Catch any other unexpected errors
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            # Consider logging this unexpected error for developers
            # import logging
            # logger = logging.getLogger(__name__)
            # logger.error(f"Unexpected error in sample_status_update for sample {sample.sample_id}: {str(e)}")

        return redirect('core:sample_detail', pk=sample.sample_id)

    # For GET requests: redirect to detail page. 
    # Status changes should only occur via POST.
    # Optionally, add a message or return HttpResponseNotAllowed for GET.
    return redirect('core:sample_detail', pk=sample.sample_id)

@login_required
@admin_required # Or specific role required for managing test parameters
def setup_test_parameters(request):
    # Placeholder for test parameter setup view
    # This view would typically allow admins to create, update, or list TestParameter objects.
    # It might involve a ModelForm for TestParameter.
    
    # Example: List existing parameters and provide a form to add new ones.
    parameters = TestParameter.objects.all().order_by('name')
    form = TestParameterForm() # Assuming TestParameterForm is defined and imported

    if request.method == 'POST':
        form = TestParameterForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    parameter = form.save()
                    AuditTrail.log_change(user=request.user, action='CREATE', instance=parameter, request=request)
                    messages.success(request, f"Test parameter '{parameter.name}' created successfully.")
                    return redirect('core:setup_test_parameters') # Redirect to the same page to show the new list
            except Exception as e:
                messages.error(request, f"Error creating test parameter: {str(e)}")
        else:
            messages.error(request, "Error in form submission. Please check the details.")

    context = {
        'parameters': parameters,
        'form': form,
        'page_title': 'Setup Test Parameters' # Example title for the template
    }
    return render(request, 'core/setup_test_parameters.html', context)

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
                AuditTrail.log_change(user=self.request.user, action='UPDATE', instance=parameter, old_values=old_values, new_values=form.cleaned_data, request=self.request)
                messages.success(self.request, f"Test parameter '{parameter.name}' updated successfully.")
        except Exception as e:
            messages.error(self.request, f"Error updating test parameter: {str(e)}")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit Test Parameter: {self.object.name}'
        context['is_edit'] = True # For template to adapt if needed
        return context
