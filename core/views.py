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
                    if not sample.has_all_test_results(): # Should not happen if it was REVIEW_PENDING, but check anyway
                        missing_tests_qs = sample.get_missing_test_results()
                        missing_names = [test.name for test in missing_tests_qs]
                        messages.warning(request, f'Results updated, but now missing: {", ".join(missing_names)}. Sample remains in Review Pending.')
                    else:
                        messages.info(request, "Results updated by Admin. Sample remains in 'Review Pending' status for re-evaluation by consultant.")
                elif sample.has_all_test_results():
                    sample.update_status('RESULTS_ENTERED', request.user) # This will fail if current_status is REVIEW_PENDING due to can_transition_to
                    messages.success(request, 'All test results completed! Sample ready for review.')
                else:
                    missing_tests_qs = sample.get_missing_test_results()
                    missing_names = [test.name for test in missing_tests_qs]
                    messages.info(request, f'Results saved. Still missing: {", ".join(missing_names)}')
                
                if results_entered_count > 0:
                    messages.success(request, f'{results_entered_count} new test results saved successfully!')
                if results_updated_count > 0:
                    messages.success(request, f'{results_updated_count} test results updated successfully!')
            
        except ValidationError as ve: # Catch specific validation errors from forms or manual raises
             messages.error(request, f'Validation Error: {ve.messages[0] if ve.messages else str(ve)}')
             # To show errors on the form, we'd need to fall through to the GET rendering logic
             # with the invalid forms. This is a simplification for now.
        except Exception as e:
            messages.error(request, f'Error saving results: {str(e)}')
        
        # Always redirect to sample detail after POST, success or error (unless re-rendering form with errors)
        return redirect('core:sample_detail', pk=sample.sample_id)

    # GET request handling
    existing_results_dict = {r.parameter.parameter_id: r for r in sample.results.all()} # Renamed
    form_data = []
    for test_param_model in sample.tests_requested.all(): # Renamed
        initial_data = {}
        existing_result = existing_results_dict.get(test_param_model.parameter_id)
        if existing_result:
            initial_data['result_value'] = existing_result.result_value
            initial_data['observation'] = existing_result.observation
        
        # Use 'validate' class for Materialize CSS compatibility
        form_instance = TestResultEntryForm(
            prefix=f'param_{test_param_model.parameter_id}', 
            initial=initial_data
        )
        # Update widget attributes for Materialize if not done in form class globally
        form_instance.fields['result_value'].widget.attrs.update({'class': 'validate'})
        form_instance.fields['observation'].widget.attrs.update({'class': 'materialize-textarea validate'})


        form_data.append({
            'parameter': test_param_model,
            'form': form_instance,
            'existing_result': existing_result 
        })
    
    missing_tests_qs = sample.get_missing_test_results() # Renamed

    
    can_edit_results = sample.current_status in ['TESTING_IN_PROGRESS', 'RESULTS_ENTERED']
    if sample.current_status == 'REVIEW_PENDING' and request.user.is_admin:
        can_edit_results = True

    return render(request, 'core/test_result_entry.html', {
        'sample': sample,
        'form_data': form_data, 
        'existing_results': existing_results_dict, 
        'missing_tests': missing_tests_qs, 
        'can_edit': can_edit_results, # Updated can_edit logic
    })

