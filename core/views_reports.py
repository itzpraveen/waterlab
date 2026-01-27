import logging
import os
import re
from collections import OrderedDict
from decimal import Decimal
from html import escape
from io import BytesIO

from django.contrib import messages
from django.contrib.staticfiles import finders
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from reportlab.lib.utils import ImageReader

from .models import Invoice, LabProfile, Sample
from .views_common import (
    _choose_signer_with_signature,
    _format_error_message,
    _user_can_view_sensitive_records,
)

logger = logging.getLogger(__name__)


def download_sample_report_view(request, pk):
    sample = get_object_or_404(Sample, pk=pk)

    if not _user_can_view_sensitive_records(request.user):
        messages.error(request, "You do not have permission to download this report.")
        return redirect('core:dashboard')

    layout = (request.GET.get('layout') or 'branded').casefold()
    include_branding = layout != 'plain'
    background_template = None
    watermark_image = None
    if include_branding:
        template_path = finders.find('report_templates/biofix_wl_template_page.png')
        if template_path and os.path.exists(template_path):
            try:
                background_template = ImageReader(template_path)
            except Exception:
                logger.warning("Failed to load branded report template image from %s", template_path)
        watermark_path = finders.find('report_templates/biofix_wl_watermark.png')
        if watermark_path and os.path.exists(watermark_path):
            try:
                watermark_image = ImageReader(watermark_path)
            except Exception:
                logger.warning("Failed to load watermark image from %s", watermark_path)

    if sample.current_status not in ['REPORT_APPROVED', 'REPORT_SENT']:
        messages.error(request, "Report is not yet approved or available for download.")
        return redirect('core:sample_detail', pk=sample.pk)

    from django.conf import settings
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        BaseDocTemplate,
        CondPageBreak,
        Frame,
        Image,
        KeepTogether,
        ListFlowable,
        PageBreak,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buffer = BytesIO()

    def _register_body_fonts() -> tuple[str, str]:
        """Use built-in Helvetica so Latin text always renders (no custom fonts)."""
        return 'Helvetica', 'Helvetica-Bold'

    class ReportDocTemplate(BaseDocTemplate):
        def __init__(self, filename, include_branding=True, background_image=None, watermark_image=None, **kwargs):
            self.include_branding = include_branding
            self.background_image = background_image
            self.watermark_image = watermark_image
            super().__init__(filename, **kwargs)
            self.addPageTemplates([
                PageTemplate(
                    id='ReportPage',
                    frames=[Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='main_frame')],
                    onPage=self._maybe_header,
                    onPageEnd=self._maybe_footer,
                )
            ])

        def _maybe_header(self, canvas, doc):
            if self.include_branding:
                self.header(canvas, doc)

        def _maybe_footer(self, canvas, doc):
            if self.include_branding:
                self.footer(canvas, doc)

        def header(self, canvas, doc):
            canvas.saveState()
            page_width, page_height = doc.pagesize
            if self.background_image:
                canvas.drawImage(
                    self.background_image,
                    0,
                    0,
                    width=page_width,
                    height=page_height,
                    preserveAspectRatio=True,
                    mask='auto',
                )
                if self.watermark_image:
                    wm_width, wm_height = self.watermark_image.getSize()
                    target_width = page_width * 0.55
                    scale = target_width / wm_width
                    target_height = wm_height * scale
                    wm_x = (page_width - target_width) / 2
                    wm_y = (page_height - target_height) / 2 - 10 * mm
                    canvas.saveState()
                    try:
                        canvas.setFillAlpha(0.22)
                    except AttributeError:
                        pass
                    canvas.drawImage(
                        self.watermark_image,
                        wm_x,
                        wm_y,
                        width=target_width,
                        height=target_height,
                        mask='auto',
                        preserveAspectRatio=True,
                    )
                    canvas.restoreState()
            else:
                lab_settings = getattr(settings, 'WATERLAB_SETTINGS', {})
                profile = LabProfile.get_active()
                logo_path = profile.logo_path
                lab_name = (profile.name or lab_settings.get('LAB_NAME') or 'Biofix Laboratory').strip()
                lab_address = (profile.formatted_address or profile.address_line1 or lab_settings.get('LAB_ADDRESS') or '').strip()
                lab_phone = (profile.phone or lab_settings.get('LAB_PHONE') or '').strip()
                lab_email = (profile.email or lab_settings.get('LAB_EMAIL') or '').strip()
                lab_contact = profile.contact_line

                if logo_path and os.path.exists(logo_path):
                    logo = ImageReader(logo_path)
                    canvas.drawImage(
                        logo,
                        doc.leftMargin,
                        page_height - 38 * mm,
                        width=45 * mm,
                        height=17 * mm,
                        preserveAspectRatio=True,
                        mask='auto',
                    )

                draw_x = page_width - doc.rightMargin
                cursor_y = page_height - 28 * mm

                def _draw_line(value: str, font_name: str = None, font_size: int = 9):
                    nonlocal cursor_y
                    text = (value or '').strip()
                    if not text:
                        return
                    chosen_font = font_name or body_font
                    try:
                        canvas.setFont(chosen_font, font_size)
                    except Exception:
                        canvas.setFont('Helvetica', font_size)
                    canvas.drawRightString(draw_x, cursor_y, text)
                    cursor_y -= 4 * mm

                canvas.setFillColor(colors.HexColor('#0F172A'))
                _draw_line(lab_name or 'Biofix Laboratory', font_name=body_font_bold, font_size=11)
                _draw_line(lab_address)

                contact_line = lab_contact
                if not contact_line:
                    contact_parts = []
                    if lab_phone:
                        contact_parts.append(f"Phone: {lab_phone}")
                    if lab_email:
                        contact_parts.append(f"Email: {lab_email}")
                    contact_line = '  |  '.join(contact_parts)
                _draw_line(contact_line)

            canvas.restoreState()

        def footer(self, canvas, doc):
            canvas.saveState()
            styles = getSampleStyleSheet()

            footer_text = f"Page {doc.page} | Report ID: {sample.display_id}"
            p = Paragraph(footer_text, styles['Normal'])
            p.wrapOn(canvas, doc.width, doc.bottomMargin)
            p.drawOn(canvas, doc.leftMargin, 4 * mm)

            canvas.restoreState()

    top_margin_mm = 54 if include_branding else 50
    bottom_margin_mm = 34 if include_branding else 30

    doc = ReportDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=top_margin_mm * mm,
        bottomMargin=bottom_margin_mm * mm,
        include_branding=include_branding,
        background_image=background_template,
        watermark_image=watermark_image,
    )

    palette = {
        'surface': colors.HexColor('#F8FAFC') if include_branding else colors.white,
        'primary': colors.HexColor('#3BBCA3') if include_branding else colors.black,
        'text': colors.HexColor('#0F172A') if include_branding else colors.black,
        'muted': colors.HexColor('#6B7280') if include_branding else colors.HexColor('#1F2937'),
        'grid': colors.HexColor('#E2E8F0') if include_branding else colors.HexColor('#9CA3AF'),
        'row_alt': colors.HexColor('#ECFFFA') if include_branding else colors.white,
    }

    surface = palette['surface']
    primary = palette['primary']
    text_color = palette['text']
    muted_color = palette['muted']
    grid_color = palette['grid']
    row_alt_color = palette['row_alt']
    header_text_color = colors.white if include_branding else text_color

    body_font, body_font_bold = _register_body_fonts()

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, fontName=body_font))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, fontName=body_font))
    styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT, fontName=body_font))
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['h1'],
        alignment=TA_CENTER,
        spaceAfter=12,
        fontSize=18,
        fontName=body_font_bold,
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['h2'],
        spaceAfter=10,
        fontSize=12,
        leading=14,
        fontName=body_font_bold,
    ))
    styles.add(ParagraphStyle(name='Label', parent=styles['Normal'], fontName=body_font_bold, fontSize=9, textColor=muted_color))
    styles.add(ParagraphStyle(name='Value', parent=styles['Normal'], fontName=body_font, fontSize=10, textColor=text_color))
    styles.add(ParagraphStyle(name='TableHead', parent=styles['Normal'], fontName=body_font_bold, alignment=TA_CENTER, textColor=header_text_color, fontSize=9))
    styles.add(ParagraphStyle(name='TableCell', parent=styles['Normal'], fontName=body_font, alignment=TA_LEFT, leading=12, fontSize=9))

    styles.add(ParagraphStyle(
        name='CategoryHeading',
        parent=styles['Normal'],
        fontName=body_font_bold,
        fontSize=11,
        textColor=text_color,
        spaceBefore=10,
        spaceAfter=6,
    ))

    styles['ReportTitle'].textColor = primary
    styles['SectionTitle'].textColor = primary
    styles['Normal'].textColor = text_color
    styles['Normal'].fontName = body_font

    elements = []
    elements.append(Paragraph("WATER QUALITY ANALYSIS REPORT", styles['ReportTitle']))

    def _user_display(user_obj) -> str:
        if not user_obj:
            return 'N/A'
        full_name = (user_obj.get_full_name() or '').strip()
        return full_name or user_obj.username

    def _safe_text(value, default='N/A', preserve_breaks: bool = False) -> str:
        """Escape user-provided text before injecting into Paragraph markup."""
        text = ''
        if value is not None:
            text = str(value).strip()
        if not text:
            text = default
        text = escape(text)
        if preserve_breaks:
            text = text.replace('\n', '<br/>')
        return text

    customer = sample.customer
    location_display = (
        sample.sampling_location
        or getattr(customer, 'village_town_city', '') or getattr(customer, 'street_locality_landmark', '')
        or getattr(customer, 'district', '')
        or 'N/A'
    )

    meta_rows = [
        [Paragraph('<b>Sample Code</b>', styles['Label']), Paragraph(_safe_text(sample.display_id, 'N/A'), styles['Value']),
         Paragraph('<b>Report Number</b>', styles['Label']), Paragraph(_safe_text(sample.report_number, 'N/A'), styles['Value'])],
        [Paragraph('<b>Customer</b>', styles['Label']), Paragraph(_safe_text(sample.customer.name, 'N/A'), styles['Value']),
         Paragraph('<b>Collected On</b>', styles['Label']), Paragraph(_safe_text(sample.collection_datetime.strftime('%d %b %Y %H:%M') if sample.collection_datetime else '', 'N/A'), styles['Value'])],
        [Paragraph('<b>Sample Source</b>', styles['Label']), Paragraph(_safe_text(sample.get_sample_source_display(), 'N/A'), styles['Value']),
         Paragraph('<b>Location</b>', styles['Label']), Paragraph(_safe_text(location_display, 'N/A'), styles['Value'])],
        [Paragraph('<b>Received At Lab</b>', styles['Label']), Paragraph(_safe_text(sample.date_received_at_lab.strftime('%d %b %Y %H:%M') if sample.date_received_at_lab else '', 'N/A'), styles['Value']),
         Paragraph('<b>Test Commenced</b>', styles['Label']), Paragraph(_safe_text(sample.test_commenced_on.strftime('%d %b %Y') if sample.test_commenced_on else '', 'N/A'), styles['Value'])],
        [Paragraph('<b>Test Completed</b>', styles['Label']), Paragraph(_safe_text(sample.test_completed_on.strftime('%d %b %Y') if sample.test_completed_on else '', 'N/A'), styles['Value']), '', ''],
    ]
    last_meta_row_index = len(meta_rows) - 1
    meta_table = Table(meta_rows, colWidths=[32 * mm, 55 * mm, 32 * mm, doc.width - 119 * mm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), surface),
        ('BOX', (0, 0), (-1, -1), 0.75, grid_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, grid_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('SPAN', (1, last_meta_row_index), (3, last_meta_row_index)),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 8))

    address_table = Table([
        [Paragraph('<b>Customer Address</b>', styles['Label'])],
        [Paragraph(_safe_text(sample.customer.address, 'N/A', preserve_breaks=True), styles['Value'])],
    ], colWidths=[doc.width])
    address_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, grid_color),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), surface),
    ]))
    elements.append(address_table)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("TEST REPORTS", styles['SectionTitle']))
    elements.append(Spacer(1, 3))

    results_queryset = sample.results.select_related('parameter').order_by('parameter__display_order', 'parameter__name')
    results = list(results_queryset)

    section_headings = {
        'physical': 'Physical Parameters',
        'chemical': 'Chemical Parameters',
        'microbiological': 'Microbiological Parameters',
        'other': 'Other Parameters',
    }

    section_templates: dict[str, dict] = {}
    section_order: list[str] = []

    def _section_for_category(label: str) -> str:
        lowered = label.casefold()
        if 'physical' in lowered:
            return 'physical'
        if 'chemical' in lowered:
            return 'chemical'
        if any(token in lowered for token in ('micro', 'bacter', 'pathogen')):
            return 'microbiological'
        return 'other'

    for result in results:
        display_label = (getattr(result.parameter, 'category_label', '') or '').strip() or 'Uncategorized'
        section_key = _section_for_category(display_label)
        section_bucket = section_templates.setdefault(section_key, {'categories': OrderedDict()})
        categories = section_bucket['categories']
        if section_key not in section_order:
            section_order.append(section_key)
        if display_label not in categories:
            categories[display_label] = []
        categories[display_label].append(result)

    available_width = doc.width
    column_widths = [
        available_width * 0.07,
        available_width * 0.28,
        available_width * 0.11,
        available_width * 0.20,
        available_width * 0.18,
        available_width * 0.16,
    ]

    status_styles = {
        'WITHIN_LIMITS': ('Within limits', '#0F766E'),
        'BELOW_LIMIT': ('Below minimum', '#B45309'),
        'ABOVE_LIMIT': ('Above maximum', '#DC2626'),
        'NON_NUMERIC': ('', '#0F172A'),
        'UNKNOWN': ('', '#0F172A'),
    }

    def _build_results_table(category_results, start_index, section_key: str):
        header = [
            Paragraph('Sl. No', styles['TableHead']),
            Paragraph('Parameter', styles['TableHead']),
            Paragraph('Unit', styles['TableHead']),
            Paragraph('Method', styles['TableHead']),
            Paragraph('Results', styles['TableHead']),
            Paragraph('Limit', styles['TableHead']),
        ]
        table_data = [header]

        def format_limits(param):
            if getattr(param, 'max_limit_display', None):
                return param.max_limit_display
            if param.min_permissible_limit is None and param.max_permissible_limit is None:
                return '—'
            if param.min_permissible_limit is None:
                return f"≤ {param.max_permissible_limit} {param.unit or ''}".strip()
            if param.max_permissible_limit is None:
                return f"≥ {param.min_permissible_limit} {param.unit or ''}".strip()
            return f"{param.min_permissible_limit} – {param.max_permissible_limit} {param.unit or ''}".strip()

        running_index = start_index
        for result in category_results:
            param = result.parameter
            limits_text = format_limits(param)
            status = getattr(result, 'get_limit_status', lambda: None)()
            label_text, label_color = status_styles.get(status, ('', '#0F172A'))
            result_value = (result.result_value or '—').strip() or '—'
            colour = label_color or '#0F172A'
            if section_key == 'microbiological' and result_value.lower() == 'present':
                colour = '#DC2626'
            result_label = f'<font color="{colour}">{escape(result_value)}</font>'
            if label_text:
                result_label += f'<br/><font size="8" color="#6B7280">{escape(label_text)}</font>'

            table_data.append([
                Paragraph(str(running_index), styles['TableCell']),
                Paragraph(_safe_text(param.name, '—'), styles['TableCell']),
                Paragraph(_safe_text(param.unit, '—'), styles['TableCell']),
                Paragraph(_safe_text(param.method, '—'), styles['TableCell']),
                Paragraph(result_label, styles['TableCell']),
                Paragraph(_safe_text(limits_text, '—'), styles['TableCell']),
            ])
            running_index += 1

        table = Table(table_data, colWidths=column_widths, repeatRows=1)
        header_padding = 5 if include_branding else 6
        body_padding = 4 if include_branding else 6
        table_style = [
            ('FONTNAME', (0, 0), (-1, 0), body_font_bold),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.4, grid_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, 0), header_padding),
            ('BOTTOMPADDING', (0, 0), (-1, 0), header_padding),
            ('TOPPADDING', (0, 1), (-1, -1), body_padding),
            ('BOTTOMPADDING', (0, 1), (-1, -1), body_padding),
        ]
        if include_branding:
            table_style.extend([
                ('BACKGROUND', (0, 0), (-1, 0), primary),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), (colors.white, row_alt_color)),
            ])
        else:
            table_style.append(('LINEBELOW', (0, 0), (-1, 0), 0.5, grid_color))
        table.setStyle(TableStyle(table_style))
        return table, running_index

    def _labels_redundant(section_heading: str, category_label: str) -> bool:
        """Treat headings that differ only by filler words as duplicates."""
        def _canonical(value: str) -> str:
            tokens = re.findall(r'[a-z0-9]+', value.casefold())
            filtered = [
                token for token in tokens
                if token not in {'parameter', 'parameters', 'category', 'categories'}
            ]
            return ' '.join(filtered).strip()

        canonical_heading = _canonical(section_heading)
        canonical_category = _canonical(category_label)
        return bool(canonical_heading and canonical_heading == canonical_category)

    def _render_section(section_key: str, heading: str, serial_counter: int):
        section = section_templates.get(section_key, {'categories': OrderedDict()})
        elements.append(Paragraph(heading, styles['SectionTitle']))
        elements.append(Spacer(1, 6))
        if section['categories']:
            for category_label, category_results in section['categories'].items():
                label_text = (category_label or '').strip()
                if label_text and not _labels_redundant(heading, label_text):
                    elements.append(Paragraph(_safe_text(label_text, ''), styles['CategoryHeading']))
                table, serial_counter = _build_results_table(category_results, serial_counter, section_key)
                elements.append(table)
                elements.append(Spacer(1, 10))
        else:
            elements.append(Paragraph("No parameters recorded for this category.", styles['Normal']))
            elements.append(Spacer(1, 10))
        return serial_counter

    review = getattr(sample, 'review', None)
    if review:
        recommendations_text = (review.recommendations or '').strip()
        comments_text = (review.comments or '').strip()
    else:
        recommendations_text = ''
        comments_text = ''
    signatories = sample.resolve_signatories()

    def _signatory_name(user):
        if not user:
            return 'Not assigned'
        full = (user.get_full_name() or '').strip()
        return full or user.username

    def _signatory_payload(user, role):
        return {
            'name': _signatory_name(user),
            'role': role,
            'signature_path': getattr(user, 'signature_path', '') if user else '',
        }

    def _signature_cell(data):
        elements = []
        signature_path = (data.get('signature_path') or '').strip()
        if signature_path:
            try:
                signature_img = Image(signature_path)
                signature_img._restrictSize(48 * mm, 20 * mm)
            except Exception as exc:
                logger.warning(
                    "Unable to load signature image for %s",
                    data.get('name'),
                    exc_info=settings.DEBUG,
                )
            else:
                elements.append(signature_img)
                elements.append(Spacer(1, 4))
        safe_name = _safe_text(data.get('name'), 'Not assigned')
        safe_role = _safe_text(data.get('role'), '')
        elements.append(Paragraph(f"<b>{safe_name}</b><br/>{safe_role}", styles['Center']))
        if len(elements) == 1:
            return elements[0]
        inner = Table([[el] for el in elements], colWidths=[52 * mm])
        inner.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return inner

    def _append_signatories_section(introduce_break: bool = False):
        """Render authorised signatories, optionally forcing a new page."""
        if introduce_break:
            elements.append(PageBreak())
        elements.append(Paragraph("AUTHORISED SIGNATORIES", styles['SectionTitle']))
        payloads = [
            _signatory_payload(signatories.get('chem_manager'), 'Chief of Quality - Chemistry'),
            _signatory_payload(signatories.get('bio_manager'), 'Chief of Quality - Microbiology'),
            _signatory_payload(signatories.get('food_analyst'), 'Chief Scientific Officer'),
        ]
        active_payloads = [p for p in payloads if any(p.values())]

        cells = [_signature_cell(slot) for slot in active_payloads]
        if not cells:
            cells = ['', '', '']
        while len(cells) < 3:
            cells.append('')
        sign_table = Table(
            [cells[:3]],
            colWidths=[(doc.width / 3.0) - 6] * 3,
            rowHeights=[40 * mm],
            hAlign='CENTER',
        )
        sign_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(sign_table)
        elements.append(Spacer(1, 12))

    def _append_consultant_signature_section():
        """Render the consultant sign-off below remarks."""
        reviewer = review.reviewer if review else None
        fallback_consultant = signatories.get('solutions_manager')
        consultant_user = _choose_signer_with_signature(reviewer, fallback_consultant)
        role_label = 'Chief of Solutions - Water Quality'
        if consultant_user:
            consultant_slot = _signatory_payload(consultant_user, role_label)
            consultant_cell = _signature_cell(consultant_slot)
            table = Table([[consultant_cell]], colWidths=[58 * mm])
            table.hAlign = 'RIGHT'
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 18))
        else:
            elements.append(
                Paragraph(
                    f"{_safe_text(role_label, role_label)}: Not assigned",
                    styles['Normal'],
                )
            )
            elements.append(Spacer(1, 12))

    serial_counter = 1
    sign_section_inserted = False
    for index, section_key in enumerate(section_order):
        if index > 0:
            elements.append(PageBreak())
        heading = section_headings.get(section_key, section_headings['other'])
        serial_counter = _render_section(section_key, heading, serial_counter)
        if not sign_section_inserted and section_key == 'microbiological':
            _append_signatories_section(introduce_break=False)
            sign_section_inserted = True

    if not sign_section_inserted:
        if elements and not isinstance(elements[-1], PageBreak):
            elements.append(PageBreak())
        _append_signatories_section(introduce_break=False)

    elements.append(PageBreak())

    elements.append(Paragraph("REMARKS", styles['SectionTitle']))
    if comments_text:
        elements.append(Paragraph(_safe_text(comments_text, preserve_breaks=True), styles['Normal']))
    else:
        elements.append(Paragraph(
            "The sample has been analysed in accordance with IS 10500:2012 guidelines. Outcomes above include automated compliance status for each parameter.",
            styles['Normal'],
        ))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Consultant Recommendations", styles['SectionTitle']))
    if recommendations_text:
        elements.append(Paragraph(_safe_text(recommendations_text, preserve_breaks=True), styles['Normal']))
    else:
        elements.append(Paragraph("No consultant recommendations recorded for this sample.", styles['Normal']))
    elements.append(Spacer(1, 18))
    _append_consultant_signature_section()

    doc.build(elements)

    buffer.seek(0)
    filename_suffix = '_plain' if not include_branding else ''
    response = FileResponse(
        buffer,
        as_attachment=True,
        filename=f'WaterQualityReport_{sample.display_id}{filename_suffix}.pdf',
    )

    if sample.current_status == 'REPORT_APPROVED':
        try:
            sample.update_status('REPORT_SENT', request.user)
            messages.info(
                request,
                f"Report for sample {sample.display_id} downloaded and status updated to 'Report Sent'.",
            )
        except Exception as exc:
            logger.exception(
                "Failed to update sample %s status after report download",
                sample.sample_id,
            )
            messages.warning(
                request,
                _format_error_message(
                    "Report downloaded, but failed to update sample status.",
                    exc,
                ),
            )

    return response


