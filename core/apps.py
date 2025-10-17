from django.apps import AppConfig


def _auto_seed_parameters():
    """Seed parameters once after migrations if empty.

    Kept lightweight and exception-safe to avoid blocking app startup.
    """
    from django.conf import settings
    from django.db.utils import OperationalError, ProgrammingError
    from .models import TestParameter, TestCategory
    from .services.parameters import seed_standard_parameters
    from .services.categories import seed_standard_categories

    try:
        auto_seed = getattr(settings, 'AUTO_SEED_PARAMETERS', True)
        # Skip during test runs to avoid interfering with isolated DBs
        import sys as _sys
        if (not auto_seed) or ('test' in _sys.argv):
            return
        # Ensure categories exist first, then parameters
        if not TestCategory.objects.exists():
            seed_standard_categories()
        if not TestParameter.objects.exists():
            seed_standard_parameters()
    except (OperationalError, ProgrammingError):
        # Database might not be ready during certain operations.
        pass


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Defer seeding until post_migrate to ensure DB tables exist
        from django.db.models.signals import post_migrate

        def _handler(**kwargs):
            _auto_seed_parameters()

        post_migrate.connect(_handler, sender=self)
