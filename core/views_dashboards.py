import logging
from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, Q
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
            now = timezone.now()
            today = timezone.localdate()
            sample_counts = Sample.objects.aggregate(
                total_samples=Count('sample_id'),
                pending_samples_count=Count(
                    'sample_id',
                    filter=Q(current_status='RECEIVED_FRONT_DESK'),
                ),
                testing_samples_count=Count(
                    'sample_id',
                    filter=Q(current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']),
                ),
                review_pending_count=Count(
                    'sample_id',
                    filter=Q(current_status='REVIEW_PENDING'),
                ),
                completed_samples_count=Count(
                    'sample_id',
                    filter=Q(current_status__in=['REPORT_APPROVED', 'REPORT_SENT']),
                ),
                today_samples_count=Count(
                    'sample_id',
                    filter=Q(collection_datetime__date=today),
                ),
                week_samples_count=Count(
                    'sample_id',
                    filter=Q(collection_datetime__gte=now - timedelta(days=7)),
                ),
            )

            context['total_users'] = CustomUser.objects.count()
            context['total_customers'] = Customer.objects.count()
            context.update(sample_counts)

            context['recent_customers'] = Customer.objects.order_by('-customer_id')[:5]
            context['recent_samples'] = Sample.objects.select_related('customer').order_by('-collection_datetime')[:10]

            role_labels = dict(CustomUser.ROLE_CHOICES)
            context['user_stats'] = [
                {
                    'role': role_labels.get(stat['role'], stat['role'] or 'Undefined'),
                    'count': stat['count'],
                }
                for stat in CustomUser.objects.values('role').annotate(count=Count('pk')).order_by('role')
            ]

            context['samples_in_lab'] = Sample.objects.filter(
                current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']
            ).select_related('customer').order_by('collection_datetime')[:5]

            context['samples_awaiting_review'] = Sample.objects.filter(
                current_status='REVIEW_PENDING'
            ).select_related('customer').order_by('collection_datetime')[:5]

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
        today = timezone.localdate()

        sample_counts = Sample.objects.aggregate(
            pending_tests=Count(
                'sample_id',
                filter=Q(current_status__in=['SENT_TO_LAB', 'TESTING_IN_PROGRESS']),
            ),
            completed_tests=Count(
                'sample_id',
                filter=Q(current_status='RESULTS_ENTERED'),
            ),
        )
        result_counts = TestResult.objects.filter(technician=self.request.user).aggregate(
            my_tests=Count('pk'),
            today_tests=Count('pk', filter=Q(test_date__date=today)),
        )

        context.update({
            **sample_counts,
            **result_counts,
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
        now = timezone.now()
        today = timezone.localdate()
        sample_counts = Sample.objects.aggregate(
            pending_samples=Count(
                'sample_id',
                filter=Q(current_status='RECEIVED_FRONT_DESK'),
            ),
            today_samples=Count(
                'sample_id',
                filter=Q(collection_datetime__date=today),
            ),
            ready_reports=Count(
                'sample_id',
                filter=Q(current_status='REPORT_APPROVED'),
            ),
            week_samples=Count(
                'sample_id',
                filter=Q(collection_datetime__gte=now - timedelta(days=7)),
            ),
        )

        context.update({
            'total_customers': Customer.objects.count(),
            **sample_counts,
            'recent_customers': Customer.objects.order_by('-customer_id')[:8],
            'recent_samples': Sample.objects.select_related('customer').order_by('-collection_datetime')[:10],
            'samples_by_status': Sample.objects.values('current_status').annotate(
                count=Count('sample_id')
            ).order_by('current_status'),
            'week_customers': Customer.objects.filter(
                customer_id__in=Customer.objects.order_by('-customer_id')[:50].values_list('customer_id', flat=True)
            ).count(),
        })
        return context


class ConsultantDashboardView(ConsultantRequiredMixin, TemplateView):
    template_name = 'core/dashboards/consultant_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        pending_reviews = Sample.objects.filter(current_status='REVIEW_PENDING').count()
        review_counts = ConsultantReview.objects.filter(reviewer=self.request.user).aggregate(
            my_reviews=Count('pk'),
            approved_reports=Count('pk', filter=Q(status='APPROVED')),
            today_reviews=Count('pk', filter=Q(review_date__date=today)),
        )

        context.update({
            'pending_reviews': pending_reviews,
            **review_counts,
            'samples_for_review': Sample.objects.filter(
                current_status='REVIEW_PENDING'
            ).select_related('customer').annotate(
                result_count=Count('results')
            ).order_by('collection_datetime')[:10],
            'recent_reviews': ConsultantReview.objects.filter(
                reviewer=self.request.user
            ).select_related('sample', 'sample__customer').order_by('-review_date')[:10],
            'recently_reviewed_samples': Sample.objects.filter(
                review__reviewer=self.request.user,
                review__status__in=['APPROVED', 'REJECTED'],
            ).select_related('customer').order_by('-review__review_date')[:10],
            'review_stats': ConsultantReview.objects.filter(
                reviewer=self.request.user
            ).values('status').annotate(count=Count('review_id')),
        })
        return context
