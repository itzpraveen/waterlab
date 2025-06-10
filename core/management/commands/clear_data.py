from django.core.management.base import BaseCommand
from core.models import Sample, TestResult

class Command(BaseCommand):
    help = 'Clear all sample and test result data'

    def handle(self, *args, **options):
        self.stdout.write('Clearing all sample and test result data...')
        TestResult.objects.all().delete()
        Sample.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Data cleared successfully!'))
