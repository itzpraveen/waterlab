import json
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from core.models import KeralaLocation


class Command(BaseCommand):
    help = "Seed Kerala districts → taluks → panchayats from the bundled JSON (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            default=os.path.join(settings.BASE_DIR, 'static', 'js', 'kerala_address_data.json'),
            help='Path to kerala_address_data.json'
        )

    def handle(self, *args, **opts):
        path = opts['path']
        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        created = 0
        skipped = 0

        with transaction.atomic():
            for district_name, taluks in data.items():
                district, d_created = KeralaLocation.objects.get_or_create(
                    name=district_name,
                    location_type='district',
                    defaults={'parent': None}
                )
                created += int(d_created)

                for taluk_name, bodies in taluks.items():
                    taluk, t_created = KeralaLocation.objects.get_or_create(
                        name=taluk_name,
                        location_type='taluk',
                        parent=district
                    )
                    created += int(t_created)

                    for lb_name in bodies:
                        # Treat entries as panchayat by default. Admins can refine later.
                        lb, lb_created = KeralaLocation.objects.get_or_create(
                            name=lb_name,
                            location_type='panchayat',
                            parent=taluk
                        )
                        created += int(lb_created)

        total = KeralaLocation.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Kerala locations seed complete. Created {created}, total rows now {total}."
        ))

