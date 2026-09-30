from django.db import IntegrityError
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

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


class ScrapeJobsCommandTests(TestCase):
    def setUp(self):
        self.source = JobSource.objects.create(
            name='Fixture Source',
            slug='fixture-source',
            base_url='https://fixture.example.com',
            source_type=JobSource.SourceType.FIXTURE,
        )

    def test_command_imports_selected_source(self):
        call_command('scrape_jobs', source='fixture-source')

        self.assertEqual(Job.objects.count(), 2)
        self.assertEqual(ScrapeRun.objects.count(), 1)

    def test_command_rejects_disabled_selected_source(self):
        self.source.is_enabled = False
        self.source.save(update_fields=['is_enabled'])

        with self.assertRaisesMessage(CommandError, 'Enabled source not found: fixture-source'):
            call_command('scrape_jobs', source='fixture-source')


class JobApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.source = JobSource.objects.create(
            name='Fixture Source',
            slug='fixture-source',
            base_url='https://fixture.example.com',
        )
        self.other_source = JobSource.objects.create(
            name='Hidden Source',
            slug='hidden-source',
            base_url='https://hidden.example.com',
            is_enabled=False,
        )
        self.lahore_job = Job.objects.create(
            source=self.source,
            title='Django Developer',
            company_name='Example Tech',
            location_text='Lahore',
            description='Build Python APIs.',
            job_type=Job.JobType.FULL_TIME,
            workplace_type=Job.WorkplaceType.HYBRID,
            source_url='https://fixture.example.com/jobs/1',
            fingerprint='api-fingerprint-1',
        )
        Job.objects.create(
            source=self.source,
            title='QA Intern',
            company_name='Testing Labs',
            location_text='Karachi',
            description='Learn software testing.',
            job_type=Job.JobType.INTERNSHIP,
            workplace_type=Job.WorkplaceType.ONSITE,
            source_url='https://fixture.example.com/jobs/2',
            fingerprint='api-fingerprint-2',
        )
        Job.objects.create(
            source=self.other_source,
            title='Inactive Source Job',
            company_name='Hidden Co',
            location_text='Lahore',
            source_url='https://hidden.example.com/jobs/1',
            fingerprint='api-fingerprint-3',
        )

    def test_job_list_is_paginated_and_active(self):
        response = self.client.get('/api/jobs/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['source']['slug'], 'fixture-source')

    def test_job_filters_and_search(self):
        response = self.client.get(
            '/api/jobs/',
            {
                'location': 'lahore',
                'job_type': 'full_time',
                'search': 'python',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Django Developer')

    def test_job_detail_and_read_only_behavior(self):
        response = self.client.get(f'/api/jobs/{self.lahore_job.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['salary']['currency'], '')

        response = self.client.post('/api/jobs/', {})
        self.assertEqual(response.status_code, 405)

    def test_sources_only_include_enabled_sources(self):
        response = self.client.get('/api/sources/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [
            {'slug': 'fixture-source', 'name': 'Fixture Source'},
        ])

    def test_missing_job_returns_not_found(self):
        response = self.client.get('/api/jobs/99999/')

        self.assertEqual(response.status_code, 404)
