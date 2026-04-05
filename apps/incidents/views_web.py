from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.incidents.models import Incident, IncidentStatus, IncidentStatusHistory
from apps.incidents.serializers import IncidentSerializer, IncidentDetailSerializer, IncidentStatusUpdateSerializer, IncidentCompleteSerializer
from apps.assignments.models import Assignment, AssignmentStatus
from apps.users.permissions import IsWorkshopOwner
from apps.workshops.models import Workshop
from django.utils import timezone


@api_view(['GET'])
@permission_classes([IsWorkshopOwner])
def available_incidents(request):
    """Solicitudes de emergencia disponibles para el taller"""
    try:
        workshop = Workshop.objects.get(owner=request.user.owner_profile)
    except Workshop.DoesNotExist:
        return Response({'error': 'No tienes un taller registrado'}, status=status.HTTP_404_NOT_FOUND)

    # Buscar assignments ofrecidas a este taller
    assignments = Assignment.objects.filter(
        workshop=workshop,
        status=AssignmentStatus.OFFERED
    ).select_related('incident', 'incident__client', 'incident__vehicle').order_by('-offered_at')

    incidents_data = []
    for assignment in assignments:
        incident = assignment.incident
        incidents_data.append({
            'assignment_id': assignment.id,
            'incident_id': incident.id,
            'client_name': incident.client.user.get_full_name(),
            'vehicle': f"{incident.vehicle.brand} {incident.vehicle.model}" if incident.vehicle else None,
            'incident_type': incident.get_incident_type_display(),
            'priority': incident.get_priority_display() if incident.priority else None,
            'description': incident.description,
            'address': incident.address_text,
            'distance_km': assignment.distance_km,
            'ai_summary': incident.ai_summary,
            'ai_confidence': incident.ai_confidence,
            'created_at': incident.created_at,
            'offered_at': assignment.offered_at,
        })

    return Response(incidents_data)


