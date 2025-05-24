from django.core.management.base import BaseCommand
from core.models import TestParameter

class Command(BaseCommand):
    help = 'Create standard water test parameters'

    def handle(self, *args, **options):
        test_parameters = [
            {
                'name': 'pH',
                'unit': 'pH units',
                'standard_method': 'IS 3025 Part-11',
                'min_permissible_limit': 6.5,
                'max_permissible_limit': 8.5,
            },
            {
                'name': 'Total Dissolved Solids',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 Part-16',
                'min_permissible_limit': 0,
                'max_permissible_limit': 500,
            },
            {
                'name': 'Turbidity',
                'unit': 'NTU',
                'standard_method': 'IS 3025 Part-10',
                'min_permissible_limit': 0,
                'max_permissible_limit': 1,
            },
            {
                'name': 'Total Hardness',
                'unit': 'mg/L as CaCO3',
                'standard_method': 'IS 3025 Part-21',
                'min_permissible_limit': 0,
                'max_permissible_limit': 200,
            },
            {
                'name': 'Chlorides',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 Part-32',
                'min_permissible_limit': 0,
                'max_permissible_limit': 250,
            },
            {
                'name': 'Total Alkalinity',
                'unit': 'mg/L as CaCO3',
                'standard_method': 'IS 3025 Part-23',
                'min_permissible_limit': 0,
                'max_permissible_limit': 200,
            },
            {
                'name': 'Iron',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 Part-53',
                'min_permissible_limit': 0,
                'max_permissible_limit': 0.3,
            },
            {
                'name': 'Fluoride',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 Part-57',
                'min_permissible_limit': 0,
                'max_permissible_limit': 1.0,
            },
            {
                'name': 'Nitrate',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 Part-34',
                'min_permissible_limit': 0,
                'max_permissible_limit': 45,
            },
            {
                'name': 'Residual Chlorine',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 Part-26',
                'min_permissible_limit': 0.2,
                'max_permissible_limit': 1.0,
            },
            {
                'name': 'Total Coliform',
                'unit': 'CFU/100mL',
                'standard_method': 'IS 1622',
                'min_permissible_limit': 0,
                'max_permissible_limit': 0,
            },
            {
                'name': 'E. Coli',
                'unit': 'CFU/100mL',
                'standard_method': 'IS 1622',
                'min_permissible_limit': 0,
                'max_permissible_limit': 0,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for param_data in test_parameters:
            parameter, created = TestParameter.objects.get_or_create(
                name=param_data['name'],
                defaults=param_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created parameter: {parameter.name}')
                )
            else:
                # Update existing parameter
                for key, value in param_data.items():
                    if key != 'name':
                        setattr(parameter, key, value)
                parameter.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'🔄 Updated parameter: {parameter.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🧪 Test parameters setup complete!')
        )
        self.stdout.write(f'📊 Created: {created_count} parameters')
        self.stdout.write(f'🔄 Updated: {updated_count} parameters')
        
        self.stdout.write(
            self.style.SUCCESS('\n💡 Test parameters are ready for use in sample testing!')
        )