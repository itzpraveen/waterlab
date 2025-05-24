from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Create admin user for deployment'

    def handle(self, *args, **options):
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@waterlab.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'waterlab123')
        
        if not User.objects.filter(username=admin_username).exists():
            admin_user = User.objects.create_user(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                role='admin',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(
                self.style.SUCCESS(f'Admin user "{admin_username}" created successfully!')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Admin user "{admin_username}" already exists.')
            )