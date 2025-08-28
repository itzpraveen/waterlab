from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Create admin user for deployment (safe, opt‑in).'

    def handle(self, *args, **options):
        # Opt-in switch: only run if explicitly requested
        if os.environ.get('CREATE_ADMIN', '0') not in ('1', 'true', 'TRUE', 'yes', 'YES'):
            self.stdout.write(self.style.WARNING('CREATE_ADMIN not set; skipping admin creation.'))
            return

        admin_username = os.environ.get('ADMIN_USERNAME')
        admin_email = os.environ.get('ADMIN_EMAIL')
        admin_password = os.environ.get('ADMIN_PASSWORD')

        # Require explicit, strong credentials
        if not admin_username or not admin_email or not admin_password:
            raise SystemExit('ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD must be set when CREATE_ADMIN=1')
        if len(admin_password) < 12:
            raise SystemExit('ADMIN_PASSWORD must be at least 12 characters long')

        if not User.objects.filter(username=admin_username).exists():
            User.objects.create_user(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                role='admin',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(self.style.SUCCESS(f'Admin user "{admin_username}" created successfully.'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin user "{admin_username}" already exists.'))
