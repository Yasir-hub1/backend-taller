from django.urls import path
from apps.payments import views_app, views_web, views_admin

app_name = 'payments'

# App móvil - /api/app/payments/
app_patterns = [
    path('create-intent/', views_app.create_payment_intent, name='app-create-intent'),
    path('confirm/', views_app.confirm_payment, name='app-confirm'),
    path('history/', views_app.payment_history, name='app-history'),
    path('<int:pk>/', views_app.payment_detail, name='app-detail'),
]

shared_patterns = [
    path('stripe/webhook/', views_app.stripe_webhook, name='stripe-webhook'),
]

# Web - /api/web/payments/
web_patterns = [
    path('earnings/', views_web.earnings_summary, name='web-earnings'),
    path('', views_web.payment_list, name='web-list'),
]

# Admin - /api/admin-api/
admin_patterns = [
    # Comisiones
    path('commission/', views_admin.CommissionConfigViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='admin-commission-list'),
    path('commission/<int:pk>/', views_admin.CommissionConfigViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='admin-commission-detail'),
    path('commission/current/', views_admin.CommissionConfigViewSet.as_view({
        'get': 'current'
    }), name='admin-commission-current'),

    # Pagos
    path('payments/', views_admin.PaymentAdminViewSet.as_view({
        'get': 'list'
    }), name='admin-payments-list'),
    path('payments/<int:pk>/', views_admin.PaymentAdminViewSet.as_view({
        'get': 'retrieve'
    }), name='admin-payments-detail'),

    # Métricas
    path('metrics/', views_admin.platform_metrics, name='admin-metrics'),
]
