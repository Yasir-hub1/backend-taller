from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from apps.users.permissions import IsAdmin
from apps.payments.models import Payment, CommissionConfig, PaymentStatus
from apps.payments.serializers import (
    PaymentSerializer, CommissionConfigSerializer, MetricsSerializer
)
from apps.users.models import User, Role
from apps.workshops.models import Workshop
from apps.incidents.models import Incident, IncidentStatus
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class CommissionConfigViewSet(viewsets.ModelViewSet):
    """Gestión de configuración de comisiones (solo admin)"""
    queryset = CommissionConfig.objects.all().order_by('-effective_from')
    serializer_class = CommissionConfigSerializer
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Obtener la configuración de comisión activa actual"""
        from datetime import date
        config = CommissionConfig.objects.filter(
            is_active=True,
            effective_from__lte=date.today()
        ).order_by('-effective_from').first()

        if config:
            serializer = CommissionConfigSerializer(config)
            return Response(serializer.data)
        return Response({'error': 'No hay configuración de comisión activa'}, status=status.HTTP_404_NOT_FOUND)


class PaymentAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """Visualización de todos los pagos (solo admin)"""
    queryset = Payment.objects.all().order_by('-created_at')
    serializer_class = PaymentSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['status']


@api_view(['GET'])
@permission_classes([IsAdmin])
def platform_metrics(request):
    """Métricas globales de la plataforma"""

    # Usuarios
    total_users = User.objects.count()
    total_clients = User.objects.filter(role=Role.CLIENT).count()
    total_workshops = Workshop.objects.count()

    # Incidentes
    total_incidents = Incident.objects.count()
    start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    incidents_this_month = Incident.objects.filter(created_at__gte=start_of_month).count()
    active_incidents = Incident.objects.filter(
        status__in=[IncidentStatus.PENDING, IncidentStatus.ANALYZING,
                   IncidentStatus.WAITING_WORKSHOP, IncidentStatus.ASSIGNED,
                   IncidentStatus.IN_PROGRESS]
    ).count()
    completed_incidents = Incident.objects.filter(status=IncidentStatus.COMPLETED).count()

    # Ingresos
    payments = Payment.objects.filter(
        status__in=[PaymentStatus.CLIENT_PAID, PaymentStatus.COMMISSION_SETTLED]
    )
    total_revenue = sum(p.total_amount for p in payments) if payments.exists() else Decimal('0.00')
    total_commission_earned = sum(p.commission_amount for p in payments) if payments.exists() else Decimal('0.00')

    data = {
        'total_users': total_users,
        'total_clients': total_clients,
        'total_workshops': total_workshops,
        'total_incidents': total_incidents,
        'incidents_this_month': incidents_this_month,
        'total_revenue': total_revenue,
        'total_commission_earned': total_commission_earned,
        'active_incidents': active_incidents,
        'completed_incidents': completed_incidents,
    }

    serializer = MetricsSerializer(data)
    return Response(serializer.data)
