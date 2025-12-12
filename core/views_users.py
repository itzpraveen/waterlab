import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, resolve_url
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from .decorators import admin_required
from .forms import AdminUserCreateForm, AdminUserUpdateForm, LabProfileForm
from .mixins import AdminRequiredMixin, AuditMixin
from .models import AuditTrail, CustomUser, LabProfile
from .views_common import _format_error_message

logger = logging.getLogger(__name__)


class AdminUserListView(AdminRequiredMixin, ListView):
    model = CustomUser
    template_name = 'core/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        queryset = CustomUser.objects.all().order_by('-is_active', 'first_name', 'username')
        search_term = self.request.GET.get('q', '').strip()
        role_filter = self.request.GET.get('role', 'all').strip()
        status_filter = self.request.GET.get('status', 'all').strip()

        if search_term:
            queryset = queryset.filter(
                Q(username__icontains=search_term)
                | Q(first_name__icontains=search_term)
                | Q(last_name__icontains=search_term)
                | Q(email__icontains=search_term)
                | Q(phone__icontains=search_term)
            )

        valid_roles = {choice[0] for choice in CustomUser.ROLE_CHOICES}
        if role_filter in valid_roles:
            queryset = queryset.filter(role=role_filter)

        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_term = self.request.GET.get('q', '').strip()
        role_filter = self.request.GET.get('role', 'all').strip()
        status_filter = self.request.GET.get('status', 'all').strip()

        context.update({
            'page_title': 'User management',
            'search_term': search_term,
            'role_filter': role_filter,
            'status_filter': status_filter,
            'role_choices': CustomUser.ROLE_CHOICES,
            'active_count': CustomUser.objects.filter(is_active=True).count(),
            'inactive_count': CustomUser.objects.filter(is_active=False).count(),
            'role_counts': CustomUser.objects.values('role').annotate(count=Count('pk')).order_by('role'),
            'query_string': self._build_query_string(exclude_keys=['page']),
        })
        return context

    def _build_query_string(self, exclude_keys=None):
        exclude_keys = set(exclude_keys or [])
        params = self.request.GET.copy()
        for key in list(params.keys()):
            if key in exclude_keys:
                params.pop(key)
        encoded = params.urlencode()
        return f'&{encoded}' if encoded else ''


class AdminUserCreateView(AuditMixin, AdminRequiredMixin, CreateView):
    model = CustomUser
    form_class = AdminUserCreateForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"User '{self.object.username}' created successfully.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Add team member'
        context['is_create'] = True
        return context


class AdminUserUpdateView(AuditMixin, AdminRequiredMixin, UpdateView):
    model = CustomUser
    form_class = AdminUserUpdateForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_list')

    def form_valid(self, form):
        original = CustomUser.objects.get(pk=self.object.pk)
        new_role = form.cleaned_data.get('role')
        new_active = form.cleaned_data.get('is_active')

        if original.role == 'admin' and (new_role != 'admin' or not new_active):
            remaining_admins = (
                CustomUser.objects.filter(role='admin', is_active=True)
                .exclude(pk=original.pk)
            )
            if not remaining_admins.exists():
                if new_role != 'admin':
                    form.add_error('role', 'At least one active administrator must remain.')
                else:
                    form.add_error('is_active', 'At least one active administrator must remain active.')
                return self.form_invalid(form)

        response = super().form_valid(form)
        if form.cleaned_data.get('password1'):
            messages.success(self.request, f"User '{self.object.username}' updated and password reset.")
        else:
            messages.success(self.request, f"User '{self.object.username}' updated successfully.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Edit: {self.object.get_full_name() or self.object.username}"
        context['is_create'] = False
        return context


class LabProfileUpdateView(AuditMixin, AdminRequiredMixin, UpdateView):
    model = LabProfile
    form_class = LabProfileForm
    template_name = 'core/lab_profile_form.html'
    success_url = reverse_lazy('core:lab_profile')

    def get_object(self, queryset=None):
        defaults = getattr(settings, 'WATERLAB_SETTINGS', {})
        profile, _ = LabProfile.objects.get_or_create(
            defaults={
                'name': defaults.get('LAB_NAME', 'Biofix Laboratory'),
                'address_line1': defaults.get('LAB_ADDRESS', ''),
                'phone': defaults.get('LAB_PHONE', ''),
                'email': defaults.get('LAB_EMAIL', ''),
            }
        )
        return profile

    def form_valid(self, form):
        messages.success(self.request, 'Laboratory profile updated successfully.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Laboratory profile'
        return context


@login_required
@admin_required
@require_POST
def toggle_user_active(request, pk):
    user_to_toggle = get_object_or_404(CustomUser, pk=pk)

    redirect_target = request.POST.get('next') or resolve_url('core:user_list')

    if user_to_toggle == request.user:
        messages.error(request, 'You cannot change your own activation status.')
        return redirect(redirect_target)

    if user_to_toggle.role == 'admin' and user_to_toggle.is_active:
        remaining_admins = (
            CustomUser.objects.filter(role='admin', is_active=True)
            .exclude(pk=user_to_toggle.pk)
        )
        if not remaining_admins.exists():
            messages.error(
                request,
                'At least one active administrator must remain. Promote another admin before deactivating this account.',
            )
            return redirect(redirect_target)

    try:
        with transaction.atomic():
            old_values = {'is_active': user_to_toggle.is_active}
            user_to_toggle.is_active = not user_to_toggle.is_active
            user_to_toggle.save(update_fields=['is_active'])
            new_values = {'is_active': user_to_toggle.is_active}
            AuditTrail.log_change(
                user=request.user,
                action='UPDATE',
                instance=user_to_toggle,
                old_values=old_values,
                new_values=new_values,
                request=request,
            )
        status_text = 'activated' if user_to_toggle.is_active else 'deactivated'
        messages.success(request, f"User '{user_to_toggle.username}' has been {status_text}.")
    except Exception as exc:
        logger.exception('Failed to toggle activation for user %s', pk)
        messages.error(request, _format_error_message('Unable to change user status.', exc))

    return redirect(redirect_target)

