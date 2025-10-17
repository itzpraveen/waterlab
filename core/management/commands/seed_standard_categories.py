from django.core.management.base import BaseCommand

from core.services.categories import seed_standard_categories


class Command(BaseCommand):
    help = "Idempotently seed a standard set of TestCategory rows (safe, non-destructive)."

    def handle(self, *args, **options):
        created, skipped = seed_standard_categories()
        self.stdout.write(self.style.SUCCESS(
            f"Category seed complete: created {created}, skipped {skipped} (already present)."
        ))

