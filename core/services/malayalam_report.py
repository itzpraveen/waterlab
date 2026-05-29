"""Render the Malayalam remarks page and merge it onto the main report PDF.

The primary report is produced with ReportLab, which cannot shape Malayalam
script. The Malayalam summary page is therefore rendered separately with
WeasyPrint (HTML -> PDF with proper complex-script shaping) and appended to the
ReportLab output with pypdf.

Every step degrades gracefully: if WeasyPrint or pypdf is unavailable (e.g. the
native pango/cairo libraries are missing in a deployment), the Malayalam page is
quietly skipped and the English-only report is returned unchanged.
"""

import logging
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders

logger = logging.getLogger(__name__)


def _file_uri(static_path: str, fallback_relative: str) -> str | None:
    """Resolve a static asset to a ``file://`` URI for WeasyPrint."""
    resolved = finders.find(static_path)
    if not resolved:
        candidate = Path(settings.BASE_DIR) / fallback_relative
        resolved = str(candidate) if candidate.exists() else None
    if not resolved or not Path(resolved).exists():
        return None
    return Path(resolved).as_uri()


def render_malayalam_remarks_pdf(*, sample, remarks_ml, recommendations_ml, branded=True):
    """Render a single-page Malayalam remarks PDF, or ``None`` when not possible.

    Returns ``None`` when there is no Malayalam content to show or when WeasyPrint
    cannot be imported / fails to render.
    """
    remarks_ml = (remarks_ml or '').strip()
    recommendations_ml = (recommendations_ml or '').strip()
    if not remarks_ml and not recommendations_ml:
        return None

    try:
        from weasyprint import HTML
    except Exception:
        logger.warning(
            "WeasyPrint is unavailable; skipping the Malayalam report page. "
            "Install weasyprint and its native dependencies (pango, cairo) to enable it.",
            exc_info=True,
        )
        return None

    from django.template.loader import render_to_string

    from core.services.ai_remarks import bullet_items

    context = {
        'branded': branded,
        'sample_code': sample.display_id or str(sample.sample_id),
        'report_number': getattr(sample, 'report_number_with_revision', '') or '',
        'customer_name': getattr(sample.customer, 'name', '') or '',
        'remarks_ml': remarks_ml,
        'recommendations_ml': recommendations_ml,
        'remarks_ml_items': bullet_items(remarks_ml),
        'recommendations_ml_items': bullet_items(recommendations_ml),
        'font_regular_url': _file_uri(
            'fonts/NotoSansMalayalam-Regular.ttf', 'static/fonts/NotoSansMalayalam-Regular.ttf'
        ),
        'font_bold_url': _file_uri(
            'fonts/NotoSansMalayalam-Bold.ttf', 'static/fonts/NotoSansMalayalam-Bold.ttf'
        ),
        'background_url': _file_uri(
            'report_templates/biofix_wl_template_page.png',
            'static/report_templates/biofix_wl_template_page.png',
        ) if branded else None,
        'watermark_url': _file_uri(
            'report_templates/biofix_wl_watermark.png',
            'static/report_templates/biofix_wl_watermark.png',
        ) if branded else None,
    }

    try:
        html_string = render_to_string('core/report_malayalam_page.html', context)
        return HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf()
    except Exception:
        logger.exception("Failed to render the Malayalam report page with WeasyPrint.")
        return None


def append_pdf_pages(base_pdf_bytes: bytes, extra_pdf_bytes: bytes) -> bytes:
    """Append ``extra_pdf_bytes`` pages after ``base_pdf_bytes``.

    Returns the original ``base_pdf_bytes`` unchanged if merging is not possible,
    so the core report is never lost to a merge failure.
    """
    if not extra_pdf_bytes:
        return base_pdf_bytes

    try:
        from pypdf import PdfReader, PdfWriter
    except Exception:
        logger.warning("pypdf is unavailable; cannot append the Malayalam page.", exc_info=True)
        return base_pdf_bytes

    try:
        writer = PdfWriter()
        for source in (base_pdf_bytes, extra_pdf_bytes):
            reader = PdfReader(BytesIO(source))
            for page in reader.pages:
                writer.add_page(page)
        output = BytesIO()
        writer.write(output)
        return output.getvalue()
    except Exception:
        logger.exception("Failed to merge the Malayalam page into the report PDF.")
        return base_pdf_bytes
