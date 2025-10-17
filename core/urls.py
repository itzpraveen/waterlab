from django.urls import path
from django.views.generic import RedirectView
from django.conf import settings

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
    setup_test_parameters,
    reorder_test_parameters,
    setup_test_categories,
    TestResultListView,
    TestResultDetailView,
    download_sample_report_view,
    TestParameterUpdateView,
    delete_test_parameter,
    TestCategoryUpdateView,
    delete_test_category,
    AdminUserListView,
    AdminUserCreateView,
    AdminUserUpdateView,
    toggle_user_active,
    kerala_locations_json,
)

from .auth_views import (
    UserLoginView, 
    SecureLogoutView,
    DashboardView
)

app_name = 'core'

urlpatterns = [
    # Health check for deployment monitoring
    path('health/', health_check, name='health_check'),
    
    # Authentication URLs
    path('', UserLoginView.as_view(), name='home'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('admin-login/', RedirectView.as_view(pattern_name='core:login', permanent=False), name='admin_login'),
    path('user-login/', RedirectView.as_view(pattern_name='core:login', permanent=False), name='user_login'),
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
    path('address/kerala.json', kerala_locations_json, name='kerala_locations_json'),
    path('setup-test-parameters/reorder/', reorder_test_parameters, name='test_parameter_reorder'),
    path('setup-test-categories/', setup_test_categories, name='setup_test_categories'),
    
    # Audit Trail
    path('audit/', AuditTrailView.as_view(), name='audit_trail'),

    # Test Results List (New)
    path('results/', TestResultListView.as_view(), name='test_result_list'),
    path('results/<uuid:pk>/', TestResultDetailView.as_view(), name='test_result_detail'),
    path('samples/<uuid:pk>/download-report/', download_sample_report_view, name='download_sample_report'),
    
    # Test Parameter Management (Admin)
    path('setup-test-parameters/<uuid:pk>/edit/', TestParameterUpdateView.as_view(), name='test_parameter_edit'),
    path('setup-test-parameters/<uuid:pk>/delete/', delete_test_parameter, name='test_parameter_delete'),
    # Category Management (Admin)
    path('setup-test-categories/<int:pk>/edit/', TestCategoryUpdateView.as_view(), name='test_category_edit'),
    path('setup-test-categories/<int:pk>/delete/', delete_test_category, name='test_category_delete'),

    # User management (Admin)
    path('users/', AdminUserListView.as_view(), name='user_list'),
    path('users/add/', AdminUserCreateView.as_view(), name='user_add'),
    path('users/<int:pk>/edit/', AdminUserUpdateView.as_view(), name='user_edit'),
    path('users/<int:pk>/toggle/', toggle_user_active, name='user_toggle_active'),
]

if settings.DEBUG:
    urlpatterns += [
        path('debug-admin/', debug_admin, name='debug_admin'),
        path('create-admin/', create_admin_web, name='create_admin_web'),
        path('debug/', debug_view, name='debug_view'),
        path('form-test/', form_test, name='form_test'),
        path('fix-admin-role/', fix_admin_role_web, name='fix_admin_role_web'),
    ]
