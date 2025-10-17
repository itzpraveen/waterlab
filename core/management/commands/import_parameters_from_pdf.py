from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pdfminer.high_level import extract_text
import re

from core.models import TestParameter, TestCategory, AuditTrail


HEADERS = {"parameters", "test method", "limit"}
UNIT_PATTERN = re.compile(r"(mg/L|ppm|NTU|µs/cm|Colonies|Absent/ml|<|OC)")


NAME_ALIASES = {
    # Physical & Chemical
    "tds": "Total Dissolved Solids",
    "e. conductivity": "Electrical Conductivity",
    "oxidation reduction potential": "ORP",
    "total suspended solids chemical": "Total Suspended Solids",
    "rfc": "Residual Chlorine",
    # Microbiological
    "e coli": "E. Coli",
    "coliforms": "Total Coliform",
}

SKIP_TOKENS = {"agreeable", "colorless"}


def _is_method_token(s: str) -> bool:
    return s.startswith("IS") or s in {
        "Thermometer", "Microscopy", "In house", "standardized", "method", "Filtration", "Sedimentation"
    }


def _normalize_name(name: str) -> str:
    cleaned = name.replace("Odour-", "Odour").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    low = cleaned.lower()
    if low in NAME_ALIASES:
        return NAME_ALIASES[low]
    return cleaned


def parse_pdf(path: str) -> dict[str, list[str]]:
    text = extract_text(path)
    lines = [l.strip() for l in (text or "").splitlines()]

    categories = {"physical": "Physical & Chemical", "microbiology": "Microbiological"}
    params_by_cat: dict[str, list[str]] = {}
    cur: str | None = None

    i = 0
    while i < len(lines):
        s = lines[i].strip()
        low = s.lower()
        if not s or low in HEADERS:
            i += 1; continue
        if low in categories:
            cur = categories[low]
            i += 1; continue
        if cur is None:
            i += 1; continue
        if s.isdigit() or UNIT_PATTERN.search(s) or _is_method_token(s) or low in SKIP_TOKENS:
            i += 1; continue

        # Collect a short phrase until we hit units/methods
        parts = [s]
        j = i + 1
        while j < len(lines):
            t = lines[j].strip(); tl = t.lower()
            if (not t) or (tl in HEADERS) or (tl in categories) or t.isdigit() or _is_method_token(t) or UNIT_PATTERN.search(t) or (tl in SKIP_TOKENS):
                break
            if len(t.split()) <= 3:
                parts.append(t)
                j += 1
            else:
                break
        name = _normalize_name(" ".join(parts))
        if name and not any(ch.isdigit() for ch in name):
            params_by_cat.setdefault(cur, []).append(name)
        i = j

    # De-duplicate while preserving order
    for cat, items in list(params_by_cat.items()):
        seen = set(); uniq = []
        for n in items:
            key = n.casefold()
            if key in seen: continue
            seen.add(key); uniq.append(n)
        params_by_cat[cat] = uniq

    return params_by_cat


class Command(BaseCommand):
    help = "Import categories and parameters from a PDF and update existing records."

    def add_arguments(self, parser):
        parser.add_argument('--path', default='tmp/parameters pdf (1).pdf', help='Path to PDF file')
        parser.add_argument('--json', help='Optional JSON manifest (category -> [parameters]) to import instead of a PDF')
        parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')

    def handle(self, *args, **opts):
        path = opts['path']
        dry = opts['dry_run']

        if opts.get('json'):
            import json
            with open(opts['json'], 'r', encoding='utf-8') as f:
                parsed = json.load(f)
        else:
            try:
                parsed = parse_pdf(path)
            except Exception as exc:
                raise CommandError(f"Failed to parse PDF: {exc}")

        self.stdout.write(self.style.NOTICE(f"Parsed categories: {', '.join(parsed.keys())}"))
        created_params = 0
        updated_params = 0
        created_cats = 0

        if dry:
            for cat, items in parsed.items():
                self.stdout.write(self.style.HTTP_INFO(f"[{cat}] {len(items)} parameters"))
                for i, n in enumerate(items, start=1):
                    self.stdout.write(f"  {i*10:>3}: {n}")
            return

        with transaction.atomic():
            # Ensure categories (keep existing order when present; otherwise append)
            next_cat_order = (TestCategory.objects.order_by('-display_order').first().display_order or 0) if TestCategory.objects.exists() else 0
            for idx, (cat_name, items) in enumerate(parsed.items(), start=1):
                cat = TestCategory.objects.filter(name__iexact=cat_name).first()
                if not cat:
                    next_cat_order += 10
                    cat = TestCategory.objects.create(name=cat_name, display_order=next_cat_order)
                    created_cats += 1

                # Apply display order within each category and assign category_obj
                order = 10
                for pname in items:
                    obj = TestParameter.objects.filter(name__iexact=pname).first()
                    if obj:
                        changed = False
                        if obj.category_obj_id != cat.id:
                            obj.category_obj = cat; changed = True
                        if obj.display_order != order:
                            obj.display_order = order; changed = True
                        if changed:
                            obj.save(update_fields=['category_obj','display_order'])
                            updated_params += 1
                    else:
                        TestParameter.objects.create(name=pname, unit='', category_obj=cat, display_order=order)
                        created_params += 1
                    order += 10

        self.stdout.write(self.style.SUCCESS(
            f"Categories created: {created_cats}; Parameters created: {created_params}; updated: {updated_params}"
        ))
