from django.urls import path
from apps.workshops import views_app, views_web, views_admin

app_name = 'workshops'

# App móvil - /api/app/workshops/
app_patterns = [
    path('nearby/', views_app.nearby_workshops, name='app-nearby'),
    path('<int:pk>/', views_app.workshop_detail, name='app-detail'),
    path('<int:pk>/rate/', views_app.rate_workshop, name='app-rate'),
]

# Web - /api/web/workshop/
web_patterns = [
    path('', views_web.workshop_detail, name='web-detail'),
    path('create/', views_web.workshop_create, name='web-create'),
    path('dashboard/', views_web.workshop_dashboard, name='web-dashboard'),
    path('earnings/', views_web.workshop_earnings, name='web-earnings'),

    # Técnicos
    path('technicians/', views_web.TechnicianViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='web-technicians-list'),
    path('technicians/<int:pk>/', views_web.TechnicianViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='web-technicians-detail'),
    path('technicians/<int:pk>/availability/', views_web.TechnicianViewSet.as_view({
        'patch': 'availability'
    }), name='web-technicians-availability'),
    path('technicians/<int:pk>/location/', views_web.TechnicianViewSet.as_view({
        'patch': 'location'
    }), name='web-technicians-location'),
]

# Admin - /api/admin-api/workshops/
admin_patterns = [
    path('', views_admin.WorkshopAdminViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='admin-list'),
    path('<int:pk>/', views_admin.WorkshopAdminViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='admin-detail'),
    path('<int:pk>/verify/', views_admin.WorkshopAdminViewSet.as_view({
        'patch': 'verify'
    }), name='admin-verify'),
    path('<int:pk>/toggle-active/', views_admin.WorkshopAdminViewSet.as_view({
        'patch': 'toggle_active'
    }), name='admin-toggle-active'),
]
