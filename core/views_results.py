import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Max, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import DetailView, ListView
from django.core.exceptions import ValidationError

from .decorators import lab_required
from .forms import TestResultEntryForm
from .models import AuditTrail, Sample, TestResult
from .views_common import _format_error_message

logger = logging.getLogger(__name__)


class TestResultListView(LoginRequiredMixin, ListView):
    model = Sample
    template_name = 'core/test_result_list.html'
    context_object_name = 'samples_with_results'
    paginate_by = 15

    def get_search_query(self):
        return (self.request.GET.get('q') or '').strip()

    def get_status_filter(self):
        status = (self.request.GET.get('status') or '').upper().strip()
        if status in {code for code, _ in Sample.SAMPLE_STATUS_CHOICES}:
            return status
        if status in {'PENDING', 'IN_LAB', 'AWAITING_REVIEW', 'COMPLETED'}:
            mapping = {
                'PENDING': ['RECEIVED_FRONT_DESK'],
                'IN_LAB': ['SENT_TO_LAB', 'TESTING_IN_PROGRESS'],
                'AWAITING_REVIEW': ['REVIEW_PENDING'],
                'COMPLETED': ['REPORT_APPROVED', 'REPORT_SENT'],
            }
            return mapping[status]
        return None

    def get_status_label(self, raw_value):
        if not raw_value:
            return ''
        raw_upper = raw_value.upper()
        friendly = {
            'PENDING': 'Pending intake',
            'IN_LAB': 'In laboratory',
            'AWAITING_REVIEW': 'Awaiting review',
            'COMPLETED': 'Completed',
        }.get(raw_upper)
        if friendly:
            return friendly
        status_choices = dict(Sample.SAMPLE_STATUS_CHOICES)
        return status_choices.get(raw_value, raw_value)

    def get_filter_dates(self):
        collected = (self.request.GET.get('collected') or '').lower()
        if collected == 'today':
            return timezone.now().date(), None
        if collected == 'week':
            return timezone.now().date() - timedelta(days=7), None
        if collected == 'month':
            return timezone.now().date() - timedelta(days=30), None
        return None, None

    def get_collected_label(self, raw_value):
        mapping = {
            'today': 'Collected today',
            'week': 'Past 7 days',
            'month': 'Past 30 days',
        }
        return mapping.get((raw_value or '').lower(), raw_value)

    def get_queryset(self):
        ordered_results = TestResult.objects.select_related('parameter', 'parameter__category_obj').order_by(
            'parameter__category_obj__display_order',
            'parameter__category',
            'parameter__display_order',
            'parameter__name',
        )
        queryset = (
            Sample.objects.annotate(latest_test_date=Max('results__test_date'))
            .filter(results__isnull=False)
            .select_related('customer')
            .prefetch_related(Prefetch('results', queryset=ordered_results), 'tests_requested')
            .distinct()
            .order_by('-latest_test_date', '-collection_datetime')
        )

        query = self.get_search_query()
        if query:
            queryset = queryset.filter(
                Q(display_id__icontains=query)
                | Q(customer__name__icontains=query)
                | Q(customer__street_locality_landmark__icontains=query)
                | Q(customer__village_town_city__icontains=query)
            )

        status_filter = self.get_status_filter()
        if status_filter:
            if isinstance(status_filter, (list, tuple, set)):
                queryset = queryset.filter(current_status__in=status_filter)
            else:
                queryset = queryset.filter(current_status=status_filter)

        start_date, end_date = self.get_filter_dates()
        if start_date:
            queryset = queryset.filter(collection_datetime__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(collection_datetime__date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Samples with Test Results'
        context['search_query'] = self.get_search_query()
        context['status_filter'] = self.request.GET.get('status', '')
        context['collected_filter'] = self.request.GET.get('collected', '')
        context['status_filter_label'] = self.get_status_label(context['status_filter'])
        context['collected_filter_label'] = self.get_collected_label(context['collected_filter'])
        context['active_filters'] = {
            'status': context['status_filter'],
            'collected': context['collected_filter'],
        }
        context['sample_status_choices'] = Sample.SAMPLE_STATUS_CHOICES

        if context['search_query'] or context['status_filter'] or context['collected_filter']:
            context['show_reset_filters'] = True

        return context


class TestResultDetailView(LoginRequiredMixin, DetailView):
    model = Sample
    template_name = 'core/test_result_detail.html'
    context_object_name = 'sample'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['results'] = (
            TestResult.objects.filter(sample=self.object)
            .select_related('parameter', 'parameter__category_obj')
            .order_by(
                'parameter__category_obj__display_order',
                'parameter__category',
                'parameter__display_order',
                'parameter__name',
            )
        )
        return context


@lab_required
def test_result_entry(request, sample_id):
    sample = get_object_or_404(Sample, sample_id=sample_id)

    allowed_statuses_for_entry = ['SENT_TO_LAB', 'TESTING_IN_PROGRESS', 'RESULTS_ENTERED']
    if request.user.is_admin and sample.current_status == 'REVIEW_PENDING':
        allowed_statuses_for_entry.append('REVIEW_PENDING')

    if sample.current_status not in allowed_statuses_for_entry:
        messages.error(
            request,
            f'Sample is not available for result entry/correction. Current status: {sample.get_current_status_display()}',
        )
        return redirect('core:sample_detail', pk=sample.sample_id)

    if request.method == 'POST':
        submit_action = request.POST.get('submit_action', 'save')
        send_for_review = submit_action == 'save_and_review'
        try:
            with transaction.atomic():
                original_status_was_review_pending = (sample.current_status == 'REVIEW_PENDING')

                if sample.current_status == 'SENT_TO_LAB':
                    sample.update_status('TESTING_IN_PROGRESS', request.user)

                results_entered_count = 0
                results_updated_count = 0
                all_forms_valid = True
                form_errors = {}

                for test_param_model in sample.tests_requested.all().order_by('display_order', 'name'):
                    form_prefix = f'param_{test_param_model.parameter_id}'
                    form = TestResultEntryForm(request.POST, prefix=form_prefix)

                    if form.is_valid():
                        result_value = form.cleaned_data['result_value']
                        observation = form.cleaned_data['observation']
                        remarks = form.cleaned_data.get('remarks')

                        if result_value and result_value.strip():
                            test_result, created = TestResult.objects.get_or_create(
                                sample=sample,
                                parameter=test_param_model,
                                defaults={
                                    'result_value': result_value.strip(),
                                    'observation': observation,
                                    'remarks': remarks,
                                    'technician': request.user,
                                },
                            )
                            if created:
                                AuditTrail.log_change(
                                    user=request.user,
                                    action='CREATE',
                                    instance=test_result,
                                    request=request,
                                )
                                test_result.full_clean()
                                results_entered_count += 1
                            else:
                                old_values = {
                                    'result_value': test_result.result_value,
                                    'observation': test_result.observation,
                                    'remarks': test_result.remarks,
                                }
                                test_result.result_value = result_value.strip()
                                test_result.observation = observation
                                test_result.remarks = remarks
                                test_result.full_clean()
                                test_result.save()
                                AuditTrail.log_change(
                                    user=request.user,
                                    action='UPDATE',
                                    instance=test_result,
                                    old_values=old_values,
                                    new_values=form.cleaned_data,
                                    request=request,
                                )
                                results_updated_count += 1
                    else:
                        all_forms_valid = False
                        form_errors[test_param_model.parameter_id] = form.errors

                if not all_forms_valid:
                    messages.error(request, "There were errors in your submission. Please correct them and try again.")
                    raise ValidationError(
                        f"Form validation failed for {test_param_model.name}. Please check your input."
                    )

                if original_status_was_review_pending:
                    messages.info(
                        request,
                        f"Results for sample (ID: {sample.sample_id}) updated by admin. The sample remains in 'Review Pending' status.",
                    )
                else:
                    total_tests = sample.tests_requested.count()
                    completed_tests = sample.results.count()

                    if completed_tests >= total_tests and total_tests > 0:
                        status_now = sample.current_status
                        if status_now != 'RESULTS_ENTERED':
                            sample.update_status('RESULTS_ENTERED', request.user)
                            messages.success(
                                request,
                                f'All test results entered for sample {sample.sample_id}. Sample moved to "Results Entered" status.',
                            )
                        else:
                            messages.success(
                                request,
                                f'All test results for sample {sample.sample_id} have been updated.',
                            )

                        if send_for_review:
                            try:
                                sample.update_status('REVIEW_PENDING', request.user)
                                messages.success(
                                    request,
                                    f'Sample {sample.sample_id} sent for consultant review.',
                                )
                            except ValidationError as exc:
                                error_message = (
                                    str(exc.message_dict)
                                    if hasattr(exc, 'message_dict')
                                    else str(exc)
                                )
                                messages.error(request, f"Could not send for review: {error_message}")
                                return redirect('core:sample_detail', pk=sample.sample_id)
                    else:
                        if send_for_review:
                            messages.warning(
                                request,
                                'All requested tests must have results before sending for review.',
                            )
                        messages.info(
                            request,
                            f'Results saved. {completed_tests}/{total_tests} tests completed.',
                        )

                if results_entered_count > 0:
                    messages.success(request, f'{results_entered_count} new test results entered.')
                if results_updated_count > 0:
                    messages.info(request, f'{results_updated_count} test results updated.')

                return redirect('core:sample_detail', pk=sample.sample_id)

        except Exception as exc:
            logger.exception("Failed to save test results for sample %s", sample.sample_id)
            messages.error(request, _format_error_message('Error saving test results.', exc))
            return redirect('core:sample_detail', pk=sample.sample_id)

    form_data = {}
    for test_param_model in sample.tests_requested.all().order_by('display_order', 'name'):
        form_prefix = f'param_{test_param_model.parameter_id}'

        try:
            existing_result = TestResult.objects.get(sample=sample, parameter=test_param_model)
            initial_data = {
                'result_value': existing_result.result_value,
                'observation': existing_result.observation,
                'remarks': existing_result.remarks,
            }
        except TestResult.DoesNotExist:
            initial_data = {}
            existing_result = None

        form_data[test_param_model.parameter_id] = {
            'form': TestResultEntryForm(
                prefix=form_prefix,
                initial=initial_data,
                parameter=test_param_model,
            ),
            'parameter': test_param_model,
            'existing_result': existing_result,
        }

        if 'existing_result' in locals():
            del existing_result

    context = {
        'sample': sample,
        'form_data': form_data,
        'can_edit': sample.current_status in ['SENT_TO_LAB', 'TESTING_IN_PROGRESS', 'RESULTS_ENTERED']
        or (request.user.is_admin() and sample.current_status == 'REVIEW_PENDING'),
        'can_send_for_review': sample.current_status in ['SENT_TO_LAB', 'TESTING_IN_PROGRESS', 'RESULTS_ENTERED']
        and sample.tests_requested.exists(),
    }

    return render(request, 'core/test_result_entry.html', context)
