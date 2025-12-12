import logging
import os
from collections import OrderedDict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import CustomPasswordChangeForm
from .models import Customer, Sample

logger = logging.getLogger(__name__)

# Roles allowed to view customer/sample/report data.
# Keep in sync with CustomUser.ROLE_CHOICES.
_SENSITIVE_ROLES = {
    'admin',
    'lab',
    'frontdesk',
    'consultant',
    'food_analyst',
    'bio_manager',
    'chem_manager',
    'solutions_manager',
}


def _user_can_view_sensitive_records(user) -> bool:
    """Gate access to customer/sample/report data until per-customer scoping exists."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return getattr(user, 'role', None) in _SENSITIVE_ROLES


def apply_user_scope(queryset, user):
    """Optionally restrict a queryset to the requesting user's records.

    When `ENFORCE_USER_SCOPING` is enabled in settings, front desk staff only
    see customers/samples they created. Admins and other staff remain global.
    """
    if not getattr(settings, 'ENFORCE_USER_SCOPING', False):
        return queryset
    if not user or not user.is_authenticated:
        return queryset.none()
    if getattr(user, 'is_superuser', False) or getattr(user, 'role', None) == 'admin':
        return queryset
    if getattr(user, 'role', None) == 'frontdesk':
        return queryset.filter(created_by=user)
    return queryset


def _choose_signer_with_signature(preferred, fallback):
    """Return preferred signer if they have a signature; otherwise use a fallback that does."""
    def _has_signature(user):
        if not user:
            return False
        try:
            return bool(getattr(user, 'signature_path', '') or '')
        except Exception:
            return False

    if _has_signature(preferred):
        return preferred
    if _has_signature(fallback):
        return fallback
    return preferred or fallback


def _format_error_message(base_message, exc):
    """Return debug-friendly error text without leaking details in production."""
    if settings.DEBUG:
        return f"{base_message} Details: {exc}"
    return base_message


def health_check(request):
    """Health check endpoint for load balancers and monitoring systems."""
    return HttpResponse("healthy", content_type="text/plain")


def debug_admin(request):
    """Debug endpoint to check admin user - REMOVE IN PRODUCTION."""
    if not settings.DEBUG:
        return HttpResponseNotFound()

    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        admin_users = User.objects.filter(is_superuser=True)
        user_info = [
            f"Username: {user.username}, Email: {user.email}, Role: {user.role}"
            for user in admin_users
        ]

        if admin_users.exists():
            return HttpResponse(
                f"Admin users found: {'; '.join(user_info)}",
                content_type="text/plain",
            )
        return HttpResponse("No admin users found", content_type="text/plain")
    except Exception as exc:
        logger.exception("Failed to gather admin user debug info")
        return HttpResponse(
            _format_error_message("Error retrieving admin users.", exc),
            content_type="text/plain",
            status=500,
        )


def create_admin_web(request):
    """Web endpoint to create admin user - REMOVE IN PRODUCTION."""
    if not settings.DEBUG:
        return HttpResponseNotFound()

    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        if User.objects.filter(username='admin').exists():
            return HttpResponse("Admin user already exists", content_type="text/plain")

        User.objects.create_user(
            username='admin',
            email='admin@waterlab.com',
            password='WaterLab2024!',
            role='admin',
            is_staff=True,
            is_superuser=True,
        )
        return HttpResponse(
            "Admin user created successfully! Username: admin, Password: WaterLab2024!",
            content_type="text/plain",
        )
    except Exception as exc:
        logger.exception("Failed to create admin user via debug endpoint")
        return HttpResponse(
            _format_error_message("Error creating admin user.", exc),
            content_type="text/plain",
            status=500,
        )


def debug_view(request):
    """Debug endpoint to check configuration and functionality."""
    if not settings.DEBUG:
        return HttpResponseNotFound()

    debug_info = [
        "=== Django Configuration Debug ===",
        f"DEBUG: {settings.DEBUG}",
        f"STATIC_URL: {settings.STATIC_URL}",
        f"STATIC_ROOT: {settings.STATIC_ROOT}",
        f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}",
        "\n=== Static Files Check ===",
    ]

    static_css_path = os.path.join(settings.STATIC_ROOT, 'css', 'style.css')
    debug_info.append(f"CSS file exists: {os.path.exists(static_css_path)}")

    debug_info.append("\n=== Database Check ===")
    try:
        debug_info.extend([
            f"Customers: {Customer.objects.count()}",
            f"Samples: {Sample.objects.count()}",
        ])
    except Exception as exc:
        logger.exception("Database check failed in debug_view")
        debug_info.append(
            _format_error_message("Database error encountered while generating debug info.", exc)
        )

    debug_info.append("\n=== User Session ===")
    debug_info.append(f"User authenticated: {request.user.is_authenticated}")
    if request.user.is_authenticated:
        debug_info.extend([
            f"Username: {request.user.username}",
            f"Role: {request.user.role}",
            f"Is admin: {request.user.is_admin()}",
        ])

    debug_info.append("\n=== Environment Variables ===")
    debug_info.append(f"DATABASE_URL set: {'DATABASE_URL' in os.environ}")
    debug_info.append(f"SECRET_KEY set: {'SECRET_KEY' in os.environ}")

    return HttpResponse("\n".join(debug_info), content_type="text/plain")


def form_test(request):
    """Simple form test to debug form submission issues."""
    if not settings.DEBUG:
        return HttpResponseNotFound()
    if request.method == 'POST':
        name = request.POST.get('name', 'No name provided')
        return HttpResponse(
            f"Form submitted successfully! Name: {name}",
            content_type="text/plain",
        )

    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Form Test</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body style="padding: 20px;">
        <h1>🧪 Water Lab LIMS - Form Test</h1>
        <form method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}">
            <div class="form-group">
                <label for="name">Test Name:</label>
                <input type="text" name="name" id="name" class="form-control" placeholder="Enter test name" required>
            </div>
            <button type="submit" class="btn btn-primary">Test Submit</button>
        </form>
        <p><a href="/debug/">View Debug Info</a></p>
    </body>
    </html>
    '''

    from django.middleware.csrf import get_token
    from django.template import Context, Template

    template = Template(html)
    context = Context({'csrf_token': get_token(request)})
    return HttpResponse(template.render(context))


def fix_admin_role_web(request):
    """Web endpoint to fix admin role case sensitivity - REMOVE IN PRODUCTION."""
    if not settings.DEBUG:
        return HttpResponseNotFound()

    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        admin_users = User.objects.filter(role='ADMIN')
        fixed_count = 0

        for user in admin_users:
            user.role = 'admin'
            user.save()
            fixed_count += 1

        admin_users_correct = User.objects.filter(role='admin')

        result = (
            f"Fixed {fixed_count} users with ADMIN role.\n"
            f"Found {admin_users_correct.count()} admin users with correct role.\n\n"
        )
        for user in admin_users_correct:
            result += f"- {user.username}: is_admin()={user.is_admin()}, role='{user.role}'\n"

        return HttpResponse(result, content_type="text/plain")
    except Exception as exc:
        logger.exception("Failed to normalize admin roles via debug endpoint")
        return HttpResponse(
            _format_error_message("Error normalizing admin roles.", exc),
            content_type="text/plain",
            status=500,
        )


def simple_home(request):
    """Simple home page to avoid redirect loops."""
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    return HttpResponse(
        '<h1>Water Lab LIMS</h1>'
        '<p><a href="/admin/">Admin Login</a></p>'
        '<p><a href="/accounts/login/">User Login</a></p>',
        content_type="text/html",
    )


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return '/dashboard/'


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'registration/password_change.html'
    success_url = reverse_lazy('core:password_change_done')

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been successfully updated!')
        return super().form_valid(form)


@login_required
def password_change_done(request):
    """Simple view to show password change success."""
    return render(request, 'registration/password_change_done.html')


def simple_dashboard(request):
    """Simple dashboard that works without redirect loops."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    context = {
        'user': request.user,
        'user_role': getattr(request.user, 'role', 'USER'),
        'total_customers': Customer.objects.count(),
        'total_samples': Sample.objects.count(),
    }

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Water Lab LIMS - Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ background: #007cba; color: white; padding: 20px; border-radius: 5px; }}
            .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
            .stat-box {{ background: #f5f5f5; padding: 15px; border-radius: 5px; flex: 1; }}
            .nav {{ margin: 20px 0; }}
            .nav a {{ background: #007cba; color: white; padding: 10px 15px; text-decoration: none; border-radius: 3px; margin-right: 10px; }}
            .nav a:hover {{ background: #005a87; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Water Lab LIMS Dashboard</h1>
            <p>Welcome, {request.user.username}! ({context['user_role']})</p>
        </div>

        <div class="stats">
            <div class="stat-box">
                <h3>Total Customers</h3>
                <p style="font-size: 24px; margin: 0;">{context['total_customers']}</p>
            </div>
            <div class="stat-box">
                <h3>Total Samples</h3>
                <p style="font-size: 24px; margin: 0;">{context['total_samples']}</p>
            </div>
        </div>

        <div class="nav">
            <a href="/admin/">Django Admin</a>
            <a href="/customers/">Customers</a>
            <a href="/samples/">Samples</a>
            <a href="/accounts/logout/">Logout</a>
        </div>

        <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin-top: 20px;">
            <h3>✅ Dashboard Working!</h3>
            <p>Your Water Lab LIMS is now running successfully. You can access all features through Django Admin or the navigation links above.</p>
        </div>
    </body>
    </html>
    """

    return HttpResponse(html_content)
