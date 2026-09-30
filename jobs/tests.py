from django.db import IntegrityError
from django.test import TestCase

from .models import Job, JobSource, ScrapeRun
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
