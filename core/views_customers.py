from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import CustomerForm
from .mixins import AuditMixin, FrontDeskRequiredMixin, RoleRequiredMixin
from .models import Customer, Sample
from .views_common import _SENSITIVE_ROLES, apply_user_scope


class CustomerListView(RoleRequiredMixin, ListView):
    model = Customer
    template_name = 'core/customer_list.html'
    context_object_name = 'customers'
    allowed_roles = list(_SENSITIVE_ROLES)

    def get_queryset(self):
        return apply_user_scope(super().get_queryset(), self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        customers_qs = apply_user_scope(Customer.objects.all(), self.request.user)
        samples_qs = apply_user_scope(Sample.objects.all(), self.request.user)

        context['stats'] = {
            'total_customers': customers_qs.count(),
            'total_samples': samples_qs.count(),
            'pending_samples': samples_qs.filter(current_status='RECEIVED_FRONT_DESK').count(),
            'completed_samples': samples_qs.filter(current_status='REPORT_APPROVED').count(),
        }

        context['recent_samples'] = (
            apply_user_scope(
                Sample.objects.select_related('customer').order_by('-collection_datetime'),
                self.request.user,
            )[:5]
        )

        return context


class CustomerDetailView(RoleRequiredMixin, DetailView):
    model = Customer
    template_name = 'core/customer_detail.html'
    context_object_name = 'customer'
    allowed_roles = list(_SENSITIVE_ROLES)

    def get_queryset(self):
        return apply_user_scope(super().get_queryset(), self.request.user)


class CustomerCreateView(AuditMixin, FrontDeskRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'core/customer_form.html'
    success_url = reverse_lazy('core:customer_list')

    def form_valid(self, form):
        if not form.instance.created_by and self.request.user.is_authenticated:
            form.instance.created_by = self.request.user
        messages.success(self.request, f'Customer "{form.instance.name}" has been created successfully!')
        return super().form_valid(form)


class CustomerUpdateView(AuditMixin, FrontDeskRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'core/customer_form.html'

    def get_queryset(self):
        return apply_user_scope(super().get_queryset(), self.request.user)

    def get_success_url(self):
        return reverse_lazy('core:customer_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Customer "{form.instance.name}" has been updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context
