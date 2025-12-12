import logging
from collections import OrderedDict
from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .decorators import consultant_required
from .forms import SampleForm, SampleReportMetadataForm
from .mixins import (
    AuditMixin,
    FrontDeskRequiredMixin,
    LabRequiredMixin,
    RoleRequiredMixin,
)
from .models import AuditTrail, ConsultantReview, LabProfile, Sample, TestResult
from .views_common import _SENSITIVE_ROLES, _format_error_message, apply_user_scope

logger = logging.getLogger(__name__)


class SampleListView(RoleRequiredMixin, ListView):
    model = Sample
    template_name = 'core/sample_list.html'
    context_object_name = 'samples'
    paginate_by = 25
    allowed_roles = list(_SENSITIVE_ROLES)

    def get_queryset(self):
        qs = (
            Sample.objects.select_related('customer')
            .prefetch_related('tests_requested')
            .order_by('-collection_datetime')
        )
        status_param = self.request.GET.get('status')
        if status_param:
            status_key = status_param.upper()
            status_map = {
                'PENDING': ['RECEIVED_FRONT_DESK'],
                'IN_LAB': ['SENT_TO_LAB', 'TESTING_IN_PROGRESS'],
                'AWAITING_REVIEW': ['REVIEW_PENDING'],
                'COMPLETED': ['REPORT_APPROVED', 'REPORT_SENT'],
            }
            if status_key in status_map:
                qs = qs.filter(current_status__in=status_map[status_key])
            else:
                qs = qs.filter(current_status=status_key)

        collected_scope = self.request.GET.get('collected')
        if collected_scope == 'today':
            qs = qs.filter(collection_datetime__date=timezone.now().date())
        elif collected_scope == 'week':
            qs = qs.filter(collection_datetime__gte=timezone.now() - timedelta(days=7))
        return apply_user_scope(qs, self.request.user)


