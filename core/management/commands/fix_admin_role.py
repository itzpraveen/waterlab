from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Fix admin user role case sensitivity issue'

    def handle(self, *args, **options):
        # Find users with uppercase ADMIN role and fix them
        admin_users = User.objects.filter(role='ADMIN')
        
        if admin_users.exists():
            for user in admin_users:
                user.role = 'admin'  # Change to lowercase
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Fixed role for user "{user.username}" from ADMIN to admin')
                )
        else:
            self.stdout.write(
                self.style.WARNING('No users with ADMIN role found.')
            )
        
        # Verify admin users now work
        admin_users = User.objects.filter(role='admin')
        self.stdout.write(
            self.style.SUCCESS(f'Found {admin_users.count()} admin users with correct role.')
        )
        
        for user in admin_users:
            self.stdout.write(f'  - {user.username}: is_admin()={user.is_admin()}')