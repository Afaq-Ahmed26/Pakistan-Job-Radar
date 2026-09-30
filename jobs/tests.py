from django.db import IntegrityError
from django.test import TestCase

from .models import Job, JobSource, ScrapeRun


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
