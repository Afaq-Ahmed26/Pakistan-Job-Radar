from django.core.management.base import BaseCommand, CommandError

from jobs.models import JobSource, ScrapeRun
from jobs.scrapers.fixture import FixtureAdapter
from jobs.services import run_adapter


class Command(BaseCommand):
    help = 'Import jobs from one source or all enabled sources.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            dest='source_slug',
            help='Run only the source with this slug.',
        )

    def handle(self, *args, **options):
        source_slug = options['source_slug']
        sources = self._get_sources(source_slug)

        if not sources:
            self.stdout.write('No enabled job sources found.')
            return

        failed_runs = 0
        for source in sources:
            scrape_run = run_adapter(source, self._get_adapter(source))
            status = (
                self.style.ERROR('FAILED')
                if scrape_run.status == ScrapeRun.Status.FAILED
                else self.style.SUCCESS('SUCCEEDED')
            )
            self.stdout.write(
                f'{status} {source.slug}: '
                f'seen={scrape_run.jobs_seen}, '
                f'created={scrape_run.jobs_created}, '
                f'updated={scrape_run.jobs_updated}, '
                f'skipped={scrape_run.jobs_skipped}'
            )
            if scrape_run.status == ScrapeRun.Status.FAILED:
                failed_runs += 1

        if failed_runs:
            raise CommandError(f'{failed_runs} source run(s) failed.')

    def _get_sources(self, source_slug):
        if source_slug:
            try:
                source = JobSource.objects.get(
                    slug=source_slug,
                    is_enabled=True,
                )
            except JobSource.DoesNotExist as exc:
                raise CommandError(
                    f'Enabled source not found: {source_slug}'
                ) from exc
            return [source]

        return list(JobSource.objects.filter(is_enabled=True))

    @staticmethod
    def _get_adapter(source):
        if source.source_type == JobSource.SourceType.FIXTURE:
            return FixtureAdapter()
        raise CommandError(
            f'No adapter is registered for source type: {source.source_type}'
        )
