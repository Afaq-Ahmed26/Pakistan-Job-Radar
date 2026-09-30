import django_filters

from .models import Job


class JobFilter(django_filters.FilterSet):
    location = django_filters.CharFilter(
        field_name='location_text',
        lookup_expr='icontains',
    )
    company = django_filters.CharFilter(
        field_name='company_name',
        lookup_expr='icontains',
    )
    source = django_filters.CharFilter(
        field_name='source__slug',
        lookup_expr='exact',
    )

    class Meta:
        model = Job
        fields = (
            'location',
            'company',
            'job_type',
            'workplace_type',
            'source',
        )