class SampleDetailView(RoleRequiredMixin, DetailView):
    model = Sample
    template_name = 'core/sample_detail.html'
    context_object_name = 'sample'
    allowed_roles = list(_SENSITIVE_ROLES)

    def get_queryset(self):
        return apply_user_scope(super().get_queryset(), self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sample = context['sample']
        tests_qs = sample.tests_requested.all().order_by('display_order', 'name')
        results_qs = sample.results.select_related('parameter').order_by(
            'parameter__display_order',
            'parameter__name',
        )

        def _category_key(label: str) -> tuple[int, str]:
            lowered = label.casefold()
            if any(token in lowered for token in ('physical', 'chemical')):
                return (0, label)
            if any(token in lowered for token in ('micro', 'bacter')):
                return (1, label)
            if 'solution' in lowered:
                return (2, label)
            return (3, label)

        def _group_by_category(items, get_category):
            buckets = {}
            counter = 1
            for item in items:
                raw_category = (get_category(item) or '').strip()
                label = raw_category or 'Uncategorized'
                buckets.setdefault(label, []).append({
                    'index': counter,
                    'item': item,
                })
                counter += 1
            ordered_labels = sorted(buckets.keys(), key=_category_key)
            return OrderedDict((label, buckets[label]) for label in ordered_labels)

        context['ordered_tests'] = tests_qs
        context['tests_by_category'] = _group_by_category(
            tests_qs,
            lambda param: param.category_label,
        )
        context['ordered_results'] = results_qs

        results_by_category = _group_by_category(
            results_qs,
            lambda result: result.parameter.category_label,
        )
        for grouped_entries in results_by_category.values():
            for entry in grouped_entries:
                result = entry['item']
                status = result.get_limit_status()
                entry['limit_status'] = status
                entry['is_out_of_range'] = status in {'ABOVE_LIMIT', 'BELOW_LIMIT'}

        context['results_by_category'] = results_by_category
        lab_profile = LabProfile.get_active()
        context['lab_profile'] = lab_profile
        context['resolved_signatories'] = sample.resolve_signatories(lab_profile)
        return context


class SampleCreateView(AuditMixin, FrontDeskRequiredMixin, CreateView):
    model = Sample
    form_class = SampleForm
    template_name = 'core/sample_form.html'
    success_url = reverse_lazy('core:sample_list')

    def form_valid(self, form):
        if not form.instance.created_by and self.request.user.is_authenticated:
            form.instance.created_by = self.request.user
        messages.success(self.request, 'Sample has been registered successfully!')
        return super().form_valid(form)


class SampleUpdateView(AuditMixin, FrontDeskRequiredMixin, UpdateView):
    model = Sample
    form_class = SampleForm
    template_name = 'core/sample_form.html'

    def get_queryset(self):
        return apply_user_scope(super().get_queryset(), self.request.user)

    def get_success_url(self):
        return reverse_lazy('core:sample_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        sample = self.get_object()

        if sample.current_status not in ['RECEIVED_FRONT_DESK', 'SENT_TO_LAB']:
            messages.error(
                self.request,
                f'Cannot edit sample in status "{sample.get_current_status_display()}". '
                'Only samples that are "Received at Front Desk" or "Sent to Lab" can be modified.',
            )
            return redirect('core:sample_detail', pk=sample.sample_id)

        if sample.current_status == 'SENT_TO_LAB':
            original_tests = set(sample.tests_requested.all())
            new_tests = set(form.cleaned_data.get('tests_requested', []))

            if original_tests != new_tests:
                messages.error(
                    self.request,
                    'Cannot modify test requests after sample has been sent to lab. '
                    'Contact lab staff if changes are needed.',
                )
                return redirect('core:sample_detail', pk=sample.sample_id)

        messages.success(self.request, 'Sample has been updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True

        sample = self.get_object()
        context['sample_status'] = sample.current_status
        context['can_edit_tests'] = sample.current_status == 'RECEIVED_FRONT_DESK'
        context['can_edit_datetime'] = sample.current_status == 'RECEIVED_FRONT_DESK'
        context['status_display'] = sample.get_current_status_display()

        return context


class SampleReportMetadataUpdateView(AuditMixin, LabRequiredMixin, UpdateView):
    model = Sample
    form_class = SampleReportMetadataForm
    template_name = 'core/sample_report_metadata_form.html'

    def get_success_url(self):
        return reverse_lazy('core:sample_detail', kwargs={'pk': self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        sample = self.get_object()
        if not sample.sampling_location and sample.customer:
            fallback_location = (
                sample.customer.street_locality_landmark
                or sample.customer.village_town_city
                or sample.customer.district
            )
            if fallback_location:
                initial.setdefault('sampling_location', fallback_location)
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Report metadata updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the highlighted issues before saving.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sample'] = self.get_object()
        return context


@consultant_required
def consultant_review(request, sample_id):
    sample = get_object_or_404(Sample, sample_id=sample_id)

    if sample.current_status == 'RESULTS_ENTERED':
        if request.user.is_consultant() or request.user.is_admin():
            try:
                sample.update_status('REVIEW_PENDING', request.user)
                messages.info(
                    request,
                    f"Sample {sample.sample_id} moved to 'Review Pending' status.",
                )
                return redirect('core:consultant_review', sample_id=sample.sample_id)
            except ValidationError as exc:
                error_message = (
                    str(exc.message_dict)
                    if hasattr(exc, 'message_dict')
                    else str(exc)
                )
                messages.error(request, f"Could not move sample to review: {error_message}")
                return redirect('core:sample_detail', pk=sample.sample_id)
            except Exception as exc:
                logger.exception(
                    "Unexpected error while moving sample %s to review pending",
                    sample.sample_id,
                )
                messages.error(
                    request,
                    _format_error_message(
                        "An unexpected error occurred while updating status.",
                        exc,
                    ),
                )
                return redirect('core:sample_detail', pk=sample.sample_id)

        messages.error(
            request,
            "You do not have permission to move this sample to review.",
        )
        return redirect('core:sample_detail', pk=sample.sample_id)

    if sample.current_status != 'REVIEW_PENDING':
        messages.error(
            request,
            f'Sample is not available for review. Current status: {sample.get_current_status_display()}',
        )
        return redirect('core:sample_detail', pk=sample.sample_id)

    try:
        review = ConsultantReview.objects.get(sample=sample)
    except ConsultantReview.DoesNotExist:
        review = None

    if request.method == 'POST':
        action = request.POST.get('status')
        comments = request.POST.get('comments', '').strip()
        recommendations = request.POST.get('recommendations', '').strip()

        if action in ['APPROVED', 'REJECTED']:
            try:
                with transaction.atomic():
                    if review:
                        old_values = {
                            'status': review.status,
                            'comments': review.comments,
                            'recommendations': review.recommendations,
                        }
                        review.status = action
                        review.comments = comments
                        review.recommendations = recommendations
                        review.reviewer = request.user
                        review.review_date = timezone.now()
                        review.save()
                        AuditTrail.log_change(
                            user=request.user,
                            action='UPDATE',
                            instance=review,
                            old_values=old_values,
                            new_values=request.POST.dict(),
                            request=request,
                        )
                    else:
                        review = ConsultantReview.objects.create(
                            sample=sample,
                            reviewer=request.user,
                            status=action,
                            comments=comments,
                            recommendations=recommendations,
                        )
                        AuditTrail.log_change(
                            user=request.user,
                            action='CREATE',
                            instance=review,
                            request=request,
                        )

                    if action == 'APPROVED':
                        messages.success(
                            request,
                            f'Review for sample {sample.sample_id} saved as Approved. Sample status updated accordingly.',
                        )
                    elif action == 'REJECTED':
                        messages.warning(
                            request,
                            f'Review for sample {sample.sample_id} saved as Rejected. Sample status updated accordingly.',
                        )
                    else:
                        messages.info(
                            request,
                            f'Review for sample {sample.sample_id} saved with status {action}.',
                        )

                    return redirect('core:sample_detail', pk=sample.sample_id)

            except Exception as exc:
                logger.exception(
                    "Failed to process consultant review for sample %s",
                    sample.sample_id,
                )
                messages.error(request, _format_error_message('Error processing review.', exc))
                return redirect('core:sample_detail', pk=sample.sample_id)

        messages.error(request, 'Invalid action specified.')

    context = {
        'sample': sample,
        'review': review,
        'test_results': sample.results.all().select_related('parameter'),
        'can_review': sample.current_status == 'REVIEW_PENDING',
    }

    return render(request, 'core/consultant_review.html', context)


def sample_status_update(request, sample_id):
    sample_qs = apply_user_scope(Sample.objects.all(), request.user)
    sample = get_object_or_404(sample_qs, sample_id=sample_id)

    if request.method == 'POST':
        if not (
            request.user.is_frontdesk()
            or request.user.is_admin()
            or request.user.is_lab_tech()
        ):
            messages.error(request, "You do not have permission to perform this action.")
            return redirect('core:sample_detail', pk=sample.sample_id)

        new_status = request.POST.get('new_status')

        valid_status_codes = [s[0] for s in Sample.SAMPLE_STATUS_CHOICES]
        if not new_status or new_status not in valid_status_codes:
            messages.error(request, "Invalid target status provided.")
            return redirect('core:sample_detail', pk=sample.sample_id)

        try:
            sample.update_status(new_status, request.user)

            new_status_display_tuple = next(
                (s for s in Sample.SAMPLE_STATUS_CHOICES if s[0] == new_status),
                None,
            )
            new_status_display_name = (
                new_status_display_tuple[1]
                if new_status_display_tuple
                else new_status
            )

            messages.success(
                request,
                f"Sample {sample.sample_id} status successfully updated to '{new_status_display_name}'.",
            )

        except ValidationError as exc:
            error_message = (
                str(exc.message_dict)
                if hasattr(exc, 'message_dict')
                else str(exc)
            )
            messages.error(request, f"Error updating status: {error_message}")

        except Exception as exc:
            logger.exception(
                "Unexpected error in sample_status_update for sample %s",
                sample.sample_id,
            )
            messages.error(
                request,
                _format_error_message(
                    "An unexpected error occurred while updating sample status.",
                    exc,
                ),
            )

        return redirect('core:sample_detail', pk=sample.sample_id)

    return redirect('core:sample_detail', pk=sample.sample_id)
