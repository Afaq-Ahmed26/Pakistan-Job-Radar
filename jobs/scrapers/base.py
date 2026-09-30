from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable

import requests
from django.conf import settings


@dataclass(frozen=True)
class NormalizedJob:
    title: str
    company_name: str
    location_text: str
    source_url: str
    external_id: str = ''
    description: str = ''
    salary_text: str = ''
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str = ''
    job_type: str = ''
    workplace_type: str = ''
    posted_at: datetime | None = None
    expires_at: datetime | None = None


class BaseJobSourceAdapter(ABC):
    source_slug: str

    def __init__(
        self,
        *,
        timeout: int | None = None,
        user_agent: str | None = None,
    ):
        self.timeout = timeout or int(
            getattr(settings, 'SCRAPER_TIMEOUT_SECONDS', 15)
        )
        self.user_agent = user_agent or getattr(
            settings,
            'SCRAPER_USER_AGENT',
            'PakistanJobRadar/0.1',
        )

    @abstractmethod
    def fetch(self) -> str:
        """Fetch raw source content."""

    @abstractmethod
    def parse(self, raw_content: str) -> Iterable[NormalizedJob]:
        """Parse raw source content into normalized jobs."""

    def fetch_with_requests(self, url: str) -> str:
        response = requests.get(
            url,
            headers={'User-Agent': self.user_agent},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.text


def read_fixture(path: Path) -> str:
    return path.read_text(encoding='utf-8')
