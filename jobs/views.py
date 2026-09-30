from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics

from .filters import JobFilter
from .models import Job, JobSource
from .serializers import JobSerializer, JobSourceSerializer


class JobListView(generics.ListAPIView):
    queryset = Job.objects.select_related('source').filter(
        is_active=True,
        source__is_enabled=True,
    )
    serializer_class = JobSerializer
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_class = JobFilter
    search_fields = ('title', 'company_name', 'description')
    ordering_fields = ('posted_at', 'first_seen_at', 'last_seen_at')
    ordering = ('-posted_at', '-first_seen_at')


class JobDetailView(generics.RetrieveAPIView):
    queryset = Job.objects.select_related('source').filter(
        is_active=True,
        source__is_enabled=True,
    )
    serializer_class = JobSerializer


class JobSourceListView(generics.ListAPIView):
    queryset = JobSource.objects.filter(is_enabled=True)
    serializer_class = JobSourceSerializer
    pagination_class = None
