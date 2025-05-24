from django.urls import path
from .views import (
    CustomerListView, 
    SampleListView, 
    CustomerDetailView, 
    SampleDetailView,
    CustomerCreateView,
    CustomerUpdateView,
    SampleCreateView,
    SampleUpdateView,
    test_result_entry,
    consultant_review,
    AdminDashboardView,
    LabDashboardView,
    FrontDeskDashboardView,
    ConsultantDashboardView,
    CustomPasswordChangeView,
    password_change_done,
    AuditTrailView,
    health_check,
    debug_admin,
    create_admin_web,
    debug_view,
    form_test,
    fix_admin_role_web,
    sample_status_update,
    setup_test_parameters
)

from .auth_views import (
    AdminLoginView,
    UserLoginView, 
    SecureLogoutView,
    DashboardView,
    login_selector
)

app_name = 'core'

urlpatterns = [
    # Health check for deployment monitoring
    path('health/', health_check, name='health_check'),
    path('debug-admin/', debug_admin, name='debug_admin'),
    path('create-admin/', create_admin_web, name='create_admin_web'),
    path('debug/', debug_view, name='debug_view'),
    path('form-test/', form_test, name='form_test'),
    path('fix-admin-role/', fix_admin_role_web, name='fix_admin_role_web'),
    
    # Professional Authentication URLs
    path('', login_selector, name='home'),
    path('login/', login_selector, name='login_selector'),
    path('admin-login/', AdminLoginView.as_view(), name='admin_login'),
    path('user-login/', UserLoginView.as_view(), name='user_login'),
    path('logout/', SecureLogoutView.as_view(), name='logout'),
    
    # Dashboard URLs  
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/admin/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/lab/', LabDashboardView.as_view(), name='lab_dashboard'),
    path('dashboard/frontdesk/', FrontDeskDashboardView.as_view(), name='frontdesk_dashboard'),
    path('dashboard/consultant/', ConsultantDashboardView.as_view(), name='consultant_dashboard'),
    
    # Password Management
    path('password-change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('password-change/done/', password_change_done, name='password_change_done'),
    
    # Customer URLs
    path('customers/', CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', CustomerCreateView.as_view(), name='customer_add'),
    path('customers/<uuid:pk>/', CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<uuid:pk>/edit/', CustomerUpdateView.as_view(), name='customer_edit'),
    
    # Sample URLs
    path('samples/', SampleListView.as_view(), name='sample_list'),
    path('samples/add/', SampleCreateView.as_view(), name='sample_add'),
    path('samples/<uuid:pk>/', SampleDetailView.as_view(), name='sample_detail'),
    path('samples/<uuid:pk>/edit/', SampleUpdateView.as_view(), name='sample_edit'),
    path('samples/<uuid:sample_id>/test-results/', test_result_entry, name='test_result_entry'),
    path('samples/<uuid:sample_id>/review/', consultant_review, name='consultant_review'),
    path('samples/<uuid:sample_id>/status-update/', sample_status_update, name='sample_status_update'),
    
    # Test Parameters Setup
    path('setup-test-parameters/', setup_test_parameters, name='setup_test_parameters'),
    
    # Audit Trail
    path('audit/', AuditTrailView.as_view(), name='audit_trail'),
]
