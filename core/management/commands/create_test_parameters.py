from django.core.management.base import BaseCommand
from core.models import TestParameter

class Command(BaseCommand):
    help = 'Create standard water test parameters'

    def handle(self, *args, **options):
        TestParameter.objects.all().delete()
        
        physical_params = TestParameter.objects.create(name='Physical Parameters', category='A')
        chemical_params = TestParameter.objects.create(name='Chemical Parameters', category='B')
        bacteriological_params = TestParameter.objects.create(name='Bacteriological Parameters', category='C')

        test_parameters = [
            {
                'name': 'Odour',
                'unit': 'Agreeable',
                'standard_method': 'IS 3025 (Part 05)',
                'parent': physical_params,
            },
            {
                'name': 'Colour',
                'unit': 'Colourless',
                'standard_method': 'IS 3025 (Part 04)',
                'parent': physical_params,
            },
            {
                'name': 'Taste',
                'unit': 'Agreeable',
                'standard_method': 'IS 3025 (Part 08)',
                'parent': physical_params,
            },
            {
                'name': 'Temperature',
                'unit': '°C',
                'standard_method': 'Thermometry',
                'parent': physical_params,
            },
            {
                'name': 'pH',
                'unit': 'pH units',
                'standard_method': 'IS 3025 (Part11)',
                'min_permissible_limit': 6.5,
                'max_permissible_limit': 8.5,
                'parent': physical_params,
            },
            {
                'name': 'Turbidity',
                'unit': 'NTU',
                'standard_method': 'IS 3025 (Part 10)',
                'max_permissible_limit': 5,
                'parent': physical_params,
            },
            {
                'name': 'Total Dissolved Solids (TDS)',
                'unit': 'ppm',
                'standard_method': 'IS 3025 (Part 16)',
                'max_permissible_limit': 500.57,
                'parent': physical_params,
            },
            {
                'name': 'Electrical Conductivity(EC)',
                'unit': 'µS/cm',
                'standard_method': 'IS 3025 (Part 11)',
                'max_permissible_limit': 800,
                'parent': physical_params,
            },
            {
                'name': 'Oxidation Reduction Potential(ORP)',
                'unit': 'mv',
                'standard_method': 'In-house Standardized Method (ISM)',
                'parent': physical_params,
            },
            {
                'name': 'Sedimentation',
                'unit': '',
                'standard_method': 'Filtration Method',
                'parent': physical_params,
            },
            {
                'name': 'Total Suspended Solids',
                'unit': 'mg/l',
                'standard_method': 'IS 3025',
                'parent': physical_params,
            },
            {
                'name': 'Acidity',
                'unit': 'mg/L',
                'standard_method': 'IS 3025',
                'parent': chemical_params,
            },
            {
                'name': 'Total Hardness',
                'unit': 'ppm',
                'standard_method': 'IS 3025',
                'max_permissible_limit': 200.22,
                'parent': chemical_params,
            },
            {
                'name': 'Hardness as CaCO3',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 (Part 21)',
                'max_permissible_limit': 200,
                'parent': chemical_params,
            },
            {
                'name': 'Chloride (as Cl)',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 (Part 32)',
                'max_permissible_limit': 250,
                'parent': chemical_params,
            },
            {
                'name': 'Fluoride (as F)',
                'unit': 'ppm',
                'standard_method': 'IS 3025 (Part 60)',
                'max_permissible_limit': 1.2,
                'parent': chemical_params,
            },
            {
                'name': 'Iron (as Fe)',
                'unit': 'ppm',
                'standard_method': 'IS 3025 (Part 53)',
                'max_permissible_limit': 0.3,
                'parent': chemical_params,
            },
            {
                'name': 'Nitrate (as NO3-)',
                'unit': 'ppm',
                'standard_method': 'IS 3025 (Part 34)',
                'max_permissible_limit': 45,
                'parent': chemical_params,
            },
            {
                'name': 'Residual Free Chlorine',
                'unit': 'mg/l',
                'standard_method': 'Iodometric Methods Ref: IS 3025(Part – 26)',
                'max_permissible_limit': 0.2,
                'parent': chemical_params,
            },
            {
                'name': 'Barium',
                'unit': 'mg/l',
                'standard_method': 'Volumetric Ref:IS13428AnnexF',
                'max_permissible_limit': 0.7,
                'parent': chemical_params,
            },
            {
                'name': 'Copper',
                'unit': 'mg/l',
                'standard_method': 'Neocuproine Ref: IS 3025(Part42)',
                'max_permissible_limit': 0.05,
                'parent': chemical_params,
            },
            {
                'name': 'Manganese',
                'unit': 'mg/l',
                'standard_method': 'Colour comparison Ref: IS 3025(Part – 59)',
                'max_permissible_limit': 0.1,
                'parent': chemical_params,
            },
            {
                'name': 'Nitrite',
                'unit': 'Mg/l',
                'standard_method': 'Spectrometric Ref: IS 3025(Part – 34)',
                'max_permissible_limit': 0.02,
                'parent': chemical_params,
            },
            {
                'name': 'Aluminium',
                'unit': 'Mg/l',
                'standard_method': 'Eriochrome Cyanine R Dye Method Ref: IS 3025(Part – 55)',
                'max_permissible_limit': 0.03,
                'parent': chemical_params,
            },
            {
                'name': 'Calcium',
                'unit': 'mg/l',
                'standard_method': 'EDTAMethod Ref: IS 3025(Part – 40)',
                'max_permissible_limit': 75,
                'parent': chemical_params,
            },
            {
                'name': 'Magnesium',
                'unit': 'mg/L',
                'standard_method': 'Volumetric Ref: IS 3025(Part – 46)',
                'max_permissible_limit': 30,
                'parent': chemical_params,
            },
            {
                'name': 'Sulphate (as SO4)',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 (Part 24)',
                'max_permissible_limit': 200,
                'parent': chemical_params,
            },
            {
                'name': 'Sulphide (as H2S)',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 (Part 29)',
                'max_permissible_limit': 0.05,
                'parent': chemical_params,
            },
            {
                'name': 'Phosphate (as PO4)',
                'unit': 'mg/L',
                'standard_method': 'EPA 365.1',
                'max_permissible_limit': 0.05,
                'parent': chemical_params,
            },
            {
                'name': 'Ammonia',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 (Part 34)',
                'max_permissible_limit': 0.03,
                'parent': chemical_params,
            },
            {
                'name': 'Chromium(as Cr)',
                'unit': 'mg/L',
                'standard_method': 'IS 3025 (Part 52)',
                'max_permissible_limit': 0.05,
                'parent': chemical_params,
            },
            {
                'name': 'Total Plate Count/ Total Microbial Load',
                'unit': 'cfu/ml',
                'standard_method': 'IS 5402:2012',
                'parent': bacteriological_params,
            },
            {
                'name': 'Total coliforms',
                'unit': 'Absent/ml',
                'standard_method': 'IS 15185:2016',
                'parent': bacteriological_params,
            },
            {
                'name': 'Fecal coliforms: E. coli',
                'unit': 'Absent/ml',
                'standard_method': 'IS 1622:1981',
                'parent': bacteriological_params,
            },
            {
                'name': 'Enterobacter',
                'unit': 'Absent/ml',
                'standard_method': 'IS 15186:2002',
                'parent': bacteriological_params,
            },
            {
                'name': 'Klebsiella sp.',
                'unit': 'Absent/ml',
                'standard_method': 'Culture Characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Salmonella sp.',
                'unit': 'Absent/ml',
                'standard_method': 'IS15187:2002',
                'parent': bacteriological_params,
            },
            {
                'name': 'Shigella sp.',
                'unit': 'Absent/ml',
                'standard_method': 'Culture Characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Chromobacterium violaceum',
                'unit': 'Absent/ml',
                'standard_method': 'Culture characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Serratia sp.',
                'unit': 'Absent/ml',
                'standard_method': 'Culture characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Flavobacterium sp.',
                'unit': 'Absent/ml',
                'standard_method': 'Culture characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Staphylococcus aureus',
                'unit': 'Absent/ml',
                'standard_method': 'IS 5887:1976 Part II',
                'parent': bacteriological_params,
            },
            {
                'name': 'Proteus sp.',
                'unit': 'Absent/ml',
                'standard_method': 'Culture Characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Pseudomonas sp.',
                'unit': 'Absent/ml',
                'standard_method': 'Culture Characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Bacillus sp.',
                'unit': 'Absent/ml',
                'standard_method': 'Culture Characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Vibrio sp.',
                'unit': 'Absent/ml',
                'standard_method': 'Culture Characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Iron oxidizing bacteria',
                'unit': 'Absent/ml',
                'standard_method': 'Culture Characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Actinomycetes',
                'unit': 'Absent/ml',
                'standard_method': 'Culture Characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Aspergillus sp.',
                'unit': 'Absent/ml',
                'standard_method': 'Culture Characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Yeast',
                'unit': 'Absent/ml',
                'standard_method': 'Culture Characteristics',
                'parent': bacteriological_params,
            },
            {
                'name': 'Entamoeba sp.',
                'unit': 'Absent/ml',
                'standard_method': 'Microscopy',
                'parent': bacteriological_params,
            },
            {
                'name': 'Giardia sp.',
                'unit': 'Absent/ml',
                'standard_method': 'Microscopy',
                'parent': bacteriological_params,
            },
            {
                'name': 'Algae/ Microscopic Phytoplankton',
                'unit': 'Absent/ml',
                'standard_method': 'Microscopy',
                'parent': bacteriological_params,
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
