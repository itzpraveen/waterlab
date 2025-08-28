from django.core.management.base import BaseCommand

from core.services.parameters import seed_standard_parameters


class Command(BaseCommand):
    help = "Idempotently seed a standard set of TestParameter rows (safe, non-destructive)."

    def handle(self, *args, **options):
        created, skipped = seed_standard_parameters()
        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: created {created}, skipped {skipped} (already present)."
        ))

