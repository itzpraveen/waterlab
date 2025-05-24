from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import CustomUser

class Command(BaseCommand):
    help = 'Create dummy users for all roles in the Water Lab LIMS'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Define dummy users for each role
        dummy_users = [
            {
                'username': 'admin',
                'password': 'admin123',
                'email': 'admin@waterlab.com',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': 'admin',
                'department': 'Administration',
                'employee_id': 'EMP001',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'frontdesk',
                'password': 'front123',
                'email': 'frontdesk@waterlab.com',
                'first_name': 'Priya',
                'last_name': 'Nair',
                'role': 'frontdesk',
                'department': 'Front Office',
                'employee_id': 'EMP002',
                'phone': '9876543210',
            },
            {
                'username': 'labtech',
                'password': 'lab123',
                'email': 'labtech@waterlab.com',
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'role': 'lab',
                'department': 'Laboratory',
                'employee_id': 'EMP003',
                'phone': '9876543211',
            },
            {
                'username': 'consultant',
                'password': 'consult123',
                'email': 'consultant@waterlab.com',
                'first_name': 'Dr. Sunitha',
                'last_name': 'Menon',
                'role': 'consultant',
                'department': 'Quality Assurance',
                'employee_id': 'EMP004',
                'phone': '9876543212',
            },
            {
                'username': 'labtech2',
                'password': 'lab456',
                'email': 'labtech2@waterlab.com',
                'first_name': 'Anil',
                'last_name': 'Varma',
                'role': 'lab',
                'department': 'Laboratory',
                'employee_id': 'EMP005',
                'phone': '9876543213',
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for user_data in dummy_users:
            username = user_data.pop('username')
            password = user_data.pop('password')
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults=user_data
            )
            
            if created:
                user.set_password(password)
                user.save()
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created user: {username} (Role: {user.get_role_display()})')
                )
            else:
                # Update existing user
                for key, value in user_data.items():
                    setattr(user, key, value)
                user.set_password(password)
                user.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'🔄 Updated user: {username} (Role: {user.get_role_display()})')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Dummy users setup complete!')
        )
        self.stdout.write(f'📊 Created: {created_count} users')
        self.stdout.write(f'🔄 Updated: {updated_count} users')
        
        self.stdout.write(
            self.style.SUCCESS('\n🔑 Login Credentials:')
        )
        self.stdout.write('👨‍💼 Admin: admin / admin123')
        self.stdout.write('📋 Front Desk: frontdesk / front123') 
        self.stdout.write('🧬 Lab Tech 1: labtech / lab123')
        self.stdout.write('🧬 Lab Tech 2: labtech2 / lab456')
        self.stdout.write('👨‍⚕️ Consultant: consultant / consult123')
        
        self.stdout.write(
            self.style.SUCCESS('\n💡 All users can update their passwords after login!')
        )