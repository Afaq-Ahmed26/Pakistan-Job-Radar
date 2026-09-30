from django.db import models


class JobSource(models.Model):
    class SourceType(models.TextChoices):
        HTML = 'html', 'HTML'
        JSON = 'json', 'JSON'
        FIXTURE = 'fixture', 'Fixture'
        FEED = 'feed', 'Feed'

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=100, unique=True)
    base_url = models.URLField()
    is_enabled = models.BooleanField(default=True)
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.FIXTURE,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Job(models.Model):
    class JobType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full time'
        PART_TIME = 'part_time', 'Part time'
        CONTRACT = 'contract', 'Contract'
        INTERNSHIP = 'internship', 'Internship'
        TEMPORARY = 'temporary', 'Temporary'

    class WorkplaceType(models.TextChoices):
        ONSITE = 'onsite', 'Onsite'
        HYBRID = 'hybrid', 'Hybrid'
        REMOTE = 'remote', 'Remote'

    source = models.ForeignKey(
        JobSource,
        on_delete=models.CASCADE,
        related_name='jobs',
    )
    external_id = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    location_text = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    salary_text = models.CharField(max_length=255, blank=True)
    salary_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    salary_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    salary_currency = models.CharField(max_length=3, blank=True)
    job_type = models.CharField(
        max_length=20,
        choices=JobType.choices,
        blank=True,
    )
    workplace_type = models.CharField(
        max_length=20,
        choices=WorkplaceType.choices,
        blank=True,
    )
    source_url = models.URLField(max_length=500)
    posted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    fingerprint = models.CharField(max_length=64)

    class Meta:
        ordering = ['-posted_at', '-first_seen_at']
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'source_url'],
                name='unique_job_source_url',
            ),
            models.UniqueConstraint(
                fields=['source', 'external_id'],
                condition=~models.Q(external_id=''),
                name='unique_job_source_external_id',
            ),
            models.UniqueConstraint(
                fields=['source', 'fingerprint'],
                name='unique_job_source_fingerprint',
            ),
        ]
        indexes = [
            models.Index(fields=['location_text']),
            models.Index(fields=['company_name']),
            models.Index(fields=['job_type']),
            models.Index(fields=['workplace_type']),
            models.Index(fields=['is_active', '-posted_at']),
        ]

    def __str__(self):
        return f'{self.title} at {self.company_name}'


class ScrapeRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = 'running', 'Running'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'

    source = models.ForeignKey(
        JobSource,
        on_delete=models.CASCADE,
        related_name='scrape_runs',
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    jobs_seen = models.PositiveIntegerField(default=0)
    jobs_created = models.PositiveIntegerField(default=0)
    jobs_updated = models.PositiveIntegerField(default=0)
    jobs_skipped = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.source.name} - {self.started_at:%Y-%m-%d %H:%M}'
