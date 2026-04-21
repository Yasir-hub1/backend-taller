from django.urls import path

from apps.assignments import views_technician

app_name = 'technician'

technician_app_patterns = [
    path('assignments/', views_technician.list_assignments, name='assignments-list'),
    path('assignments/<int:pk>/', views_technician.assignment_detail, name='assignments-detail'),
    path('assignments/<int:pk>/status/', views_technician.update_assignment_status, name='assignments-status'),
]
