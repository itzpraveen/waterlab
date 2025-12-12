from django.views.generic import ListView

from .mixins import AdminRequiredMixin
from .models import AuditTrail, CustomUser


class AuditTrailView(AdminRequiredMixin, ListView):
    model = AuditTrail
    template_name = 'core/audit_trail.html'
    context_object_name = 'audit_trails'
    paginate_by = 50

    def get_queryset(self):
        qs = AuditTrail.objects.select_related('user').order_by('-timestamp')
        model = self.request.GET.get('model')
        action = self.request.GET.get('action')
        user_id = self.request.GET.get('user')
        object_id = self.request.GET.get('object_id')

        if model:
            qs = qs.filter(model_name=model)
        if action:
            qs = qs.filter(action=action)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if object_id:
            qs = qs.filter(object_id__icontains=object_id.strip())
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        filters = {
            'model': request.GET.get('model', ''),
            'action': request.GET.get('action', ''),
            'user': request.GET.get('user', ''),
            'object_id': request.GET.get('object_id', ''),
        }

        model_choices = (
            AuditTrail.objects.values_list('model_name', flat=True)
            .order_by('model_name')
            .distinct()
        )
        action_choices = [choice[0] for choice in AuditTrail.ACTION_CHOICES]
        users = (
            CustomUser.objects.filter(audit_logs__isnull=False)
            .distinct()
            .order_by('first_name', 'username')
        )

        querystring_without_page = ''
        if request.GET:
            qs = request.GET.copy()
            qs.pop('page', None)
            filtered = qs.urlencode()
            if filtered:
                querystring_without_page = '&' + filtered

        context.update({
            'model_choices': model_choices,
            'action_choices': action_choices,
            'users': users,
            'filters': filters,
            'querystring_without_page': querystring_without_page,
        })
        return context

