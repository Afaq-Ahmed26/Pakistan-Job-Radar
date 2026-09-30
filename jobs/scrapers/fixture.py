from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseJobSourceAdapter, NormalizedJob, read_fixture


class FixtureAdapter(BaseJobSourceAdapter):
    source_slug = 'fixture-source'

    def __init__(self, fixture_path: Path | None = None):
        super().__init__()
        self.fixture_path = fixture_path or (
            Path(__file__).resolve().parent.parent
            / 'tests'
            / 'fixtures'
            / 'fixture_jobs.html'
        )

    def fetch(self) -> str:
        return read_fixture(self.fixture_path)

    def parse(self, raw_content: str) -> Iterable[NormalizedJob]:
        soup = BeautifulSoup(raw_content, 'html.parser')
        for listing in soup.select('[data-job-id]'):
            title_element = listing.select_one('[data-field="title"]')
            company_element = listing.select_one('[data-field="company"]')
            location_element = listing.select_one('[data-field="location"]')
            link_element = listing.select_one('a[data-field="url"]')

            if not all(
                (title_element, company_element, location_element, link_element)
            ):
                continue

            yield NormalizedJob(
                external_id=listing['data-job-id'].strip(),
                title=title_element.get_text(' ', strip=True),
                company_name=company_element.get_text(' ', strip=True),
                location_text=location_element.get_text(' ', strip=True),
                description=self._text(listing, 'description'),
                salary_text=self._text(listing, 'salary'),
                job_type=self._text(listing, 'job-type'),
                workplace_type=self._text(listing, 'workplace-type'),
                source_url=urljoin(
                    'https://fixture.example.com',
                    link_element.get('href', ''),
                ),
            )

    @staticmethod
    def _text(listing, field_name: str) -> str:
        element = listing.select_one(f'[data-field="{field_name}"]')
        return element.get_text(' ', strip=True) if element else ''
