import hashlib
import logging
from dataclasses import dataclass
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Job, JobSource, ScrapeRun
from .scrapers.base import BaseJobSourceAdapter, NormalizedJob

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    jobs_seen: int = 0
    jobs_created: int = 0
    jobs_updated: int = 0
    jobs_skipped: int = 0


def build_job_fingerprint(source_slug: str, job: NormalizedJob) -> str:
    identity = job.external_id.strip() or job.source_url.strip()
    value = f'{source_slug.strip().lower()}|{identity}'
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def normalize_job_data(
    source: JobSource,
    job: NormalizedJob,
) -> dict:
    required_fields = {
        'title': job.title.strip(),
        'company_name': job.company_name.strip(),
        'location_text': job.location_text.strip(),
        'source_url': job.source_url.strip(),
    }
    if not all(required_fields.values()):
        raise ValidationError('Job title, company, location, and URL are required.')

    return {
        **required_fields,
        'source': source,
        'external_id': job.external_id.strip(),
        'description': job.description.strip(),
        'salary_text': job.salary_text.strip(),
        'salary_min': job.salary_min,
        'salary_max': job.salary_max,
        'salary_currency': job.salary_currency.strip().upper(),
        'job_type': job.job_type.strip(),
        'workplace_type': job.workplace_type.strip(),
        'posted_at': job.posted_at,
        'expires_at': job.expires_at,
        'fingerprint': build_job_fingerprint(source.slug, job),
    }


def persist_job(source: JobSource, normalized_job: NormalizedJob) -> bool:
    job_data = normalize_job_data(source, normalized_job)
    Job(**job_data).full_clean(
        validate_unique=False,
        validate_constraints=False,
    )
    job, created = Job.objects.update_or_create(
        source=source,
        fingerprint=job_data['fingerprint'],
        defaults=job_data,
    )
    if not created:
        job.last_seen_at = timezone.now()
        job.save(update_fields=['last_seen_at'])
    return created


def run_adapter(
    source: JobSource,
    adapter: BaseJobSourceAdapter,
) -> ScrapeRun:
    scrape_run = ScrapeRun.objects.create(source=source)
    result = IngestionResult()

    try:
        raw_content = adapter.fetch()
        for normalized_job in adapter.parse(raw_content):
            result.jobs_seen += 1
            try:
                with transaction.atomic():
                    created = persist_job(source, normalized_job)
            except (ValidationError, ValueError, TypeError) as exc:
                result.jobs_skipped += 1
                logger.warning(
                    'Skipping invalid job from source %s: %s',
                    source.slug,
                    exc,
                )
                continue

            if created:
                result.jobs_created += 1
            else:
                result.jobs_updated += 1

        scrape_run.status = ScrapeRun.Status.SUCCEEDED
    except Exception as exc:
        scrape_run.status = ScrapeRun.Status.FAILED
        scrape_run.error_message = str(exc)
        logger.exception('Scrape failed for source %s', source.slug)
    finally:
        scrape_run.finished_at = timezone.now()
        scrape_run.jobs_seen = result.jobs_seen
        scrape_run.jobs_created = result.jobs_created
        scrape_run.jobs_updated = result.jobs_updated
        scrape_run.jobs_skipped = result.jobs_skipped
        scrape_run.save(
            update_fields=[
                'finished_at',
                'status',
                'error_message',
                'jobs_seen',
                'jobs_created',
                'jobs_updated',
                'jobs_skipped',
            ]
        )

    return scrape_run