@consultant_required
def consultant_review(request, sample_id):
    sample = get_object_or_404(Sample, sample_id=sample_id)
    
    # Check if sample is ready for review
    if not sample.can_be_reviewed():
        messages.error(request, f'Sample is not ready for review. Current status: {sample.get_current_status_display()}. All test results must be completed first.')
        return redirect('core:sample_detail', pk=sample.sample_id)
    
    try:
        review = ConsultantReview.objects.get(sample=sample)
        created = False
    except ConsultantReview.DoesNotExist:
        # Create new review and update sample status
        try:
            sample.update_status('REVIEW_PENDING', request.user)
            review = ConsultantReview.objects.create(
                sample=sample,
                reviewer=request.user
            )
            created = True
        except Exception as e:
            messages.error(request, f'Error creating review: {str(e)}')
            return redirect('core:sample_detail', pk=sample.sample_id)
    
    if request.method == 'POST':
        try:
            old_status = review.status
            review.comments = request.POST.get('comments', '')
            review.recommendations = request.POST.get('recommendations', '')
            new_status = request.POST.get('status', 'PENDING')
            
            # Validate status change
            if new_status != old_status:
                if new_status == 'APPROVED' and not review.comments.strip():
                    messages.error(request, 'Comments are required when approving a sample.')
                    return render(request, 'core/consultant_review.html', {
                        'sample': sample,
                        'review': review,
                        'test_results': sample.results.all().select_related('parameter'),
                        'out_of_limit_results': [r for r in sample.results.all() if not r.is_within_limits()],
                    })
                
                if new_status == 'REJECTED' and not review.recommendations.strip():
                    messages.error(request, 'Recommendations are required when rejecting a sample.')
                    return render(request, 'core/consultant_review.html', {
                        'sample': sample,
                        'review': review,
                        'test_results': sample.results.all().select_related('parameter'),
                        'out_of_limit_results': [r for r in sample.results.all() if not r.is_within_limits()],
                    })
            
            review.status = new_status
            review.full_clean()  # Validate the review
            review.save()  # This will trigger the sample status update in the model
            
            # Log the review change
            AuditTrail.log_change(
                user=request.user,
                action='UPDATE',
                instance=review,
                old_values={'status': old_status},
                new_values={'status': new_status},
                request=request
            )
            
            if new_status == 'APPROVED':
                messages.success(request, 'Sample approved! Report is ready for delivery.')
            elif new_status == 'REJECTED':
                messages.warning(request, 'Sample rejected and sent back for retesting.')
            else:
                messages.success(request, 'Review saved successfully!')
                
        except Exception as e:
            messages.error(request, f'Error saving review: {str(e)}')
        
        return redirect('core:sample_detail', pk=sample.sample_id)
    
    # Get test results with limit status for review
    test_results = sample.results.all().select_related('parameter')
    out_of_limit_results = [r for r in test_results if not r.is_within_limits()]
    
    return render(request, 'core/consultant_review.html', {
        'sample': sample,
        'review': review,
        'test_results': test_results,
        'out_of_limit_results': out_of_limit_results,
        'is_new_review': created,
    })

class AuditTrailView(AdminRequiredMixin, ListView):
    model = AuditTrail
    template_name = 'core/audit_trail.html'
    context_object_name = 'audit_logs'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = AuditTrail.objects.select_related('user').all()
        
        # Filter by model if specified
        model_name = self.request.GET.get('model')
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        
        # Filter by object if specified
        object_id = self.request.GET.get('object_id')
        if object_id:
            queryset = queryset.filter(object_id=object_id)
        
        # Filter by user if specified
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by action if specified
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_choices'] = ['Customer', 'Sample', 'TestResult', 'ConsultantReview']
        context['action_choices'] = [choice[0] for choice in AuditTrail.ACTION_CHOICES]
        context['users'] = CustomUser.objects.all()
        context['filters'] = {
            'model': self.request.GET.get('model', ''),
            'object_id': self.request.GET.get('object_id', ''),
            'user': self.request.GET.get('user', ''),
            'action': self.request.GET.get('action', ''),
        }
        return context

