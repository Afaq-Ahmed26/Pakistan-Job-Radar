from django.contrib import admin

from .models import Job, JobSource, ScrapeRun


@admin.register(JobSource)
class JobSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'source_type', 'is_enabled')
    list_filter = ('is_enabled', 'source_type')
    search_fields = ('name', 'slug', 'base_url')


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'company_name',
        'location_text',
        'job_type',
        'workplace_type',
        'is_active',
        'last_seen_at',
    )
    list_filter = ('is_active', 'job_type', 'workplace_type', 'source')
    search_fields = ('title', 'company_name', 'location_text', 'description')
    readonly_fields = ('first_seen_at', 'last_seen_at')


@admin.register(ScrapeRun)
class ScrapeRunAdmin(admin.ModelAdmin):
    list_display = (
        'source',
        'started_at',
        'finished_at',
        'status',
        'jobs_seen',
        'jobs_created',
        'jobs_updated',
        'jobs_skipped',
    )
    list_filter = ('status', 'source')
    readonly_fields = ('started_at',)
