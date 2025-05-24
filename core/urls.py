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
    dashboard_redirect,
    AdminDashboardView,
    LabDashboardView,
    FrontDeskDashboardView,
    ConsultantDashboardView,
    CustomLoginView,
    CustomPasswordChangeView,
    password_change_done,
    AuditTrailView,
    health_check
)

app_name = 'core'

urlpatterns = [
    # Health check for deployment monitoring
    path('health/', health_check, name='health_check'),
    
    # Dashboard URLs
    path('', dashboard_redirect, name='home'),
    path('dashboard/', dashboard_redirect, name='dashboard'),
    path('dashboard/admin/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/lab/', LabDashboardView.as_view(), name='lab_dashboard'),
    path('dashboard/frontdesk/', FrontDeskDashboardView.as_view(), name='frontdesk_dashboard'),
    path('dashboard/consultant/', ConsultantDashboardView.as_view(), name='consultant_dashboard'),
    
    # Authentication URLs
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/password-change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('accounts/password-change/done/', password_change_done, name='password_change_done'),
    
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
    
    # Audit Trail
    path('audit/', AuditTrailView.as_view(), name='audit_trail'),
]