@api_view(['GET'])
@permission_classes([IsWorkshopOwner])
def incident_detail(request, pk):
    """Detalle del incidente con resumen IA"""
    try:
        workshop = Workshop.objects.get(owner=request.user.owner_profile)
    except Workshop.DoesNotExist:
        return Response({'error': 'No tienes un taller registrado'}, status=status.HTTP_404_NOT_FOUND)

    # Verificar que el taller tiene acceso a este incidente
    assignment = Assignment.objects.filter(
        workshop=workshop,
        incident_id=pk
    ).first()

    if not assignment:
        return Response({'error': 'No tienes acceso a este incidente'}, status=status.HTTP_403_FORBIDDEN)

    try:
        incident = Incident.objects.get(id=pk)
    except Incident.DoesNotExist:
        return Response({'error': 'Incidente no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    serializer = IncidentDetailSerializer(incident)
    data = serializer.data
    data['assignment'] = {
        'id': assignment.id,
        'status': assignment.status,
        'distance_km': assignment.distance_km,
        'technician': assignment.technician.name if assignment.technician else None,
    }
    return Response(data)


@api_view(['POST'])
@permission_classes([IsWorkshopOwner])
def accept_incident(request, pk):
    """Aceptar incidente y asignar técnico"""
    try:
        workshop = Workshop.objects.get(owner=request.user.owner_profile)
    except Workshop.DoesNotExist:
        return Response({'error': 'No tienes un taller registrado'}, status=status.HTTP_404_NOT_FOUND)

    # Buscar assignment ofrecida
    assignment = Assignment.objects.filter(
        workshop=workshop,
        incident_id=pk,
        status=AssignmentStatus.OFFERED
    ).first()

    if not assignment:
        return Response({'error': 'No se encontró la asignación o ya fue procesada'}, status=status.HTTP_404_NOT_FOUND)

    technician_id = request.data.get('technician_id')
    if not technician_id:
        return Response({'error': 'Debes seleccionar un técnico'}, status=status.HTTP_400_BAD_REQUEST)

    # Verificar que el técnico pertenece al taller
    technician = workshop.technicians.filter(id=technician_id, is_available=True).first()
    if not technician:
        return Response({'error': 'Técnico no encontrado o no disponible'}, status=status.HTTP_400_BAD_REQUEST)

    # Aceptar assignment
    assignment.technician = technician
    assignment.status = AssignmentStatus.ACCEPTED
    assignment.accepted_at = timezone.now()
    assignment.save()

    # Actualizar incidente
    incident = assignment.incident
    incident.status = IncidentStatus.ASSIGNED
    incident.save()

    # Crear historial
    IncidentStatusHistory.objects.create(
        incident=incident,
        previous_status=IncidentStatus.WAITING_WORKSHOP,
        new_status=IncidentStatus.ASSIGNED,
        changed_by=request.user,
        notes=f'Taller {workshop.name} aceptó el incidente. Técnico: {technician.name}'
    )

    # Rechazar otros assignments ofrecidos
    Assignment.objects.filter(
        incident=incident,
        status=AssignmentStatus.OFFERED
    ).exclude(id=assignment.id).update(
        status=AssignmentStatus.REJECTED,
        rejection_reason='Otro taller aceptó primero'
    )

    # Notificar al cliente
    try:
        from apps.notifications.models import Notification, NotificationType
        from apps.notifications.firebase_service import FirebaseService

        client_user = incident.client.user
        Notification.objects.create(
            user=client_user,
            title='Taller asignado',
            body=f'{workshop.name} atenderá tu emergencia. Técnico: {technician.name}',
            notification_type=NotificationType.WORKSHOP_ASSIGNED,
            incident=incident,
            data={'assignment_id': assignment.id, 'workshop_name': workshop.name}
        )

        if client_user.fcm_token:
            firebase = FirebaseService()
            firebase.send_notification(
                token=client_user.fcm_token,
                title='Taller asignado',
                body=f'{workshop.name} atenderá tu emergencia',
                data={'incident_id': str(incident.id), 'type': 'workshop_assigned'}
            )
    except Exception as e:
        print(f"Error sending notification: {e}")

    return Response({
        'message': 'Incidente aceptado exitosamente',
        'assignment_id': assignment.id,
        'incident_id': incident.id
    })


@api_view(['POST'])
@permission_classes([IsWorkshopOwner])
def reject_incident(request, pk):
    """Rechazar incidente con motivo"""
    try:
        workshop = Workshop.objects.get(owner=request.user.owner_profile)
    except Workshop.DoesNotExist:
        return Response({'error': 'No tienes un taller registrado'}, status=status.HTTP_404_NOT_FOUND)

    assignment = Assignment.objects.filter(
        workshop=workshop,
        incident_id=pk,
        status=AssignmentStatus.OFFERED
    ).first()

    if not assignment:
        return Response({'error': 'No se encontró la asignación'}, status=status.HTTP_404_NOT_FOUND)

    reason = request.data.get('reason', 'No especificado')
    assignment.status = AssignmentStatus.REJECTED
    assignment.rejection_reason = reason
    assignment.save()

    return Response({'message': 'Incidente rechazado'})


@api_view(['PATCH'])
@permission_classes([IsWorkshopOwner])
def update_incident_status(request, pk):
    """Actualizar estado del servicio (en ruta, llegó, en servicio)"""
    try:
        workshop = Workshop.objects.get(owner=request.user.owner_profile)
    except Workshop.DoesNotExist:
        return Response({'error': 'No tienes un taller registrado'}, status=status.HTTP_404_NOT_FOUND)

    assignment = Assignment.objects.filter(
        workshop=workshop,
        incident_id=pk,
        status__in=[AssignmentStatus.ACCEPTED, AssignmentStatus.IN_ROUTE,
                   AssignmentStatus.ARRIVED, AssignmentStatus.IN_SERVICE]
    ).first()

    if not assignment:
        return Response({'error': 'No tienes una asignación activa para este incidente'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    valid_statuses = ['in_route', 'arrived', 'in_service']

    if new_status not in valid_statuses:
        return Response({'error': 'Estado inválido'}, status=status.HTTP_400_BAD_REQUEST)

    # Actualizar assignment
    assignment.status = new_status
    assignment.save()

    # Actualizar incidente si corresponde
    incident = assignment.incident
    if new_status == 'in_service':
        incident.status = IncidentStatus.IN_PROGRESS
        incident.save()

        IncidentStatusHistory.objects.create(
            incident=incident,
            previous_status=IncidentStatus.ASSIGNED,
            new_status=IncidentStatus.IN_PROGRESS,
            changed_by=request.user,
            notes='Servicio iniciado'
        )

    return Response({'message': 'Estado actualizado', 'new_status': new_status})


@api_view(['POST'])
@permission_classes([IsWorkshopOwner])
def complete_incident(request, pk):
    """Cerrar servicio e ingresar costo"""
    try:
        workshop = Workshop.objects.get(owner=request.user.owner_profile)
    except Workshop.DoesNotExist:
        return Response({'error': 'No tienes un taller registrado'}, status=status.HTTP_404_NOT_FOUND)

    assignment = Assignment.objects.filter(
        workshop=workshop,
        incident_id=pk,
        status__in=[AssignmentStatus.IN_SERVICE, AssignmentStatus.ARRIVED]
    ).first()

    if not assignment:
        return Response({'error': 'No tienes una asignación activa para este incidente'}, status=status.HTTP_404_NOT_FOUND)

    serializer = IncidentCompleteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    service_cost = serializer.validated_data['service_cost']
    notes = serializer.validated_data.get('notes', '')

    # Actualizar assignment
    assignment.status = AssignmentStatus.COMPLETED
    assignment.service_cost = service_cost
    assignment.completed_at = timezone.now()
    assignment.save()

    # Actualizar incidente
    incident = assignment.incident
    incident.status = IncidentStatus.COMPLETED
    incident.closed_at = timezone.now()
    incident.save()

    # Crear historial
    IncidentStatusHistory.objects.create(
        incident=incident,
        previous_status=IncidentStatus.IN_PROGRESS,
        new_status=IncidentStatus.COMPLETED,
        changed_by=request.user,
        notes=f'Servicio completado. Costo: ${service_cost}. {notes}'
    )

    # Actualizar estadísticas del taller
    workshop.total_services += 1
    workshop.save()

    # Crear pago
    try:
        from apps.payments.models import Payment, CommissionConfig, PaymentStatus
        from decimal import Decimal

        commission_config = CommissionConfig.objects.filter(is_active=True).order_by('-effective_from').first()
        commission_rate = commission_config.percentage if commission_config else Decimal('10.00')

        commission_amount = (service_cost * commission_rate) / Decimal('100')
        workshop_net = service_cost - commission_amount

        Payment.objects.create(
            assignment=assignment,
            commission_config=commission_config,
            total_amount=service_cost,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
            workshop_net_amount=workshop_net,
            status=PaymentStatus.PENDING
        )
    except Exception as e:
        print(f"Error creating payment: {e}")

    # Notificar al cliente
    try:
        from apps.notifications.models import Notification, NotificationType
        from apps.notifications.firebase_service import FirebaseService

        client_user = incident.client.user
        Notification.objects.create(
            user=client_user,
            title='Servicio completado',
            body=f'Tu emergencia ha sido resuelta. Total: ${service_cost}',
            notification_type=NotificationType.SERVICE_COMPLETED,
            incident=incident,
            data={'service_cost': str(service_cost)}
        )

        if client_user.fcm_token:
            firebase = FirebaseService()
            firebase.send_notification(
                token=client_user.fcm_token,
                title='Servicio completado',
                body=f'Emergencia resuelta. Total: ${service_cost}',
                data={'incident_id': str(incident.id), 'type': 'service_completed', 'cost': str(service_cost)}
            )
    except Exception as e:
        print(f"Error sending notification: {e}")

    return Response({
        'message': 'Servicio completado exitosamente',
        'service_cost': service_cost,
        'commission_rate': commission_rate,
    })


@api_view(['GET'])
@permission_classes([IsWorkshopOwner])
def incident_history(request):
    """Historial de servicios del taller"""
    try:
        workshop = Workshop.objects.get(owner=request.user.owner_profile)
    except Workshop.DoesNotExist:
        return Response({'error': 'No tienes un taller registrado'}, status=status.HTTP_404_NOT_FOUND)

    assignments = Assignment.objects.filter(
        workshop=workshop
    ).exclude(
        status=AssignmentStatus.OFFERED
    ).select_related('incident', 'technician').order_by('-offered_at')

    history_data = []
    for assignment in assignments:
        incident = assignment.incident
        history_data.append({
            'assignment_id': assignment.id,
            'incident_id': incident.id,
            'assignment_status': assignment.status,
            'status': assignment.get_status_display(),
            'incident_type': incident.get_incident_type_display(),
            'client_name': incident.client.user.get_full_name(),
            'technician': assignment.technician.name if assignment.technician else None,
            'service_cost': assignment.service_cost,
            'distance_km': assignment.distance_km,
            'offered_at': assignment.offered_at,
            'accepted_at': assignment.accepted_at,
            'completed_at': assignment.completed_at,
        })

    return Response(history_data)