def sample_status_update(request, sample_id):
    """Allow users to update sample status based on their role and workflow"""
    sample = get_object_or_404(Sample, sample_id=sample_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        
        try:
            # Check user permissions for specific status changes
            if new_status == 'SENT_TO_LAB':
                if not (request.user.is_frontdesk() or request.user.is_admin()):
                    messages.error(request, 'Only front desk staff can send samples to lab.')
                    return redirect('core:sample_detail', pk=sample.sample_id)
                    
            elif new_status == 'CANCELLED':
                if not request.user.is_admin():
                    messages.error(request, 'Only administrators can cancel samples.')
                    return redirect('core:sample_detail', pk=sample.sample_id)
            
            # Update the status using the business logic
            sample.update_status(new_status, request.user)
            
            # Success messages based on status
            if new_status == 'SENT_TO_LAB':
                messages.success(request, f'Sample {sample.sample_id} sent to lab successfully!')
            elif new_status == 'CANCELLED':
                messages.warning(request, f'Sample {sample.sample_id} has been cancelled.')
            else:
                messages.success(request, f'Sample status updated to {sample.get_current_status_display()}.')
                
        except Exception as e:
            messages.error(request, f'Error updating status: {str(e)}')
    
    return redirect('core:sample_detail', pk=sample.sample_id)

@admin_required  
def setup_test_parameters(request):
    """Web interface to set up test parameters"""
    from django.core.management import call_command
    
    if request.method == 'POST':
        try:
            # Run the management command
            call_command('create_test_parameters')
            messages.success(request, 'Test parameters created successfully! You can now create samples with test requests.')
        except Exception as e:
            messages.error(request, f'Error creating test parameters: {str(e)}')
        
        return redirect('core:sample_add')
    
    # Show current test parameters
    from .models import TestParameter
    existing_params = TestParameter.objects.all()
    
    return render(request, 'core/setup_test_parameters.html', {
        'existing_params': existing_params,
    })

class TestResultListView(LoginRequiredMixin, ListView):
    model = Sample # Changed model to Sample
    template_name = 'core/test_result_list.html' 
    context_object_name = 'samples_with_results' # Changed context object name
    paginate_by = 15 # Adjusted pagination if needed

    def get_queryset(self):
        # Fetch samples that have at least one test result
        # Order by the most recent test result date (descending), then by sample collection date
        # This requires annotating the latest test date onto the sample queryset.
        from django.db.models import Max
        queryset = Sample.objects.annotate(
            latest_test_date=Max('results__test_date')
        ).filter(results__isnull=False).distinct().select_related('customer').order_by('-latest_test_date', '-collection_datetime')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Samples with Test Results" # Updated page title
        # Add any other context needed for the template
        return context

class TestParameterUpdateView(AdminRequiredMixin, UpdateView):
    model = TestParameter
    form_class = TestParameterForm
    template_name = 'core/test_parameter_form.html' # Will be created
    success_url = reverse_lazy('core:setup_test_parameters')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        context['page_title'] = f"Edit Test Parameter: {self.object.name}"
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Test Parameter "{form.instance.name}" updated successfully.')
        return super().form_valid(form)

@login_required
def download_sample_report_view(request, pk):
    sample = get_object_or_404(Sample, pk=pk)

    if sample.current_status not in ['REPORT_APPROVED', 'REPORT_SENT']:
        messages.error(request, "Report is not yet approved or available for download.")
        return redirect('core:sample_detail', pk=sample.pk)

    # Placeholder for PDF generation logic
    # For a real implementation, you'd use a library like ReportLab, WeasyPrint, or xhtml2pdf
    # to generate a PDF file and return it in the HttpResponse.
    
    # Example: Basic HTML content for the report (to be rendered to PDF later)
    report_html_content = f"""
    <html>
        <head><title>Test Report - {sample.sample_id}</title></head>
        <body>
            <h1>Test Report</h1>
            <p><strong>Sample ID:</strong> {sample.sample_id}</p>
            <p><strong>Customer:</strong> {sample.customer.name}</p>
            <p><strong>Collection Date:</strong> {sample.collection_datetime}</p>
            <p><strong>Sample Source:</strong> {sample.get_sample_source_display()}</p>
            <hr>
            <h2>Results:</h2>
            <ul>
    """
    for result in sample.results.all():
        report_html_content += f"<li>{result.parameter.name}: {result.result_value} {result.parameter.unit}</li>"
    
    report_html_content += """
            </ul>
            <hr>
            <p><em>Report generated on: {timezone.now()}</em></p>
            <p style='color: red; font-weight: bold;'>NOTE: This is a placeholder. PDF generation is pending implementation.</p>
        </body>
    </html>
    """
    # In a real scenario, you would render this HTML to a PDF
    # response = HttpResponse(content_type='application/pdf')
    # response['Content-Disposition'] = f'attachment; filename="report_{sample.sample_id}.pdf"'
    # ... PDF generation logic using the html_content ...

    # Create a file-like buffer to receive PDF data.
    buffer = BytesIO()

    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer, pagesize=letter)

    # Set up document properties
    p.setTitle(f"Test Report - {sample.sample_id}")

    # --- Draw things on the PDF ---
    # Start drawing from the top of the page
    y_position = 10 * inch  # Start 1 inch from the top

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(1 * inch, y_position, "Water Quality Test Report")
    y_position -= 0.5 * inch

    # Sample Information
    p.setFont("Helvetica", 12)
    p.drawString(1 * inch, y_position, f"Sample ID: {sample.sample_id}")
    y_position -= 0.3 * inch
    p.drawString(1 * inch, y_position, f"Customer: {sample.customer.name}")
    y_position -= 0.3 * inch
    p.drawString(1 * inch, y_position, f"Collection Date: {sample.collection_datetime.strftime('%Y-%m-%d %H:%M')}")
    y_position -= 0.3 * inch
    p.drawString(1 * inch, y_position, f"Sample Source: {sample.get_sample_source_display()}")
    y_position -= 0.5 * inch

    # Horizontal line
    p.line(1 * inch, y_position, 7.5 * inch, y_position)
    y_position -= 0.3 * inch

    # Test Results Header
    p.setFont("Helvetica-Bold", 14)
    p.drawString(1 * inch, y_position, "Test Results:")
    y_position -= 0.4 * inch

    # Table Headers
    p.setFont("Helvetica-Bold", 10)
    col_widths = [2.5 * inch, 1.5 * inch, 1.5 * inch, 1 * inch]
    current_x = 1 * inch
    headers = ["Parameter", "Result", "Unit", "Limits"]
    for i, header in enumerate(headers):
        p.drawString(current_x, y_position, header)
        current_x += col_widths[i]
    y_position -= 0.15 * inch
    p.line(1 * inch, y_position, 7.5 * inch, y_position) # Line under headers
    y_position -= 0.25 * inch
    
    p.setFont("Helvetica", 10)
    for result in sample.results.all().select_related('parameter'):
        if y_position < 1 * inch: # Check for page break
            p.showPage()
            p.setFont("Helvetica", 10)
            y_position = 10 * inch # Reset y_position for new page (adjust as needed)
             # Redraw headers on new page if needed (optional)

        current_x = 1 * inch
        
        # Parameter Name
        p.drawString(current_x, y_position, result.parameter.name)
        current_x += col_widths[0]
        
        # Result Value
        p.drawString(current_x, y_position, str(result.result_value))
        current_x += col_widths[1]
        
        # Unit
        p.drawString(current_x, y_position, result.parameter.unit)
        current_x += col_widths[2]
        
        # Limits
        min_limit = result.parameter.min_permissible_limit
        max_limit = result.parameter.max_permissible_limit
        limit_text = f"{min_limit if min_limit is not None else '-'} - {max_limit if max_limit is not None else '-'}"
        p.drawString(current_x, y_position, limit_text)
        
        y_position -= 0.25 * inch

    # Footer
    y_position = 0.75 * inch # Position for footer
    p.line(1 * inch, y_position + 0.1 * inch, 7.5 * inch, y_position + 0.1 * inch)
    p.setFont("Helvetica-Oblique", 9)
    p.drawString(1 * inch, y_position - 0.1 * inch, f"Report generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawRightString(7.5 * inch, y_position - 0.1 * inch, f"Page {p.getPageNumber()}")


    # --- Close the PDF object cleanly ---
    p.showPage()
    p.save()

    # FileResponse sets the Content-Disposition header so that browsers
    # present the option to save the file.
    buffer.seek(0)
    response = FileResponse(buffer, as_attachment=True, filename=f'report_{sample.sample_id}.pdf')
    
    # Update sample status to REPORT_SENT if it was REPORT_APPROVED
    if sample.current_status == 'REPORT_APPROVED':
        try:
            sample.update_status('REPORT_SENT', request.user)
            messages.info(request, f"Report for sample {sample.sample_id} downloaded and status updated to 'Report Sent'.")
        except Exception as e:
            messages.warning(request, f"Report downloaded, but failed to update sample status: {str(e)}")
            # Log this error for admin attention

    return response
