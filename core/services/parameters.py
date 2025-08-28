from decimal import Decimal
from typing import Tuple

from django.db import transaction

from core.models import TestParameter, AuditTrail


def _standard_parameter_definitions():
    """Return a list of canonical, non-destructive parameter definitions.

    Keep this as the single source of truth so it can be reused by the
    view, a management command, or post-migrate hooks. Values are chosen to
    align with common drinking-water standards and can be extended safely.
    """
    return [
        {"name": "pH", "unit": "pH", "min": Decimal("6.5"), "max": Decimal("8.5"), "method": "IS 3025 (Part 11)"},
        {"name": "Total Dissolved Solids", "unit": "mg/L", "min": Decimal("0"), "max": Decimal("500"), "method": "IS 3025 (Part 16)"},
        {"name": "Turbidity", "unit": "NTU", "min": Decimal("0"), "max": Decimal("1"), "method": "IS 3025 (Part 10)"},
        {"name": "Total Hardness", "unit": "mg/L as CaCO3", "min": Decimal("0"), "max": Decimal("200"), "method": "IS 3025"},
        {"name": "Chlorides", "unit": "mg/L", "min": Decimal("0"), "max": Decimal("250"), "method": "IS 3025 (Part 32)"},
        {"name": "Total Alkalinity", "unit": "mg/L as CaCO3", "min": Decimal("0"), "max": Decimal("200"), "method": "IS 3025"},
        {"name": "Iron", "unit": "mg/L", "min": Decimal("0"), "max": Decimal("0.3"), "method": "IS 3025 (Part 53)"},
        {"name": "Fluoride", "unit": "mg/L", "min": Decimal("0"), "max": Decimal("1.0"), "method": "IS 3025 (Part 60)"},
        {"name": "Nitrate", "unit": "mg/L", "min": Decimal("0"), "max": Decimal("45"), "method": "IS 3025 (Part 34)"},
        {"name": "Residual Chlorine", "unit": "mg/L", "min": Decimal("0.2"), "max": Decimal("1.0"), "method": "IS 3025 (Part 26)"},
        {"name": "Total Coliform", "unit": "CFU/100mL", "min": Decimal("0"), "max": Decimal("0"), "method": "IS 5401 (Part 1)"},
        {"name": "E. Coli", "unit": "CFU/100mL", "min": Decimal("0"), "max": Decimal("0"), "method": "IS 5887 (Part 1)"},
    ]


def seed_standard_parameters(user=None) -> Tuple[int, int]:
    """Idempotently create a common set of TestParameter rows.

    Returns (created_count, skipped_count).
    """
    created = 0
    skipped = 0

    with transaction.atomic():
        for p in _standard_parameter_definitions():
            # Case-insensitive existence check to avoid IntegrityErrors on unique name
            existing = TestParameter.objects.filter(name__iexact=p["name"]).first()
            if existing:
                # Optionally update metadata without changing identity
                updated = False
                if existing.unit != p["unit"]:
                    existing.unit = p["unit"]; updated = True
                if existing.method != p.get("method"):
                    existing.method = p.get("method"); updated = True
                if existing.min_permissible_limit != p.get("min"):
                    existing.min_permissible_limit = p.get("min"); updated = True
                if existing.max_permissible_limit != p.get("max"):
                    existing.max_permissible_limit = p.get("max"); updated = True
                if updated:
                    existing.save()
                skipped += 1
                continue

            obj = TestParameter.objects.create(
                name=p["name"],
                unit=p["unit"],
                method=p.get("method"),
                min_permissible_limit=p.get("min"),
                max_permissible_limit=p.get("max"),
            )
            created += 1
            if user:
                AuditTrail.log_change(user=user, action='CREATE', instance=obj)

    return created, skipped

