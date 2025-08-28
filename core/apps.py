from django.apps import AppConfig


def _auto_seed_parameters():
    """Seed parameters once after migrations if empty.

    Kept lightweight and exception-safe to avoid blocking app startup.
    """
    from django.conf import settings
    from django.db.utils import OperationalError, ProgrammingError
    from .models import TestParameter
    from .services.parameters import seed_standard_parameters

    try:
        auto_seed = getattr(settings, 'AUTO_SEED_PARAMETERS', True)
        if not auto_seed:
            return
        if TestParameter.objects.exists():
            return
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