def download_sample_invoice_view(request, pk):
    sample = get_object_or_404(Sample, pk=pk)

    if not _user_can_view_sensitive_records(request.user):
        messages.error(request, "You do not have permission to download this invoice.")
        return redirect('core:dashboard')

    if sample.current_status not in ['REPORT_APPROVED', 'REPORT_SENT']:
        messages.error(request, "Invoice can only be generated after the report is approved.")
        return redirect('core:sample_detail', pk=sample.pk)

    try:
        invoice = Invoice.create_for_sample(sample)
        force_rebuild = invoice.line_items.filter(parameter__isnull=False).exists()
        invoice.ensure_line_items(force=force_rebuild)
        invoice.recalculate_totals(save=True)
        if invoice.status == 'DRAFT':
            invoice.status = 'ISSUED'
            invoice.save(update_fields=['status'])
    except Exception as exc:
        logger.exception("Failed to prepare invoice for sample %s", sample.sample_id)
        messages.error(
            request,
            _format_error_message("Unable to generate invoice right now.", exc),
        )
        return redirect('core:sample_detail', pk=sample.pk)

    from django.conf import settings
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    def _get_currency_symbol() -> str:
        settings_data = getattr(settings, 'WATERLAB_SETTINGS', {})
        symbol = settings_data.get('CURRENCY_SYMBOL')
        return symbol or '₹'

    currency_symbol = _get_currency_symbol()

    def _register_invoice_fonts() -> tuple[str, str]:
        candidates = [
            os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf'),
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
        bold_candidates = [
            os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans-Bold.ttf'),
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]

        def _try_register(name: str, path: str) -> bool:
            if not path or not os.path.exists(path):
                return False
            try:
                if name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, path))
                return True
            except Exception:
                return False

        body_font = 'Helvetica'
        bold_font = 'Helvetica-Bold'

        for path in candidates:
            if _try_register('DejaVuSans', path):
                body_font = 'DejaVuSans'
                break

        for path in bold_candidates:
            if _try_register('DejaVuSans-Bold', path):
                bold_font = 'DejaVuSans-Bold'
                break

        return body_font, bold_font

    body_font, body_font_bold = _register_invoice_fonts()

    def _format_money(value) -> str:
        try:
            amount = Decimal(value or 0).quantize(Decimal('0.01'))
        except Exception:
            amount = Decimal('0.00')
        return f"{currency_symbol}{amount:,.2f}"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='InvoiceTitle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        textColor=colors.HexColor('#0F172A'),
        fontName=body_font_bold,
        spaceAfter=6,
    )
    label_style = ParagraphStyle(
        name='InvoiceLabel',
        parent=styles['Normal'],
        textColor=colors.HexColor('#64748B'),
        fontSize=9,
        fontName=body_font,
    )
    value_style = ParagraphStyle(
        name='InvoiceValue',
        parent=styles['Normal'],
        fontSize=10,
        fontName=body_font,
    )
    right_style = ParagraphStyle(
        name='InvoiceRight',
        parent=value_style,
        alignment=TA_RIGHT,
        fontName=body_font,
    )

    lab_settings = getattr(settings, 'WATERLAB_SETTINGS', {})
    profile = LabProfile.get_active()
    lab_name = (profile.name or lab_settings.get('LAB_NAME') or 'WaterLab Laboratory').strip()
    lab_address = (profile.formatted_address or profile.address_line1 or lab_settings.get('LAB_ADDRESS') or '').strip()
    lab_phone = (profile.phone or lab_settings.get('LAB_PHONE') or '').strip()
    lab_email = (profile.email or lab_settings.get('LAB_EMAIL') or '').strip()
    lab_contact = profile.contact_line
    if not lab_contact:
        contact_parts = []
        if lab_phone:
            contact_parts.append(f"Phone: {lab_phone}")
        if lab_email:
            contact_parts.append(f"Email: {lab_email}")
        lab_contact = '  |  '.join(contact_parts)

    header_left_parts = []
    logo_path = profile.logo_path
    if logo_path and os.path.exists(logo_path):
        try:
            logo_reader = ImageReader(logo_path)
            logo_width, logo_height = logo_reader.getSize()
            max_width = 40 * mm
            max_height = 16 * mm
            scale = min(max_width / logo_width, max_height / logo_height)
            if scale <= 0:
                scale = 1
            header_left_parts.append(
                Image(logo_path, width=logo_width * scale, height=logo_height * scale)
            )
            header_left_parts.append(Spacer(1, 4))
        except Exception:
            header_left_parts.append(Image(logo_path, width=36 * mm, height=14 * mm))
            header_left_parts.append(Spacer(1, 4))

    header_left_parts.append(Paragraph(f"<b>{escape(lab_name)}</b>", value_style))
    if lab_address:
        header_left_parts.append(Paragraph(escape(lab_address), styles['Normal']))
    if lab_contact:
        header_left_parts.append(Paragraph(escape(lab_contact), styles['Normal']))

    header_right_table = Table(
        [
            [Paragraph("Invoice #", label_style), Paragraph(invoice.invoice_number or "—", right_style)],
            [Paragraph("Date", label_style), Paragraph(invoice.issued_on.strftime('%b %d, %Y'), right_style)],
            [Paragraph("Status", label_style), Paragraph(invoice.get_status_display(), right_style)],
            [
                Paragraph("Report #", label_style),
                Paragraph(escape(sample.report_number) if sample.report_number else "—", right_style),
            ],
            [
                Paragraph("Sample ID", label_style),
                Paragraph(escape(sample.display_id) if sample.display_id else str(sample.sample_id), right_style),
            ],
        ],
        colWidths=[doc.width * 0.18, doc.width * 0.22],
        hAlign='RIGHT',
    )
    header_right_table.setStyle(
        TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ])
    )

    header_table = Table(
        [[header_left_parts, header_right_table]],
        colWidths=[doc.width * 0.58, doc.width * 0.42],
    )
    header_table.setStyle(
        TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ])
    )

    elements = [
        Paragraph("INVOICE", title_style),
        header_table,
        Spacer(1, 10),
    ]

    billing_lines = [
        Paragraph("<b>Bill To</b>", value_style),
        Paragraph(escape(sample.customer.name), value_style),
    ]
    if sample.customer.address:
        billing_lines.append(Paragraph(escape(sample.customer.address), styles['Normal']))
    if sample.customer.phone:
        billing_lines.append(Paragraph(escape(sample.customer.phone), styles['Normal']))
    if sample.customer.email:
        billing_lines.append(Paragraph(escape(sample.customer.email), styles['Normal']))

    billing_table = Table(
        [[billing_lines, '']],
        colWidths=[doc.width * 0.6, doc.width * 0.4],
    )
    billing_table.setStyle(
        TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ])
    )
    elements.extend([billing_table, Spacer(1, 12)])

    line_items = list(invoice.line_items.all().order_by('position', 'description'))
    items_table_rows = [
        [
            Paragraph("ID", label_style),
            Paragraph("Description", label_style),
            Paragraph("Quantity", label_style),
            Paragraph("Rate", label_style),
            Paragraph("Amount", label_style),
        ]
    ]
    if line_items:
        for idx, item in enumerate(line_items, start=1):
            items_table_rows.append([
                Paragraph(str(idx), value_style),
                Paragraph(escape(item.description), value_style),
                Paragraph(str(item.quantity), right_style),
                Paragraph(_format_money(item.unit_price), right_style),
                Paragraph(_format_money(item.amount), right_style),
            ])
    else:
        items_table_rows.append([
            Paragraph("—", value_style),
            Paragraph("No billable tests found.", value_style),
            Paragraph("—", value_style),
            Paragraph(_format_money(Decimal('0.00')), right_style),
            Paragraph(_format_money(Decimal('0.00')), right_style),
        ])

    items_table = Table(
        items_table_rows,
        colWidths=[doc.width * 0.08, doc.width * 0.44, doc.width * 0.12, doc.width * 0.18, doc.width * 0.18],
    )
    items_table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#CBD5F5')),
            ('GRID', (0, 1), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])
    )
    elements.extend([items_table, Spacer(1, 12)])

    totals_rows = [
        [Paragraph("Subtotal", label_style), Paragraph(_format_money(invoice.subtotal), right_style)],
        [Paragraph("Tax Rate", label_style), Paragraph(f"{invoice.tax_rate:.2f}%", right_style)],
        [Paragraph("Tax", label_style), Paragraph(_format_money(invoice.tax_amount), right_style)],
        [Paragraph("<b>Total</b>", value_style), Paragraph(f"<b>{_format_money(invoice.total)}</b>", right_style)],
    ]
    totals_table = Table(
        totals_rows,
        colWidths=[doc.width * 0.22, doc.width * 0.18],
        hAlign='RIGHT',
    )
    totals_table.setStyle(
        TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ])
    )

    thank_you = Paragraph("<b>Thank you for your business!</b>", value_style)
    thanks_table = Table(
        [[thank_you, totals_table]],
        colWidths=[doc.width * 0.6, doc.width * 0.4],
    )
    thanks_table.setStyle(
        TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ])
    )
    elements.extend([thanks_table, Spacer(1, 10)])

    settings_data = getattr(settings, 'WATERLAB_SETTINGS', {})
    payment = settings_data.get('PAYMENT_OPTIONS') or {}
    payment_lines = []
    if payment:
        payment_lines.append(Paragraph("<b>Payment Options</b>", value_style))
        if payment.get('ACCOUNT_NAME'):
            payment_lines.append(Paragraph(f"Bank account name : {escape(str(payment.get('ACCOUNT_NAME')))}", styles['Normal']))
        if payment.get('ACCOUNT_NUMBER'):
            payment_lines.append(Paragraph(f"Account number : {escape(str(payment.get('ACCOUNT_NUMBER')))}", styles['Normal']))
        if payment.get('BANK_NAME'):
            payment_lines.append(Paragraph(f"Bank name : {escape(str(payment.get('BANK_NAME')))}", styles['Normal']))
        if payment.get('IFSC'):
            payment_lines.append(Paragraph(f"IFSC Code : {escape(str(payment.get('IFSC')))}", styles['Normal']))
        if payment.get('PHONE'):
            payment_lines.append(Paragraph(f"Ph no : {escape(str(payment.get('PHONE')))}", styles['Normal']))

    if payment_lines:
        elements.append(Spacer(1, 6))
        elements.extend(payment_lines)

    if invoice.notes:
        elements.append(Paragraph("<b>Notes</b>", value_style))
        elements.append(Paragraph(escape(invoice.notes), styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    response = FileResponse(
        buffer,
        as_attachment=True,
        filename=f"Invoice_{invoice.invoice_number or sample.display_id}.pdf",
    )
    return response
