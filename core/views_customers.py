from django.contrib import messages
from django.db.models import Count, Q
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
    paginate_by = 25
    allowed_roles = list(_SENSITIVE_ROLES)

    def get_search_query(self):
        return (self.request.GET.get('q') or '').strip()

    def get_queryset(self):
        queryset = Customer.objects.annotate(sample_count=Count('samples')).order_by('name')
        query = self.get_search_query()
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone__icontains=query)
                | Q(house_name_door_no__icontains=query)
                | Q(street_locality_landmark__icontains=query)
                | Q(village_town_city__icontains=query)
                | Q(panchayat_municipality__icontains=query)
                | Q(taluk__icontains=query)
                | Q(district__icontains=query)
                | Q(pincode__icontains=query)
            )
        return apply_user_scope(queryset, self.request.user)

    def get_query_string(self):
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        encoded = query_params.urlencode()
        return f'&{encoded}' if encoded else ''

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

        page_obj = context.get('page_obj')
        context['search_query'] = self.get_search_query()
        context['query_string'] = self.get_query_string()
        context['show_reset_filters'] = bool(context['search_query'])

        if page_obj:
            context['customer_count'] = page_obj.paginator.count
            context['page_start_index'] = page_obj.start_index()
            context['page_end_index'] = page_obj.end_index()
        else:
            context['customer_count'] = len(context.get('customers', []))
            context['page_start_index'] = 0
            context['page_end_index'] = context['customer_count']

        return context


class CustomerDetailView(RoleRequiredMixin, DetailView):
    model = Customer
    template_name = 'core/customer_detail.html'
    context_object_name = 'customer'
    allowed_roles = list(_SENSITIVE_ROLES)

    def get_queryset(self):
        return apply_user_scope(super().get_queryset(), self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sample_history_qs = apply_user_scope(
            Sample.objects.filter(customer=self.object).only(
                'sample_id',
                'display_id',
                'customer_id',
                'collection_datetime',
                'current_status',
            ).order_by('-collection_datetime'),
            self.request.user,
        )
        context['sample_history_count'] = sample_history_qs.count()
        context['sample_history'] = sample_history_qs[:25]
        return context


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
