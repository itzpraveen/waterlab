from django.core.management.base import BaseCommand
from core.models import TestParameter, TestResult
import re

class Command(BaseCommand):
    help = 'Create standard water test parameters based on the analysis report'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Deleting all existing test results...'))
        TestResult.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('All existing test results have been deleted.'))

        self.stdout.write(self.style.WARNING('Deleting all existing test parameters...'))
        TestParameter.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('All existing test parameters have been deleted.'))

        # Create parent categories
        physical_params = TestParameter.objects.create(name='Physical Parameters', category='A')
        chemical_params = TestParameter.objects.create(name='Chemical Parameters', category='B')
        bacteriological_params = TestParameter.objects.create(name='Bacteriological Parameters', category='C')

        # Sub-categories for Bacteriological Parameters
        pigment_producing = TestParameter.objects.create(name='Pigment producing bacteria', parent=bacteriological_params)
        other_pathogenic = TestParameter.objects.create(name='Other pathogenic bacteria', parent=bacteriological_params)
        fungal_contamination = TestParameter.objects.create(name='Fungal contamination', parent=bacteriological_params)
        protozoa = TestParameter.objects.create(name='Protozoa', parent=bacteriological_params)

        test_parameters_data = [
            # Physical Parameters
            {'name': 'Odour', 'method': 'IS 3025 (Part 05)', 'limit': 'Agreeable', 'parent': physical_params},
            {'name': 'Colour', 'method': 'IS 3025 (Part 04)', 'limit': 'Colourless', 'parent': physical_params},
            {'name': 'Taste', 'method': 'IS 3025 (Part 08)', 'limit': 'Agreeable', 'parent': physical_params},
            {'name': 'Temperature', 'method': 'Thermometry', 'limit': '-', 'unit': '°C', 'parent': physical_params},
            {'name': 'pH', 'method': 'IS 3025 (Part11)', 'limit': '6.5 to 8.5', 'parent': physical_params},
            {'name': 'Turbidity', 'method': 'IS 3025 (Part 10)', 'limit': '<5 NTU', 'parent': physical_params},
            {'name': 'Total Dissolved Solids (TDS)', 'method': 'IS 3025 (Part 16)', 'limit': '500.57 ppm', 'parent': physical_params},
            {'name': 'Electrical Conductivity(EC)', 'method': 'IS 3025 (Part 16)', 'limit': '800 µS/cm', 'parent': physical_params},
            {'name': 'Oxidation Reduction Potential(ORP)', 'method': 'IS 3025 (Part 11)', 'limit': '< 0', 'unit': 'mv', 'parent': physical_params},
            {'name': 'Sedimentation', 'method': 'In-house Standardized Method (ISM)', 'limit': '--', 'parent': physical_params},
            {'name': 'Total Suspended Solids', 'method': 'Filtration Method', 'limit': '--', 'unit': 'mg/l', 'parent': physical_params},

            # Chemical Parameters
            {'name': 'Acidity', 'method': 'IS 3025', 'limit': '--', 'unit': 'mg/L', 'parent': chemical_params},
            {'name': 'Total Hardness', 'method': 'IS 3025', 'limit': '200.22 ppm', 'parent': chemical_params},
            {'name': 'Hardness as CaCO3', 'method': 'IS 3025 (Part 21)', 'limit': '200 mg/l', 'parent': chemical_params},
            {'name': 'Chloride (as Cl)', 'method': 'IS 3025 (Part 32)', 'limit': '250 mg/L', 'parent': chemical_params},
            {'name': 'Fluoride (as F)', 'method': 'IS 3025 (Part 60)', 'limit': '1.2 ppm', 'parent': chemical_params},
            {'name': 'Iron (as Fe)', 'method': 'IS 3025 (Part 53)', 'limit': '0.3 ppm', 'parent': chemical_params},
            {'name': 'Nitrate (as NO₃-)', 'method': 'IS 3025 (Part 34)', 'limit': '45 ppm', 'parent': chemical_params},
            {'name': 'Residual Free Chlorine', 'method': 'Iodometric Methods Ref: IS 3025(Part – 26)', 'limit': '0.2 mg/l', 'parent': chemical_params},
            {'name': 'Barium', 'method': 'Volumetric Ref:IS13428AnnexF', 'limit': '0.7 mg/l', 'parent': chemical_params},
            {'name': 'Copper', 'method': 'Neocuproine Ref: IS 3025(Part42)', 'limit': '0.05 mg/l', 'parent': chemical_params},
            {'name': 'Manganese', 'method': 'Colour comparison Ref: IS 3025(Part – 59)', 'limit': '0.1 mg/l', 'parent': chemical_params},
            {'name': 'Nitrite', 'method': 'Spectrometric Ref: IS 3025(Part – 34)', 'limit': '0.02 mg/l', 'parent': chemical_params},
            {'name': 'Aluminium', 'method': 'Eriochrome Cyanine R Dye Method Ref: IS 3025(Part – 55)', 'limit': '0.03 mg/l', 'parent': chemical_params},
            {'name': 'Calcium', 'method': 'EDTAMethod Ref: IS 3025(Part – 40)', 'limit': '75 mg/l', 'parent': chemical_params},
            {'name': 'Magnesium', 'method': 'Volumetric Ref: IS 3025(Part – 46)', 'limit': '30 mg/L', 'parent': chemical_params},
            {'name': 'Sulphate (as SO₄)', 'method': 'IS 3025 (Part 24)', 'limit': '200 mg/L', 'parent': chemical_params},
            {'name': 'Sulphide (as H₂S)', 'method': 'IS 3025 (Part 29)', 'limit': '0.05 mg/L', 'parent': chemical_params},
            {'name': 'Phosphate (as PO₄)', 'method': 'EPA 365.1', 'limit': '0.05 mg/L', 'parent': chemical_params},
            {'name': 'Ammonia', 'method': 'IS 3025 (Part 34)', 'limit': '0.03 mg/L', 'parent': chemical_params},
            {'name': 'Chromium(as Cr)', 'method': 'IS 3025 (Part 52)', 'limit': '0.05 mg/L', 'parent': chemical_params},

            # Bacteriological Parameters
            {'name': 'Total Plate Count/ Total Microbial Load', 'method': 'IS 5402:2012', 'limit': '20°C - <100 cfu/ml, 37°C - <20 cfu/ml', 'parent': bacteriological_params},
            {'name': 'Total coliforms', 'method': 'IS 15185:2016', 'limit': 'Absent/ml', 'parent': bacteriological_params},
            {'name': 'Fecal coliforms: E. coli', 'method': 'IS 1622:1981', 'limit': 'Absent/ml', 'parent': bacteriological_params},
            {'name': 'Enterobacter', 'method': 'IS 15186:2002', 'limit': 'Absent/ml', 'parent': bacteriological_params},
            {'name': 'Klebsiella sp.', 'method': 'Culture Characteristics', 'limit': 'Absent/ml', 'parent': bacteriological_params},
            {'name': 'Salmonella sp.', 'method': 'IS15187:2002', 'limit': 'Absent/ml', 'parent': bacteriological_params},
            {'name': 'Shigella sp.', 'method': 'Culture Characteristics', 'limit': 'Absent/ml', 'parent': bacteriological_params},
            
            # Pigment producing bacteria
            {'name': 'Chromobacterium violaceum', 'method': 'Culture characteristics', 'limit': 'Absent/ml', 'parent': pigment_producing},
            {'name': 'Serratia sp.', 'method': 'Culture characteristics', 'limit': 'Absent/ml', 'parent': pigment_producing},
            {'name': 'Flavobacterium sp.', 'method': 'Culture characteristics', 'limit': 'Absent/ml', 'parent': pigment_producing},

            # Other pathogenic bacteria
            {'name': 'Staphylococcus aureus', 'method': 'IS 5887:1976 Part II', 'limit': 'Absent/ml', 'parent': other_pathogenic},
            {'name': 'Proteus sp.', 'method': 'Culture Characteristics', 'limit': 'Absent/ml', 'parent': other_pathogenic},
            {'name': 'Pseudomonas sp.', 'method': 'Culture Characteristics', 'limit': 'Absent/ml', 'parent': other_pathogenic},
            {'name': 'Bacillus sp.', 'method': 'Culture Characteristics', 'limit': 'Absent/ml', 'parent': other_pathogenic},
            {'name': 'Vibrio sp.', 'method': 'Culture Characteristics', 'limit': 'Absent/ml', 'parent': other_pathogenic},
            {'name': 'Iron oxidizing bacteria', 'method': 'Culture Characteristics', 'limit': 'Absent/ml', 'parent': other_pathogenic},
            {'name': 'Actinomycetes', 'method': 'Culture Characteristics', 'limit': 'Absent/ml', 'parent': other_pathogenic},

            # Fungal contamination
            {'name': 'Aspergillus sp.', 'method': 'Culture Characteristics', 'limit': 'Absent/ml', 'parent': fungal_contamination},
            {'name': 'Yeast', 'method': 'Culture Characteristics', 'limit': 'Absent/ml', 'parent': fungal_contamination},

            # Protozoa
            {'name': 'Entamoeba sp.', 'method': 'Microscopy', 'limit': 'Absent/ml', 'parent': protozoa},
            {'name': 'Giardia sp.', 'method': 'Microscopy', 'limit': 'Absent/ml', 'parent': protozoa},
            {'name': 'Algae/ Microscopic Phytoplankton', 'method': 'Microscopy', 'limit': 'Absent/ml', 'parent': protozoa},
        ]

        created_count = 0
        for param_data in test_parameters_data:
            defaults = {
                'method': param_data['method'],
                'parent': param_data.get('parent'),
            }

            limit_str = param_data['limit']
            unit = param_data.get('unit', '')
            min_limit = None
            max_limit = None
            max_limit_display = None

            # Regex to parse limit string
            range_match = re.match(r'([\d\.]+) to ([\d\.]+)', limit_str)
            less_than_match = re.match(r'<([\d\.]+)', limit_str)
            numeric_match = re.match(r'([\d\.]+)', limit_str)

            if range_match:
                min_limit = float(range_match.group(1))
                max_limit = float(range_match.group(2))
                unit_search = re.search(r'[a-zA-Z/]+', limit_str.split('to')[-1])
                if unit_search:
                    unit = unit_search.group(0)
            elif less_than_match:
                max_limit = float(less_than_match.group(1))
                unit_search = re.search(r'[a-zA-Z/µS]+.*', limit_str)
                if unit_search:
                    unit = unit_search.group(0).strip()
            elif numeric_match and any(char.isdigit() for char in limit_str):
                max_limit = float(numeric_match.group(1))
                unit_search = re.search(r'[a-zA-Z/µS]+.*', limit_str)
                if unit_search:
                    unit = unit_search.group(0).strip()

            if 'Absent/ml' in limit_str:
                max_limit_display = 'Absent/ml'
                if not unit:
                    unit = 'Absent/ml'
            
            if 'Agreeable' in limit_str or 'Colourless' in limit_str:
                unit = limit_str
                if not max_limit_display:
                    max_limit_display = limit_str

            if param_data['name'] == 'pH':
                unit = 'pH'

            defaults['unit'] = unit
            defaults['min_permissible_limit'] = min_limit
            defaults['max_permissible_limit'] = max_limit
            defaults['max_limit_display'] = max_limit_display

            parameter, created = TestParameter.objects.update_or_create(
                name=param_data['name'],
                defaults=defaults
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Created parameter: {parameter.name}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n🧪 Test parameters setup complete! Created {created_count} new parameters.'))
