# Pakistan Job Radar

Pakistan Job Radar is a Django portfolio project that imports job listings
from permitted sources, normalizes them, stores them in PostgreSQL, and
exposes them through Django Admin and a read-only REST API.

The MVP uses a local HTML fixture so the complete ingestion flow is
deterministic and does not depend on a live job board.

## Features

- Django 5 and Django REST Framework
- PostgreSQL for Docker-backed development
- Pluggable source adapters
- BeautifulSoup HTML parsing
- Deterministic deduplication and idempotent ingestion
- Scrape-run history and per-record validation
- Read-only, paginated API with filtering, search, and ordering
- Django Admin for stored jobs and source-run inspection

## Requirements

- Python 3.12 or later
- Docker and Docker Compose for the PostgreSQL workflow

## Local setup

Create the virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The application uses SQLite automatically when `DATABASE_URL` is not set.
Apply migrations and run the local checks:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
.venv/bin/python manage.py test
```

Start Django:

```bash
.venv/bin/python manage.py runserver
```

The local server is available at <http://127.0.0.1:8000/>.

## Docker and PostgreSQL

Build the application image:

```bash
docker compose build
```

Start PostgreSQL and Django:

```bash
docker compose up -d
```

The web container waits for PostgreSQL, applies migrations, and starts Django
on <http://127.0.0.1:8000/>.

Check the service status and migration state:

```bash
docker compose ps
docker compose exec web python manage.py showmigrations
```

Stop the services without removing the PostgreSQL volume:

```bash
docker compose down
```

To remove the database volume as well when resetting local Docker data:

```bash
docker compose down -v
```

## Fixture ingestion

Create the fixture source in the active database:

```bash
docker compose exec web python manage.py shell -c \
  "from jobs.models import JobSource; JobSource.objects.get_or_create(
  slug='fixture-source',
  defaults={
    'name': 'Fixture Source',
    'base_url': 'https://fixture.example.com',
    'source_type': 'fixture',
  }
  )"
```

Run the fixture adapter:

```bash
docker compose exec web python manage.py scrape_jobs \
  --source fixture-source
```

Expected summary:

```text
SUCCEEDED fixture-source: seen=2, created=2, updated=0, skipped=0
```

Running the command again updates the existing jobs instead of creating
duplicates.

## API

The API is read-only. It does not trigger scraping and does not expose
database or scraper credentials.

List jobs:

```bash
curl http://127.0.0.1:8000/api/jobs/
```

Filter and search:

```bash
curl \
  'http://127.0.0.1:8000/api/jobs/?location=Lahore&job_type=full_time&search=python'
```

Retrieve one job:

```bash
curl http://127.0.0.1:8000/api/jobs/1/
```

List enabled sources:

```bash
curl http://127.0.0.1:8000/api/sources/
```

Supported job-list query parameters include `location`, `company`, `job_type`,
`workplace_type`, `source`, `search`, `ordering`, and `page`.

## Admin

Create a local administrator:

```bash
docker compose exec web python manage.py createsuperuser
```

Then open <http://127.0.0.1:8000/admin/>. Admin access is protected by
Django authentication and is separate from the public read-only API.

## Tests

Run the complete test suite locally:

```bash
.venv/bin/python manage.py test
```

The tests cover model constraints, fixture parsing, request timeout behavior,
ingestion validation, deduplication, scrape-run failures, management-command
execution, API filtering, pagination, and read-only behavior.

## Project boundaries

- Only permitted sources or local fixtures should be enabled.
- The project does not bypass logins, CAPTCHAs, anti-bot systems, rate limits,
  or other access controls.
- LinkedIn and sources whose terms prohibit automated extraction are excluded.
- Scraped descriptions are stored and returned as untrusted text.
- Scraping runs through a management command, not a public HTTP endpoint.

## Architecture

```text
Source adapter -> normalized job -> validation/deduplication
               -> Django ORM -> PostgreSQL
                              -> Admin and REST API
```

Source-specific parsing lives under `jobs/scrapers/`. Persistence and
deduplication live in `jobs/services.py`. The management command is
`jobs/management/commands/scrape_jobs.py`.