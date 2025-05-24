from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import Customer, Sample, TestParameter, TestResult, ConsultantReview, CustomUser, AuditTrail
from .forms import CustomerForm, SampleForm, CustomPasswordChangeForm
from .decorators import admin_required, lab_required, frontdesk_required, consultant_required
from .mixins import AdminRequiredMixin, LabRequiredMixin, FrontDeskRequiredMixin, ConsultantRequiredMixin, RoleRequiredMixin, AuditMixin

# Health check endpoint for deployment monitoring
from django.http import HttpResponse

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
            role='ADMIN',
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
        
        # Admin gets comprehensive system overview
        context.update({
            'total_customers': Customer.objects.count(),
            'total_samples': Sample.objects.count(),
            'total_users': CustomUser.objects.count(),
            'pending_samples': Sample.objects.filter(current_status='RECEIVED_FRONT_DESK').count(),
            'testing_samples': Sample.objects.filter(current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']).count(),
            'review_pending': Sample.objects.filter(current_status='REVIEW_PENDING').count(),
            'completed_samples': Sample.objects.filter(current_status='REPORT_APPROVED').count(),
            
            # Recent activity
            'recent_customers': Customer.objects.order_by('-customer_id')[:5],
            'recent_samples': Sample.objects.select_related('customer').order_by('-collection_datetime')[:10],
            'recent_users': CustomUser.objects.order_by('-date_joined')[:5],
            
            # User statistics by role
            'user_stats': CustomUser.objects.values('role').annotate(count=Count('pk')),
            
            # Daily statistics
            'today_samples': Sample.objects.filter(collection_datetime__date=timezone.now().date()).count(),
            'week_samples': Sample.objects.filter(collection_datetime__gte=timezone.now() - timedelta(days=7)).count(),
        })
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
            
            # Review statistics
            'review_stats': ConsultantReview.objects.filter(reviewer=self.request.user).values('status').annotate(count=Count('review_id')),
        })
        return context

class CustomerListView(ListView):
    model = Customer
    template_name = 'core/customer_list.html'
    context_object_name = 'customers'
    
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

class SampleListView(ListView):
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
        messages.success(self.request, f'Sample has been updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context

@lab_required
def test_result_entry(request, sample_id):
    sample = get_object_or_404(Sample, sample_id=sample_id)
    
    if request.method == 'POST':
        for test_param in sample.tests_requested.all():
            result_value = request.POST.get(f'result_{test_param.parameter_id}')
            observation = request.POST.get(f'observation_{test_param.parameter_id}')
            
            if result_value:
                # Get technician (use None if anonymous user)
                technician = request.user if request.user.is_authenticated else None
                
                test_result, created = TestResult.objects.get_or_create(
                    sample=sample,
                    parameter=test_param,
                    defaults={
                        'result_value': result_value,
                        'observation': observation,
                        'technician': technician
                    }
                )
                if not created:
                    test_result.result_value = result_value
                    test_result.observation = observation
                    test_result.save()
        
        sample.current_status = 'RESULTS_ENTERED'
        sample.save()
        messages.success(request, 'Test results saved successfully!')
        return redirect('core:sample_detail', pk=sample.sample_id)
    
    existing_results = {r.parameter.parameter_id: r for r in sample.results.all()}
    return render(request, 'core/test_result_entry.html', {
        'sample': sample,
        'existing_results': existing_results,
    })

@consultant_required
def consultant_review(request, sample_id):
    sample = get_object_or_404(Sample, sample_id=sample_id)
    
    # Get reviewer (use None if anonymous user)
    reviewer = request.user if request.user.is_authenticated else None
    
    review, created = ConsultantReview.objects.get_or_create(
        sample=sample,
        defaults={'reviewer': reviewer}
    )
    
    if request.method == 'POST':
        review.comments = request.POST.get('comments', '')
        review.recommendations = request.POST.get('recommendations', '')
        review.status = request.POST.get('status', 'PENDING')
        review.save()
        
        if review.status == 'APPROVED':
            sample.current_status = 'REPORT_APPROVED'
            sample.save()
        
        messages.success(request, 'Review saved successfully!')
        return redirect('core:sample_detail', pk=sample.sample_id)
    
    return render(request, 'core/consultant_review.html', {
        'sample': sample,
        'review': review,
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
