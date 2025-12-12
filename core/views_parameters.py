import logging
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import UpdateView

from .decorators import admin_required
from .forms import TestParameterForm
from .mixins import AdminRequiredMixin
from .models import AuditTrail, TestCategory, TestParameter
from .views_common import _format_error_message

logger = logging.getLogger(__name__)


def setup_test_parameters(request):
    """Admin view to seed and manage TestParameter records."""

    def _next_order_for(_: TestCategory | None) -> int:
        last = TestParameter.objects.order_by('-display_order').first()
        base = (last.display_order if last and last.display_order else 0)
        return (base // 10 + 1) * 10 if base else 10

    categories = TestCategory.objects.all().order_by('display_order', 'name')
    selected_category_id = request.GET.get('category') or request.POST.get('category')
    selected_category = None
    if selected_category_id:
        try:
            selected_category = categories.get(pk=selected_category_id)
        except Exception:
            selected_category = None

    parameters_qs = TestParameter.objects.all()
    if selected_category:
        parameters_qs = parameters_qs.filter(category_obj=selected_category)
    parameters = parameters_qs.order_by('display_order', 'name')
    form = TestParameterForm()
    if selected_category:
        form.fields['category_obj'].initial = selected_category.pk
        form.fields['display_order'].initial = _next_order_for(selected_category)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_standard' or not any(request.POST.get(k) for k in ['name', 'unit']):
            try:
                from core.services.parameters import seed_standard_parameters
                created_count, skipped = seed_standard_parameters(user=request.user)
                messages.success(
                    request,
                    f"Standard parameters processed. Created {created_count} new parameter(s); {skipped} existing.",
                )
                return redirect('core:setup_test_parameters')
            except Exception as exc:
                logger.exception("Failed to seed standard test parameters")
                messages.error(
                    request,
                    _format_error_message("Error creating standard parameters.", exc),
                )
        else:
            form = TestParameterForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        if not form.cleaned_data.get('display_order'):
                            form.instance.display_order = _next_order_for(form.cleaned_data.get('category_obj'))
                        parameter = form.save()
                        AuditTrail.log_change(
                            user=request.user,
                            action='CREATE',
                            instance=parameter,
                            request=request,
                        )
                        messages.success(request, f"Test parameter '{parameter.name}' created successfully.")
                        if selected_category:
                            return redirect(
                                f"{reverse_lazy('core:setup_test_parameters')}?category={selected_category.pk}"
                            )
                        return redirect('core:setup_test_parameters')
                except Exception as exc:
                    logger.exception("Failed to create test parameter via setup view")
                    messages.error(
                        request,
                        _format_error_message("Error creating test parameter.", exc),
                    )
            else:
                messages.error(request, "Error in form submission. Please check the details.")

    context = {
        'existing_params': parameters,
        'parameters': parameters,
        'categories': categories,
        'selected_category': selected_category,
        'next_order': _next_order_for(selected_category) if selected_category or parameters.exists() else 10,
        'form': form,
        'page_title': 'Setup Test Parameters',
    }
    return render(request, 'core/setup_test_parameters.html', context)


@login_required
@admin_required
@require_POST
def reorder_test_parameters(request):
    """Reorder parameters via drag-and-drop."""

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        payload = request.POST

    groups = payload.get('groups')
    if groups:
        updated_total = 0
        with transaction.atomic():
            for group in groups:
                ids = group.get('order') or []
                category_id = group.get('category')
                qs = TestParameter.objects.filter(parameter_id__in=ids)
                if category_id:
                    try:
                        cat = TestCategory.objects.get(pk=category_id)
                    except TestCategory.DoesNotExist:
                        return JsonResponse({"ok": False, "error": f"Invalid category {category_id}"}, status=400)
                    qs = qs.filter(category_obj=cat)
                else:
                    qs = qs.filter(category_obj__isnull=True)

                found_ids = set(str(x) for x in qs.values_list('parameter_id', flat=True))
                missing = [i for i in ids if str(i) not in found_ids]
                if missing:
                    return JsonResponse({"ok": False, "error": f"Unknown parameter ids: {', '.join(missing)}"}, status=400)

                obj_by_id = {str(obj.parameter_id): obj for obj in qs}
                running = 10
                changed = []
                for pid in ids:
                    obj = obj_by_id[str(pid)]
                    if obj.display_order != running:
                        obj.display_order = running
                        changed.append(obj)
                    running += 10
                if changed:
                    TestParameter.objects.bulk_update(changed, ['display_order'])
                    updated_total += len(changed)
        return JsonResponse({"ok": True, "updated": updated_total})

    order_payload = payload.get('order')
    if not isinstance(order_payload, list) or not order_payload:
        return JsonResponse({"ok": False, "error": "No order provided."}, status=400)

    def _normalise(item):
        if isinstance(item, dict):
            value = item.get('id')
        else:
            value = item
        return str(value) if value else None

    ids = [pid for pid in (_normalise(item) for item in order_payload) if pid]
    if not ids:
        return JsonResponse({"ok": False, "error": "Invalid IDs."}, status=400)

    raw_category = payload.get('category')
    if raw_category not in (None, '', 'null', 'None'):
        mode = 'category'
        try:
            category_obj = TestCategory.objects.get(pk=raw_category)
        except TestCategory.DoesNotExist:
            return JsonResponse({"ok": False, "error": f"Invalid category {raw_category}"}, status=400)
    elif raw_category in ('null', 'None'):
        mode = 'uncategorized'
        category_obj = None
    else:
        mode = 'global'
        category_obj = None

    def apply_global_sequence(sequence):
        objs = list(TestParameter.objects.filter(parameter_id__in=sequence))
        if len(objs) != len(sequence):
            found = {str(obj.parameter_id) for obj in objs}
            missing = [pid for pid in sequence if pid not in found]
            return None, JsonResponse({"ok": False, "error": f"Unknown parameter ids: {', '.join(missing)}"}, status=400)
        obj_by_id = {str(obj.parameter_id): obj for obj in objs}
        running = 10
        changed = []
        for pid in sequence:
            obj = obj_by_id[str(pid)]
            if obj.display_order != running:
                obj.display_order = running
                changed.append(obj)
            running += 10
        if changed:
            TestParameter.objects.bulk_update(changed, ['display_order'])
        return len(changed), None

    if mode == 'global':
        total = TestParameter.objects.count()
        if len(ids) != total:
            return JsonResponse({"ok": False, "error": "Full order required for global reorder."}, status=400)
        updated, error_response = apply_global_sequence(ids)
        if error_response:
            return error_response
        return JsonResponse({"ok": True, "updated": updated})

    def matches(cat_id):
        if mode == 'category':
            return cat_id == category_obj.pk
        return cat_id is None

    all_rows = list(TestParameter.objects.order_by('display_order', 'name').values_list('parameter_id', 'category_obj_id'))
    current_subset = [str(pid) for pid, cat_id in all_rows if matches(cat_id)]
    if len(current_subset) != len(ids) or set(current_subset) != set(ids):
        return JsonResponse({"ok": False, "error": "Provided IDs do not match the selected category contents."}, status=400)

    ids_iter = iter(ids)
    rebuilt_sequence = []
    for pid, cat_id in all_rows:
        if matches(cat_id):
            rebuilt_sequence.append(next(ids_iter))
        else:
            rebuilt_sequence.append(str(pid))

    updated, error_response = apply_global_sequence(rebuilt_sequence)
    if error_response:
        return error_response
    return JsonResponse({"ok": True, "updated": updated})


class TestParameterUpdateView(AdminRequiredMixin, UpdateView):
    model = TestParameter
    form_class = TestParameterForm
    template_name = 'core/test_parameter_form.html'
    success_url = reverse_lazy('core:setup_test_parameters')

    def form_valid(self, form):
        try:
            with transaction.atomic():
                old_values = TestParameter.objects.filter(pk=self.object.pk).values().first()
                parameter = form.save()
                new_values = TestParameter.objects.filter(pk=parameter.pk).values().first()
                AuditTrail.log_change(
                    user=self.request.user,
                    action='UPDATE',
                    instance=parameter,
                    old_values=old_values,
                    new_values=new_values,
                    request=self.request,
                )
                messages.success(self.request, f"Test parameter '{parameter.name}' updated successfully.")
        except Exception as exc:
            logger.exception("Failed to update test parameter %s", self.object.pk)
            messages.error(
                self.request,
                _format_error_message("Error updating test parameter.", exc),
            )
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit Test Parameter: {self.object.name}'
        context['is_edit'] = True
        return context


@login_required
@admin_required
def setup_test_categories(request):
    categories = TestCategory.objects.all().order_by('display_order', 'name')
    from django import forms

    class TestCategoryForm(forms.ModelForm):
        class Meta:
            model = TestCategory
            fields = ['name', 'display_order']
            widgets = {
                'name': forms.TextInput(attrs={'class': 'form-control'}),
                'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            }

    form = TestCategoryForm()
    if request.method == 'POST':
        form = TestCategoryForm(request.POST)
        if form.is_valid():
            obj = form.save()
            AuditTrail.log_change(user=request.user, action='CREATE', instance=obj, request=request)
            messages.success(request, f"Category '{obj.name}' created.")
            return redirect('core:setup_test_categories')
        messages.error(request, "Error in form submission.")

    return render(request, 'core/setup_test_categories.html', {
        'form': form,
        'categories': categories,
        'page_title': 'Setup Categories',
    })


class TestCategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = TestCategory
    fields = ['name', 'display_order']
    template_name = 'core/test_category_form.html'
    success_url = reverse_lazy('core:setup_test_categories')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Edit Category: {self.object.name}'
        context['is_edit'] = True
        return context


@login_required
@admin_required
@require_POST
def delete_test_category(request, pk):
    category = get_object_or_404(TestCategory, pk=pk)
    name = category.name
    try:
        with transaction.atomic():
            old_values = {'name': name, 'display_order': category.display_order}
            AuditTrail.log_change(
                user=request.user,
                action='DELETE',
                instance=category,
                old_values=old_values,
                new_values={},
                request=request,
            )
            category.delete()
            messages.success(request, f"Category '{name}' deleted.")
    except Exception as exc:
        logger.exception("Failed to delete category %s", pk)
        messages.error(request, _format_error_message("Error deleting category.", exc))
    return redirect('core:setup_test_categories')


@login_required
def kerala_locations_json(request):
    """Return district -> taluk -> local body names from the DB."""
    from .models import KeralaLocation
    if not KeralaLocation.objects.exists():
        return JsonResponse({}, status=204)

    data = {}
    districts = KeralaLocation.objects.filter(location_type='district').order_by('name')
    taluks = KeralaLocation.objects.filter(location_type='taluk').select_related('parent')
    local_bodies = KeralaLocation.objects.exclude(
        location_type__in=['district', 'taluk']
    ).select_related('parent')

    taluks_by_district = {}
    for t in taluks:
        taluks_by_district.setdefault(t.parent_id, []).append(t)

    locals_by_taluk = {}
    for lb in local_bodies:
        locals_by_taluk.setdefault(lb.parent_id, []).append(lb)

    for d in districts:
        data[d.name] = {}
        for t in sorted(taluks_by_district.get(d.id, []), key=lambda x: x.name):
            names = [x.name for x in sorted(locals_by_taluk.get(t.id, []), key=lambda x: x.name)]
            data[d.name][t.name] = names

    return JsonResponse(data)


@login_required
@admin_required
@require_POST
def delete_test_parameter(request, pk):
    parameter = get_object_or_404(TestParameter, pk=pk)
    parameter_name = parameter.name

    try:
        with transaction.atomic():
            old_values = model_to_dict(parameter)
            AuditTrail.log_change(
                user=request.user,
                action='DELETE',
                instance=parameter,
                old_values=old_values,
                new_values={},
                request=request,
            )
            parameter.delete()
            messages.success(request, f"Test parameter '{parameter_name}' deleted successfully.")
    except ProtectedError:
        messages.error(
            request,
            f"Cannot delete '{parameter_name}' because test results are linked to it.",
        )
    except Exception as exc:
        logger.exception("Failed to delete test parameter %s", pk)
        messages.error(
            request,
            _format_error_message("Error deleting test parameter.", exc),
        )

    return redirect('core:setup_test_parameters')

