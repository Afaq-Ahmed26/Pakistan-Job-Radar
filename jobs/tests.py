from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from .models import Job, JobSource, ScrapeRun
from .services import build_job_fingerprint, run_adapter
from .scrapers.base import NormalizedJob
from .scrapers.fixture import FixtureAdapter


class JobModelTests(TestCase):
    def setUp(self):
        self.source = JobSource.objects.create(
            name='Example Source',
            slug='example-source',
            base_url='https://example.com',
        )

    def test_job_string_representation(self):
        job = Job.objects.create(
            source=self.source,
            title='Django Developer',
            company_name='Example Tech',
            location_text='Lahore',
            source_url='https://example.com/jobs/1',
            fingerprint='fingerprint-1',
        )

        self.assertEqual(str(job), 'Django Developer at Example Tech')

    def test_source_url_cannot_duplicate_within_source(self):
        job_data = {
            'source': self.source,
            'title': 'Django Developer',
            'company_name': 'Example Tech',
            'location_text': 'Lahore',
            'source_url': 'https://example.com/jobs/1',
            'fingerprint': 'fingerprint-1',
        }
        Job.objects.create(**job_data)

        with self.assertRaises(IntegrityError):
            Job.objects.create(
                **{**job_data, 'fingerprint': 'fingerprint-2'}
            )

    def test_scrape_run_defaults_to_running(self):
        scrape_run = ScrapeRun.objects.create(source=self.source)

        self.assertEqual(scrape_run.status, ScrapeRun.Status.RUNNING)


class FixtureAdapterTests(TestCase):
    def test_fixture_adapter_normalizes_complete_listings(self):
        jobs = list(FixtureAdapter().parse(FixtureAdapter().fetch()))

        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0].external_id, 'fixture-001')
        self.assertEqual(jobs[0].title, 'Junior Python Developer')
        self.assertEqual(jobs[0].company_name, 'Example Tech Pakistan')
        self.assertEqual(jobs[0].workplace_type, 'hybrid')
        self.assertEqual(
            jobs[0].source_url,
            'https://fixture.example.com/jobs/fixture-001',
        )

    def test_fixture_adapter_skips_incomplete_listings(self):
        jobs = list(FixtureAdapter().parse(FixtureAdapter().fetch()))

        self.assertNotIn('fixture-incomplete', [job.external_id for job in jobs])


class IngestionServiceTests(TestCase):
    def setUp(self):
        self.source = JobSource.objects.create(
            name='Fixture Source',
            slug='fixture-source',
            base_url='https://fixture.example.com',
            source_type=JobSource.SourceType.FIXTURE,
        )

    def test_run_persists_jobs_and_skips_invalid_records(self):
        scrape_run = run_adapter(self.source, FixtureAdapter())

        self.assertEqual(scrape_run.status, ScrapeRun.Status.SUCCEEDED)
        self.assertEqual(scrape_run.jobs_seen, 2)
        self.assertEqual(scrape_run.jobs_created, 2)
        self.assertEqual(scrape_run.jobs_skipped, 0)
        self.assertEqual(Job.objects.count(), 2)

    def test_second_run_updates_instead_of_creating_duplicates(self):
        run_adapter(self.source, FixtureAdapter())
        first_job = Job.objects.get(external_id='fixture-001')
        first_seen_at = first_job.first_seen_at

        run_adapter(self.source, FixtureAdapter())

        self.assertEqual(Job.objects.count(), 2)
        updated_job = Job.objects.get(external_id='fixture-001')
        self.assertEqual(updated_job.first_seen_at, first_seen_at)
        self.assertGreaterEqual(updated_job.last_seen_at, first_seen_at)
        self.assertEqual(ScrapeRun.objects.count(), 2)

    def test_invalid_job_is_skipped_and_run_continues(self):
        valid_job = NormalizedJob(
            title='Valid job',
            company_name='Example company',
            location_text='Lahore',
            source_url='https://fixture.example.com/jobs/valid',
        )
        invalid_job = NormalizedJob(
            title='',
            company_name='Missing title company',
            location_text='Lahore',
            source_url='https://fixture.example.com/jobs/invalid',
        )

        class MixedAdapter:
            def fetch(self):
                return 'unused'

            def parse(self, raw_content):
                return [valid_job, invalid_job]

        scrape_run = run_adapter(self.source, MixedAdapter())

        self.assertEqual(scrape_run.status, ScrapeRun.Status.SUCCEEDED)
        self.assertEqual(scrape_run.jobs_seen, 2)
        self.assertEqual(scrape_run.jobs_created, 1)
        self.assertEqual(scrape_run.jobs_skipped, 1)
        self.assertEqual(Job.objects.count(), 1)

    def test_fingerprint_is_stable_for_same_identity(self):
        job = NormalizedJob(
            title='Backend developer',
            company_name='Example company',
            location_text='Lahore',
            source_url='https://fixture.example.com/jobs/42',
            external_id='42',
            posted_at=timezone.now(),
        )

        self.assertEqual(
            build_job_fingerprint(self.source.slug, job),
            build_job_fingerprint(self.source.slug, job),
        )
