from django.urls import path

from .views import JobDetailView, JobListView, JobSourceListView

app_name = 'jobs'

urlpatterns = [
    path('jobs/', JobListView.as_view(), name='job-list'),
    path('jobs/<int:pk>/', JobDetailView.as_view(), name='job-detail'),
    path('sources/', JobSourceListView.as_view(), name='source-list'),
]
