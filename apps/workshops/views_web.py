from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from apps.workshops.models import Workshop, Technician
from apps.workshops.serializers import (
    WorkshopSerializer, WorkshopDetailSerializer, WorkshopCreateSerializer,
    WorkshopDashboardSerializer, TechnicianSerializer, TechnicianCreateSerializer,
    TechnicianAvailabilitySerializer, TechnicianLocationUpdateSerializer
)
from apps.users.permissions import IsWorkshopOwner
from apps.assignments.models import Assignment, AssignmentStatus
from apps.payments.models import Payment, PaymentStatus
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsWorkshopOwner])
def workshop_detail(request):
    """Obtener y actualizar datos del taller del dueño autenticado"""
    try:
        workshop = Workshop.objects.get(owner=request.user.owner_profile)
    except Workshop.DoesNotExist:
        return Response({'error': 'No tienes un taller registrado'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = WorkshopDetailSerializer(workshop)
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        serializer = WorkshopSerializer(workshop, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(WorkshopDetailSerializer(workshop).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsWorkshopOwner])
def workshop_create(request):
    """Crear taller (solo si no tiene uno)"""
    if Workshop.objects.filter(owner=request.user.owner_profile).exists():
        return Response({'error': 'Ya tienes un taller registrado'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = WorkshopCreateSerializer(data=request.data)
    if serializer.is_valid():
        workshop = serializer.save(owner=request.user.owner_profile)
        return Response(WorkshopDetailSerializer(workshop).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsWorkshopOwner])
def workshop_dashboard(request):
    """Métricas del taller: servicios, ingresos, calificación"""
    try:
        workshop = Workshop.objects.get(owner=request.user.owner_profile)
    except Workshop.DoesNotExist:
        return Response({'error': 'No tienes un taller registrado'}, status=status.HTTP_404_NOT_FOUND)

    # Estadísticas de assignments
    total_services = Assignment.objects.filter(
        workshop=workshop,
        status=AssignmentStatus.COMPLETED
    ).count()

    pending_requests = Assignment.objects.filter(
        workshop=workshop,
        status=AssignmentStatus.OFFERED
    ).count()

    active_services = Assignment.objects.filter(
        workshop=workshop,
        status__in=[AssignmentStatus.ACCEPTED, AssignmentStatus.IN_ROUTE,
                   AssignmentStatus.ARRIVED, AssignmentStatus.IN_SERVICE]
    ).count()

    # Servicios completados este mes
    start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    completed_this_month = Assignment.objects.filter(
        workshop=workshop,
        status=AssignmentStatus.COMPLETED,
        completed_at__gte=start_of_month
    ).count()

    # Ingresos totales (suma de workshop_net_amount)
    payments = Payment.objects.filter(
        assignment__workshop=workshop,
        status__in=[PaymentStatus.CLIENT_PAID, PaymentStatus.COMMISSION_SETTLED]
    )
    total_earnings = sum(p.workshop_net_amount for p in payments) if payments.exists() else Decimal('0.00')

    month_payments = Payment.objects.filter(
        assignment__workshop=workshop,
        status__in=[PaymentStatus.CLIENT_PAID, PaymentStatus.COMMISSION_SETTLED],
        paid_at__gte=start_of_month,
    )
    earnings_this_month = (
        sum(p.workshop_net_amount for p in month_payments) if month_payments.exists() else Decimal('0.00')
    )

    # Técnicos disponibles
    available_technicians = workshop.technicians.filter(is_available=True).count()

    data = {
        'total_services': total_services,
        'pending_requests': pending_requests,
        'active_services': active_services,
        'completed_this_month': completed_this_month,
        'rating_avg': workshop.rating_avg,
        'total_earnings': total_earnings,
        'earnings_this_month': earnings_this_month,
        'available_technicians': available_technicians,
    }

    serializer = WorkshopDashboardSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsWorkshopOwner])
def workshop_earnings(request):
    """Resumen de ingresos y comisiones del taller"""
    try:
        workshop = Workshop.objects.get(owner=request.user.owner_profile)
    except Workshop.DoesNotExist:
        return Response({'error': 'No tienes un taller registrado'}, status=status.HTTP_404_NOT_FOUND)

    payments = Payment.objects.filter(
        assignment__workshop=workshop,
        status__in=[PaymentStatus.CLIENT_PAID, PaymentStatus.COMMISSION_SETTLED]
    ).select_related('assignment').order_by('-created_at')

    total_gross = sum(p.total_amount for p in payments) if payments.exists() else Decimal('0.00')
    total_commission = sum(p.commission_amount for p in payments) if payments.exists() else Decimal('0.00')
    total_net = sum(p.workshop_net_amount for p in payments) if payments.exists() else Decimal('0.00')

    # Últimos pagos
    recent_payments = payments[:10]
    payments_data = []
    for payment in recent_payments:
        payments_data.append({
            'id': payment.id,
            'incident_id': payment.assignment.incident.id,
            'total_amount': payment.total_amount,
            'commission_amount': payment.commission_amount,
            'net_amount': payment.workshop_net_amount,
            'commission_rate': payment.commission_rate,
            'status': payment.status,
            'paid_at': payment.paid_at,
            'created_at': payment.created_at,
        })

    return Response({
        'summary': {
            'total_gross': total_gross,
            'total_commission': total_commission,
            'total_net': total_net,
            'total_payments': payments.count(),
        },
        'recent_payments': payments_data,
    })


class TechnicianViewSet(viewsets.ModelViewSet):
    """CRUD de técnicos del taller"""
    serializer_class = TechnicianSerializer
    permission_classes = [IsWorkshopOwner]

    def get_queryset(self):
        try:
            workshop = Workshop.objects.get(owner=self.request.user.owner_profile)
            return Technician.objects.filter(workshop=workshop).order_by('-id')
        except Workshop.DoesNotExist:
            return Technician.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return TechnicianCreateSerializer
        return TechnicianSerializer

    def perform_create(self, serializer):
        workshop = Workshop.objects.get(owner=self.request.user.owner_profile)
        serializer.save(workshop=workshop)

    @action(detail=True, methods=['patch'])
    def availability(self, request, pk=None):
        """Cambiar disponibilidad del técnico"""
        technician = self.get_object()
        serializer = TechnicianAvailabilitySerializer(data=request.data)
        if serializer.is_valid():
            technician.is_available = serializer.validated_data['is_available']
            technician.save()
            return Response(TechnicianSerializer(technician).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def location(self, request, pk=None):
        """Actualizar ubicación del técnico"""
        technician = self.get_object()
        serializer = TechnicianLocationUpdateSerializer(data=request.data)
        if serializer.is_valid():
            technician.current_latitude = serializer.validated_data['latitude']
            technician.current_longitude = serializer.validated_data['longitude']
            technician.last_location_update = timezone.now()
            technician.save()
            return Response(TechnicianSerializer(technician).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
