import json
import logging
import re
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


_MALAYALAM_MARKER = re.compile(r'(?im)^[ \t]*malayalam[ \t]*:[ \t]*')
_ENGLISH_MARKER = re.compile(r'(?im)^[ \t]*english[ \t]*:[ \t]*\n?')


def split_bilingual_remarks(text):
    """Split combined ``English:/Malayalam:`` remark text into ``(english, malayalam)``.

    This is the inverse of :func:`_combine_language_sections`. Consultants may edit
    the drafted text, so the parsing is forgiving: when no ``Malayalam:`` marker is
    present the whole value is treated as English, and the leading ``English:`` label
    (if any) is stripped from the English portion.
    """
    text = _clean_text(text)
    if not text:
        return '', ''

    marker = _MALAYALAM_MARKER.search(text)
    if marker:
        english_part = text[:marker.start()]
        malayalam_part = text[marker.end():]
    else:
        english_part, malayalam_part = text, ''

    english_part = _ENGLISH_MARKER.sub('', english_part, count=1).strip()
    return english_part, malayalam_part.strip()


def get_ai_review_runtime_config() -> dict:
    try:
        from core.models import AISettings

        return AISettings.get_runtime_config()
    except Exception as exc:
        logger.warning("Could not load AI settings from database: %s", exc)
        api_key = _clean_text(getattr(settings, 'OPENAI_API_KEY', ''))
        return {
            'enabled': bool(api_key),
            'api_key': api_key,
            'model': _clean_text(getattr(settings, 'OPENAI_REMARKS_MODEL', '')) or 'gpt-5-mini',
            'source': 'environment' if api_key else 'none',
        }


def is_ai_review_configured() -> bool:
    runtime_config = get_ai_review_runtime_config()
    return bool(runtime_config.get('enabled') and runtime_config.get('api_key'))


def generate_ai_review_draft(sample) -> AIRemarkDraft:
    runtime_config = get_ai_review_runtime_config()
    api_key = _clean_text(runtime_config.get('api_key'))
    if not runtime_config.get('enabled') or not api_key:
        raise ImproperlyConfigured("OPENAI_API_KEY is not configured.")

    model = _clean_text(runtime_config.get('model')) or 'gpt-5-mini'
    endpoint = _clean_text(getattr(settings, 'OPENAI_RESPONSES_URL', '')) or 'https://api.openai.com/v1/responses'
    # Generous default: stronger models (e.g. gpt-5) can take well over 30s, and the
    # call runs in a background thread so it does not block a web worker.
    timeout = int(getattr(settings, 'OPENAI_REMARKS_TIMEOUT', 180))

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
