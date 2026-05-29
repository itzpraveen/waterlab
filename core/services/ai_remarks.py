import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIRemarkDraft:
    comments: str
    recommendations: str
    model: str


class AIRemarkError(RuntimeError):
    pass


def _clean_text(value):
    return (value or '').strip()


def _decimal_to_text(value):
    if value is None:
        return ''
    if isinstance(value, Decimal):
        return format(value.normalize(), 'f')
    return str(value)


def _limit_text(parameter):
    if parameter.max_limit_display:
        return parameter.max_limit_display

    minimum = _decimal_to_text(parameter.min_permissible_limit)
    maximum = _decimal_to_text(parameter.max_permissible_limit)
    unit = _clean_text(parameter.unit)

    if minimum and maximum:
        return f"{minimum} - {maximum} {unit}".strip()
    if maximum:
        return f"Maximum {maximum} {unit}".strip()
    if minimum:
        return f"Minimum {minimum} {unit}".strip()
    return "Not specified"


def _status_label(status):
    return {
        'WITHIN_LIMITS': 'Within acceptable limit',
        'ABOVE_LIMIT': 'Above acceptable limit',
        'BELOW_LIMIT': 'Below acceptable limit',
        'NON_NUMERIC': 'Qualitative/non-numeric result',
        'UNKNOWN': 'Unknown',
    }.get(status, status or 'Unknown')


def _sample_result_payload(sample):
    results = []
    queryset = sample.results.select_related('parameter', 'parameter__category_obj').order_by(
        'parameter__category_obj__display_order',
        'parameter__category',
        'parameter__display_order',
        'parameter__name',
    )

    for result in queryset:
        parameter = result.parameter
        status = result.get_limit_status()
        results.append({
            'parameter': parameter.name,
            'category': parameter.category_label,
            'value': result.result_value,
            'unit': parameter.unit or '',
            'acceptable_limit': _limit_text(parameter),
            'status': _status_label(status),
            'observation': result.observation or result.remarks or '',
        })

    return {
        'sample_id': sample.display_id or str(sample.sample_id),
        'sample_source': sample.get_sample_source_display(),
        'sampling_location': sample.sampling_location or sample.customer.village_town_city or '',
        'results': results,
    }


def _build_prompt(sample):
    payload = _sample_result_payload(sample)
    return (
        "Draft consultant remarks and recommendations for a water quality lab report.\n"
        "Use only the lab result data provided below. Do not invent measurements, do not diagnose health conditions, "
        "and do not guarantee safety beyond the listed parameters.\n"
        "Remarks should summarize which parameters are present or outside limits and which major groups are within limits.\n"
        "Recommendations should suggest practical water-treatment or retesting actions only when supported by the results.\n"
        "Write professional report-ready text in both English and Malayalam. Keep each language concise.\n\n"
        f"Lab result data:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def _response_schema():
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'remarks_english': {'type': 'string'},
            'recommendations_english': {'type': 'string'},
            'remarks_malayalam': {'type': 'string'},
            'recommendations_malayalam': {'type': 'string'},
        },
        'required': [
            'remarks_english',
            'recommendations_english',
            'remarks_malayalam',
            'recommendations_malayalam',
        ],
    }


def _extract_response_text(response_data):
    output_text = response_data.get('output_text')
    if output_text:
        return output_text

    for item in response_data.get('output', []):
        for content in item.get('content', []):
            text = content.get('text')
            if text:
                return text
    return ''


def _combine_language_sections(english, malayalam):
    sections = []
    english = _clean_text(english)
    malayalam = _clean_text(malayalam)
    if english:
        sections.append(f"English:\n{english}")
    if malayalam:
        sections.append(f"Malayalam:\n{malayalam}")
    return "\n\n".join(sections)


def generate_ai_review_draft(sample) -> AIRemarkDraft:
    api_key = _clean_text(getattr(settings, 'OPENAI_API_KEY', ''))
    if not api_key:
        raise ImproperlyConfigured("OPENAI_API_KEY is not configured.")

    model = _clean_text(getattr(settings, 'OPENAI_REMARKS_MODEL', '')) or 'gpt-5-mini'
    endpoint = _clean_text(getattr(settings, 'OPENAI_RESPONSES_URL', '')) or 'https://api.openai.com/v1/responses'
    timeout = int(getattr(settings, 'OPENAI_REMARKS_TIMEOUT', 30))

    request_payload = {
        'model': model,
        'input': [
            {
                'role': 'developer',
                'content': (
                    "You are assisting a certified water testing laboratory consultant. "
                    "Produce concise, factual, report-ready text. Return only valid structured data."
                ),
            },
            {
                'role': 'user',
                'content': _build_prompt(sample),
            },
        ],
        'text': {
            'format': {
                'type': 'json_schema',
                'name': 'water_report_ai_remarks',
                'strict': True,
                'schema': _response_schema(),
            },
        },
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(request_payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_data = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        logger.warning("OpenAI remarks request failed with HTTP %s: %s", exc.code, detail[:500])
        raise AIRemarkError("AI remarks request failed. Check API key, model, and billing access.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("OpenAI remarks request failed: %s", exc)
        raise AIRemarkError("AI remarks service is temporarily unavailable.") from exc

    output_text = _extract_response_text(response_data)
    if not output_text:
        raise AIRemarkError("AI remarks response did not include text output.")

    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError as exc:
        logger.warning("OpenAI remarks response was not valid JSON: %s", output_text[:500])
        raise AIRemarkError("AI remarks response could not be parsed.") from exc

    comments = _combine_language_sections(
        parsed.get('remarks_english'),
        parsed.get('remarks_malayalam'),
    )
    recommendations = _combine_language_sections(
        parsed.get('recommendations_english'),
        parsed.get('recommendations_malayalam'),
    )

    if not comments or not recommendations:
        raise AIRemarkError("AI remarks response was incomplete.")

    return AIRemarkDraft(comments=comments, recommendations=recommendations, model=model)
