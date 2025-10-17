from decimal import Decimal
from typing import Tuple

from django.db import transaction

from core.models import TestParameter, AuditTrail, TestCategory


def _standard_parameter_definitions():
    """Return a list of canonical, non-destructive parameter definitions.

    Keep this as the single source of truth so it can be reused by the
    view, a management command, or post-migrate hooks. Values are chosen to
    align with common drinking-water standards and can be extended safely.
    """
    definitions = [
        {"name": "pH", "unit": "pH", "min": Decimal("6.5"), "max": Decimal("8.5"), "method": "IS 3025 (Part 11)", "category": "Physical & Chemical"},
        {"name": "Total Dissolved Solids", "unit": "mg/L", "min": Decimal("0"), "max": Decimal("500"), "method": "IS 3025 (Part 16)", "category": "Physical & Chemical"},
        {"name": "Turbidity", "unit": "NTU", "min": Decimal("0"), "max": Decimal("1"), "method": "IS 3025 (Part 10)", "category": "Physical & Chemical"},
        {"name": "Total Hardness", "unit": "mg/L as CaCO3", "min": Decimal("0"), "max": Decimal("200"), "method": "IS 3025", "category": "Physical & Chemical"},
        {"name": "Chlorides", "unit": "mg/L", "min": Decimal("0"), "max": Decimal("250"), "method": "IS 3025 (Part 32)", "category": "Physical & Chemical"},
        {"name": "Total Alkalinity", "unit": "mg/L as CaCO3", "min": Decimal("0"), "max": Decimal("200"), "method": "IS 3025", "category": "Physical & Chemical"},
        {"name": "Iron", "unit": "mg/L", "min": Decimal("0"), "max": Decimal("0.3"), "method": "IS 3025 (Part 53)", "category": "Physical & Chemical"},
        {"name": "Fluoride", "unit": "mg/L", "min": Decimal("0"), "max": Decimal("1.0"), "method": "IS 3025 (Part 60)", "category": "Physical & Chemical"},
        {"name": "Nitrate", "unit": "mg/L", "min": Decimal("0"), "max": Decimal("45"), "method": "IS 3025 (Part 34)", "category": "Physical & Chemical"},
        {"name": "Residual Chlorine", "unit": "mg/L", "min": Decimal("0.2"), "max": Decimal("1.0"), "method": "IS 3025 (Part 26)", "category": "Physical & Chemical"},
        {"name": "Total Coliform", "unit": "CFU/100mL", "min": Decimal("0"), "max": Decimal("0"), "method": "IS 5401 (Part 1)", "category": "Microbiological"},
        {"name": "E. Coli", "unit": "CFU/100mL", "min": Decimal("0"), "max": Decimal("0"), "method": "IS 5887 (Part 1)", "category": "Microbiological"},
    ]

    for index, definition in enumerate(definitions, start=1):
        definition['order'] = index * 10

    return definitions


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
                # Update core metadata but NEVER override user-defined ordering.
                # Re-seeding should be safe to run without undoing manual tweaks.
                updated = False
                if existing.unit != p["unit"]:
                    existing.unit = p["unit"]; updated = True
                if existing.method != p.get("method"):
                    existing.method = p.get("method"); updated = True
                if existing.min_permissible_limit != p.get("min"):
                    existing.min_permissible_limit = p.get("min"); updated = True
                if existing.max_permissible_limit != p.get("max"):
                    existing.max_permissible_limit = p.get("max"); updated = True
                # Preserve existing.display_order unconditionally to respect admin customisation
                # (i.e., do not reset to the default seed order on re-run)

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
                display_order=p["order"],
                category_obj=TestCategory.objects.filter(name__iexact=p.get("category", "")).first(),
            )
            created += 1
            if user:
                AuditTrail.log_change(user=user, action='CREATE', instance=obj)

    return created, skipped
