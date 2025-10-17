from typing import Tuple

from django.db import transaction

from core.models import TestCategory, AuditTrail


def _standard_categories():
    return [
        {"name": "Physical & Chemical", "display_order": 0},
        {"name": "Microbiological", "display_order": 1},
        {"name": "Solution", "display_order": 2},
    ]


def seed_standard_categories(user=None) -> Tuple[int, int]:
    created = 0
    skipped = 0
    with transaction.atomic():
        for c in _standard_categories():
            existing = TestCategory.objects.filter(name__iexact=c["name"]).first()
            if existing:
                updated = False
                if existing.display_order != c["display_order"]:
                    existing.display_order = c["display_order"]; updated = True
                if updated:
                    existing.save()
                skipped += 1
                continue
            obj = TestCategory.objects.create(name=c["name"], display_order=c["display_order"])
            created += 1
            if user:
                AuditTrail.log_change(user=user, action='CREATE', instance=obj)
    return created, skipped

