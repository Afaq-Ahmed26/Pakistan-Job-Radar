from rest_framework import serializers

from .models import Job, JobSource


class JobSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSource
        fields = ('slug', 'name')


class JobSerializer(serializers.ModelSerializer):
    location = serializers.CharField(source='location_text')
    source = JobSourceSerializer(read_only=True)
    salary = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = (
            'id',
            'title',
            'company_name',
            'location',
            'description',
            'salary',
            'job_type',
            'workplace_type',
            'source',
            'source_url',
            'posted_at',
            'first_seen_at',
            'last_seen_at',
        )

    def get_salary(self, job):
        return {
            'text': job.salary_text,
            'min': job.salary_min,
            'max': job.salary_max,
            'currency': job.salary_currency,
        }
