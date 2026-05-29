"""Background job store for AI-drafted report generation.

The only slow part of an AI report is the synchronous call to the model
(~10-30s). Running it inside the web request holds the worker and looks like a
hang/502 to the user. Instead we run that call in a daemon thread and persist
the result to a small JSON file under ``MEDIA_ROOT`` (a disk shared across all
gunicorn workers on the instance, unlike the per-process LocMem cache). A
lightweight "preparing" page polls for completion, then the report is built
synchronously from the cached draft (fast).
"""

import json
import logging
import os
import tempfile
import threading
import time
import uuid

from django.conf import settings
from django.db import connections

logger = logging.getLogger(__name__)

_TTL_SECONDS = 30 * 60  # discard finished jobs after 30 minutes


def _jobs_dir() -> str:
    base = getattr(settings, 'MEDIA_ROOT', None) or tempfile.gettempdir()
    path = os.path.join(base, 'ai_report_jobs')
    os.makedirs(path, exist_ok=True)
    return path


def _job_path(job_id: str):
    safe = ''.join(ch for ch in (job_id or '') if ch.isalnum())
    if not safe:
        return None
    return os.path.join(_jobs_dir(), f'{safe}.json')


def _write_job(job_id: str, data: dict) -> None:
    path = _job_path(job_id)
    if not path:
        return
    tmp = f'{path}.{uuid.uuid4().hex}.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh)
    os.replace(tmp, path)  # atomic so readers never see a partial file


def load_ai_job(job_id: str):
    path = _job_path(job_id)
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def delete_ai_job(job_id: str) -> None:
    path = _job_path(job_id)
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _cleanup_old_jobs() -> None:
    try:
        now = time.time()
        directory = _jobs_dir()
        for name in os.listdir(directory):
            if not name.endswith('.json'):
                continue
            fp = os.path.join(directory, name)
            try:
                if now - os.path.getmtime(fp) > _TTL_SECONDS:
                    os.remove(fp)
            except OSError:
                pass
    except OSError:
        pass


def _run_job(job_id: str, sample_pk: str) -> None:
    from core.models import Sample
    from core.services.ai_remarks import generate_ai_review_draft

    try:
        sample = Sample.objects.get(pk=sample_pk)
        draft = generate_ai_review_draft(sample)
        _write_job(job_id, {
            'status': 'ready',
            'sample_pk': str(sample_pk),
            'comments': draft.comments,
            'recommendations': draft.recommendations,
            'model': draft.model,
            'updated': time.time(),
        })
    except Exception as exc:
        logger.exception("AI report job %s failed for sample %s", job_id, sample_pk)
        _write_job(job_id, {
            'status': 'error',
            'sample_pk': str(sample_pk),
            'message': str(exc) or 'AI generation failed.',
            'updated': time.time(),
        })
    finally:
        # The thread opened its own DB connection; release it.
        connections.close_all()


def start_ai_job(sample) -> str:
    """Start background AI draft generation and return the job id."""
    _cleanup_old_jobs()
    job_id = uuid.uuid4().hex
    _write_job(job_id, {
        'status': 'pending',
        'sample_pk': str(sample.pk),
        'updated': time.time(),
    })
    thread = threading.Thread(
        target=_run_job,
        args=(job_id, str(sample.pk)),
        name=f'ai-report-{job_id[:8]}',
        daemon=True,
    )
    thread.start()
    return job_id
