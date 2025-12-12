"""Facade module for core view definitions.

The original `core/views.py` grew large; implementations are now split into
feature-focused modules. This file re-exports the public views so existing
imports (urls, tests, templates) continue to work unchanged.
"""

from .views_common import (
    _SENSITIVE_ROLES,
    _choose_signer_with_signature,
    _format_error_message,
    _user_can_view_sensitive_records,
    health_check,
    debug_admin,
    create_admin_web,
    debug_view,
    form_test,
    fix_admin_role_web,
    simple_home,
    simple_dashboard,
    CustomLoginView,
    CustomPasswordChangeView,
    password_change_done,
)
from .views_dashboards import (
    AdminDashboardView,
    LabDashboardView,
    FrontDeskDashboardView,
    ConsultantDashboardView,
)
from .views_audit import AuditTrailView
from .views_users import (
    AdminUserListView,
    AdminUserCreateView,
    AdminUserUpdateView,
    LabProfileUpdateView,
    toggle_user_active,
)
from .views_results import (
    TestResultListView,
    TestResultDetailView,
    test_result_entry,
)
from .views_customers import (
    CustomerListView,
    CustomerDetailView,
    CustomerCreateView,
    CustomerUpdateView,
)
from .views_samples import (
    SampleListView,
    SampleDetailView,
    SampleCreateView,
    SampleUpdateView,
    SampleReportMetadataUpdateView,
    consultant_review,
    sample_status_update,
)
from .views_reports import download_sample_report_view
from .views_parameters import (
    setup_test_parameters,
    reorder_test_parameters,
    TestParameterUpdateView,
    setup_test_categories,
    TestCategoryUpdateView,
    delete_test_category,
    delete_test_parameter,
    kerala_locations_json,
)

__all__ = [
    '_SENSITIVE_ROLES',
    '_choose_signer_with_signature',
    '_format_error_message',
    '_user_can_view_sensitive_records',
    'health_check',
    'debug_admin',
    'create_admin_web',
    'debug_view',
    'form_test',
    'fix_admin_role_web',
    'simple_home',
    'simple_dashboard',
    'CustomLoginView',
    'CustomPasswordChangeView',
    'password_change_done',
    'AdminDashboardView',
    'LabDashboardView',
    'FrontDeskDashboardView',
    'ConsultantDashboardView',
    'AuditTrailView',
    'AdminUserListView',
    'AdminUserCreateView',
    'AdminUserUpdateView',
    'LabProfileUpdateView',
    'toggle_user_active',
    'TestResultListView',
    'TestResultDetailView',
    'test_result_entry',
    'CustomerListView',
    'CustomerDetailView',
    'CustomerCreateView',
    'CustomerUpdateView',
    'SampleListView',
    'SampleDetailView',
    'SampleCreateView',
    'SampleUpdateView',
    'SampleReportMetadataUpdateView',
    'consultant_review',
    'sample_status_update',
    'download_sample_report_view',
    'setup_test_parameters',
    'reorder_test_parameters',
    'TestParameterUpdateView',
    'setup_test_categories',
    'TestCategoryUpdateView',
    'delete_test_category',
    'delete_test_parameter',
    'kerala_locations_json',
]

