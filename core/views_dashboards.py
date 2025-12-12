import logging
from datetime import timedelta

from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.views.generic import TemplateView

from .mixins import (
    AdminRequiredMixin,
    LabRequiredMixin,
    FrontDeskRequiredMixin,
    ConsultantRequiredMixin,
)
from .models import Customer, Sample, TestParameter, TestResult, ConsultantReview, CustomUser
from .views_common import _format_error_message

logger = logging.getLogger(__name__)


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = 'core/dashboards/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'total_customers': 0,
            'total_samples': 0,
            'total_users': 0,
            'pending_samples_count': 0,
            'testing_samples_count': 0,
            'review_pending_count': 0,
            'completed_samples_count': 0,
            'recent_customers': [],
            'recent_samples': [],
            'recent_users': [],
            'user_stats': [],
            'today_samples_count': 0,
            'week_samples_count': 0,
            'samples_in_lab': [],
            'samples_awaiting_review': [],
            'data_load_error': False,
        })

        try:
            context['total_customers'] = Customer.objects.count()
            context['total_samples'] = Sample.objects.count()
            context['total_users'] = CustomUser.objects.count()
            context['pending_samples_count'] = Sample.objects.filter(current_status='RECEIVED_FRONT_DESK').count()
            context['testing_samples_count'] = Sample.objects.filter(
                current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']
            ).count()
            context['review_pending_count'] = Sample.objects.filter(current_status='REVIEW_PENDING').count()
            context['completed_samples_count'] = Sample.objects.filter(current_status='REPORT_APPROVED').count()

            context['recent_customers'] = Customer.objects.order_by('-customer_id')[:5]
            context['recent_samples'] = Sample.objects.select_related('customer').order_by('-collection_datetime')[:10]
            context['recent_users'] = CustomUser.objects.order_by('-date_joined')[:5]

            context['user_stats'] = CustomUser.objects.values('role').annotate(count=Count('pk'))

            context['today_samples_count'] = Sample.objects.filter(
                collection_datetime__date=timezone.now().date()
            ).count()
            context['week_samples_count'] = Sample.objects.filter(
                collection_datetime__gte=timezone.now() - timedelta(days=7)
            ).count()

            context['samples_in_lab'] = Sample.objects.filter(
                current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']
            ).select_related('customer').order_by('collection_datetime')[:5]

            context['samples_awaiting_review'] = Sample.objects.filter(
                current_status='RESULTS_ENTERED'
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

        context.update({
            'pending_tests': Sample.objects.filter(
                current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']
            ).count(),
            'completed_tests': Sample.objects.filter(current_status='RESULTS_ENTERED').count(),
            'my_tests': TestResult.objects.filter(technician=self.request.user).count(),
            'today_tests': TestResult.objects.filter(
                test_date__date=timezone.now().date(),
                technician=self.request.user,
            ).count(),
            'samples_for_testing': Sample.objects.filter(
                current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']
            ).select_related('customer').order_by('collection_datetime')[:10],
            'recently_completed_samples': Sample.objects.filter(
                results__technician=self.request.user,
                current_status__in=['RESULTS_ENTERED', 'REVIEW_PENDING', 'REPORT_APPROVED'],
            ).distinct().select_related('customer').order_by('-collection_datetime')[:10],
            'recent_results': TestResult.objects.filter(
                technician=self.request.user,
            ).select_related('sample', 'parameter').order_by('-test_date')[:10],
            'total_parameters': TestParameter.objects.count(),
        })
        return context


class FrontDeskDashboardView(FrontDeskRequiredMixin, TemplateView):
    template_name = 'core/dashboards/frontdesk_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'total_customers': Customer.objects.count(),
            'pending_samples': Sample.objects.filter(current_status='RECEIVED_FRONT_DESK').count(),
            'today_samples': Sample.objects.filter(collection_datetime__date=timezone.now().date()).count(),
            'ready_reports': Sample.objects.filter(current_status='REPORT_APPROVED').count(),
            'recent_customers': Customer.objects.order_by('-customer_id')[:8],
            'recent_samples': Sample.objects.select_related('customer').order_by('-collection_datetime')[:10],
            'samples_by_status': Sample.objects.values('current_status').annotate(count=Count('sample_id')),
            'week_customers': Customer.objects.filter(
                customer_id__in=Customer.objects.order_by('-customer_id')[:50].values_list('customer_id', flat=True)
            ).count(),
            'week_samples': Sample.objects.filter(
                collection_datetime__gte=timezone.now() - timedelta(days=7)
            ).count(),
        })
        return context


class ConsultantDashboardView(ConsultantRequiredMixin, TemplateView):
    template_name = 'core/dashboards/consultant_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'pending_reviews': Sample.objects.filter(current_status='REVIEW_PENDING').count(),
            'my_reviews': ConsultantReview.objects.filter(reviewer=self.request.user).count(),
            'approved_reports': ConsultantReview.objects.filter(
                reviewer=self.request.user,
                status='APPROVED',
            ).count(),
            'today_reviews': ConsultantReview.objects.filter(
                review_date__date=timezone.now().date(),
                reviewer=self.request.user,
            ).count(),
            'samples_for_review': Sample.objects.filter(
                current_status='REVIEW_PENDING'
            ).select_related('customer').order_by('collection_datetime')[:10],
            'recent_reviews': ConsultantReview.objects.filter(
                reviewer=self.request.user
            ).select_related('sample').order_by('-review_date')[:10],
            'recently_reviewed_samples': Sample.objects.filter(
                review__reviewer=self.request.user,
                review__status__in=['APPROVED', 'REJECTED'],
            ).select_related('customer').order_by('-review__review_date')[:10],
            'review_stats': ConsultantReview.objects.filter(
                reviewer=self.request.user
            ).values('status').annotate(count=Count('review_id')),
        })
        return context

