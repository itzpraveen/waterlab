from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pdfminer.high_level import extract_text
import re

from core.models import TestParameter, TestCategory, AuditTrail


HEADERS = {"parameters", "test method", "limit"}
UNIT_PATTERN = re.compile(r"(mg/L|ppm|NTU|µs/cm|Colonies|Absent/ml|°C|OC)")
RANGE_RE = re.compile(r"(?P<min>\d+(?:\.\d+)?)\s*[-–]\s*(?P<max>\d+(?:\.\d+)?)")
LTE_RE = re.compile(r"(?:≤|<)\s*(?P<max>\d+(?:\.\d+)?)")
GTE_RE = re.compile(r"(?:≥|>)\s*(?P<min>\d+(?:\.\d+)?)")


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


def _parse_limits(text: str):
    if not text:
        return None, None
    m = RANGE_RE.search(text)
    if m:
        return m.group('min'), m.group('max')
    m = LTE_RE.search(text)
    if m:
        return None, m.group('max')
    m = GTE_RE.search(text)
    if m:
        return m.group('min'), None
    return None, None


def parse_pdf(path: str) -> dict[str, list[dict]]:
    text = extract_text(path)
    lines = [l.strip() for l in (text or "").splitlines()]

    # Recognise three headings when present; if PDF only shows "Physical"
    # but contains chemical items in the same block, we'll split heuristically
    # after extraction (see below).
    categories = {"physical": "Physical", "chemical": "Chemical", "microbiology": "Microbiological"}
    params_by_cat: dict[str, list[dict]] = {}
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

        # Look ahead for method and limit hints within the next few lines
        method = None
        unit = None
        limit_text = None
        look = j
        steps = 0
        while look < len(lines) and steps < 6:
            token = lines[look].strip()
            if not token:
                look += 1; steps += 1; continue
            if _is_method_token(token) or token.startswith('IS'):
                method = token
            if UNIT_PATTERN.search(token) or any(ch.isdigit() for ch in token):
                # probable limit/units line
                limit_text = token
                # try to extract a unit keyword if present
                m = re.search(r"(mg/L|ppm|NTU|µs/cm|°C|OC)", token)
                if m:
                    unit = 'µS/cm' if m.group(0) in {'µs/cm','OC'} else m.group(0)
            # stop if we reached next obvious parameter start (capitalised word without numbers and not a method/limit)
            if (token and not any(ch.isdigit() for ch in token) and not token.startswith('IS') and not _is_method_token(token) and len(token.split())<=3 and token[0].isalpha()):
                # heuristic: might be a next parameter heading but we don't consume it here
                pass
            look += 1; steps += 1

        min_v = max_v = None
        if limit_text:
            min_s, max_s = _parse_limits(limit_text)
            min_v = float(min_s) if min_s else None
            max_v = float(max_s) if max_s else None

        if name and not any(ch.isdigit() for ch in name):
            params_by_cat.setdefault(cur, []).append({
                'name': name,
                'method': method,
                'unit': unit,
                'min': min_v,
                'max': max_v,
            })
        i = j

    # De-duplicate while preserving order
    for cat, items in list(params_by_cat.items()):
        seen = set(); uniq = []
        for item in items:
            n = item['name']
            key = n.casefold()
            if key in seen: continue
            seen.add(key); uniq.append(item)
        params_by_cat[cat] = uniq

    # If Chemical header was not explicitly found, split Physical items into
    # Physical vs Chemical using a conservative whitelist of physical-only
    # parameters observed in the document and standard practice.
    if ("Physical" in params_by_cat) and ("Chemical" not in params_by_cat):
        physical_only = {
            "Odour", "Color", "Colour", "Temperature", "pH",
            "Turbidity", "Total Dissolved Solids", "Electrical Conductivity",
            "ORP", "Total Suspended Solids"
        }
        phys_src = params_by_cat["Physical"]
        new_phys = []
        new_chem = []
        for item in phys_src:
            if item['name'] in physical_only:
                new_phys.append(item)
            else:
                new_chem.append(item)
        if new_chem:
            params_by_cat["Physical"] = new_phys
            params_by_cat["Chemical"] = new_chem

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
                for i, item in enumerate(items, start=1):
                    self.stdout.write(f"  {i*10:>3}: {item['name']} | {item.get('method') or '-'} | {item.get('min') or ''}-{item.get('max') or ''} {item.get('unit') or ''}")
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
                for item in items:
                    pname = item['name']
                    obj = TestParameter.objects.filter(name__iexact=pname).first()
                    if obj:
                        changed = False
                        if obj.category_obj_id != cat.id:
                            obj.category_obj = cat; changed = True
                        if obj.display_order != order:
                            obj.display_order = order; changed = True
                        # Update method/limits/units when available
                        if item.get('method') and obj.method != item['method']:
                            obj.method = item['method']; changed = True
                        if item.get('unit') and obj.unit != item['unit']:
                            obj.unit = item['unit']; changed = True
                        if (item.get('min') is not None) and (obj.min_permissible_limit != item['min']):
                            obj.min_permissible_limit = item['min']; changed = True
                        if (item.get('max') is not None) and (obj.max_permissible_limit != item['max']):
                            obj.max_permissible_limit = item['max']; changed = True
                        if changed:
                            obj.save()
                            updated_params += 1
                    else:
                        TestParameter.objects.create(
                            name=pname,
                            unit=item.get('unit') or '',
                            method=item.get('method'),
                            min_permissible_limit=item.get('min'),
                            max_permissible_limit=item.get('max'),
                            category_obj=cat,
                            display_order=order,
                        )
                        created_params += 1
                    order += 10

        self.stdout.write(self.style.SUCCESS(
            f"Categories created: {created_cats}; Parameters created: {created_params}; updated: {updated_params}"
        ))
