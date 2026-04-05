from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.users.permissions import IsClient
from apps.payments.models import Payment, PaymentStatus
from apps.payments.serializers import PaymentSerializer, PaymentIntentSerializer, PaymentConfirmSerializer
from apps.payments.stripe_service import StripeService
from apps.assignments.models import Assignment, AssignmentStatus
from django.utils import timezone


@api_view(['POST'])
@permission_classes([IsClient])
def create_payment_intent(request):
    """
    Crear PaymentIntent en Stripe para que el cliente pague el servicio.
    """
    serializer = PaymentIntentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    assignment_id = serializer.validated_data['assignment_id']

    try:
        assignment = Assignment.objects.select_related('incident', 'payment').get(id=assignment_id)
    except Assignment.DoesNotExist:
        return Response({'error': 'Asignación no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    # Verificar que el cliente es dueño del incidente
    if assignment.incident.client != request.user.client_profile:
        return Response({'error': 'No tienes acceso a esta asignación'}, status=status.HTTP_403_FORBIDDEN)

    # Verificar que el servicio esté completado
    if assignment.status != AssignmentStatus.COMPLETED:
        return Response({'error': 'El servicio aún no está completado'}, status=status.HTTP_400_BAD_REQUEST)

    # Verificar que exista un pago asociado
    try:
        payment = assignment.payment
    except Payment.DoesNotExist:
        return Response({'error': 'No hay un pago asociado a esta asignación'}, status=status.HTTP_400_BAD_REQUEST)

    # Si ya fue pagado
    if payment.status in [PaymentStatus.CLIENT_PAID, PaymentStatus.COMMISSION_SETTLED]:
        return Response({'error': 'Este servicio ya fue pagado'}, status=status.HTTP_400_BAD_REQUEST)

    # Obtener stripe_customer_id del cliente
    client_profile = request.user.client_profile
    stripe_customer_id = client_profile.stripe_customer_id if client_profile.stripe_customer_id else None

    # Crear PaymentIntent
    stripe_service = StripeService()
    result = stripe_service.create_payment_intent(
        amount_usd=float(payment.total_amount),
        customer_id=stripe_customer_id if stripe_customer_id else '',
        metadata={
            'payment_id': str(payment.id),
            'assignment_id': str(assignment.id),
            'incident_id': str(assignment.incident.id),
            'client_email': request.user.email,
        }
    )

    if 'error' in result:
        return Response({'error': result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Guardar el payment_intent_id
    payment.stripe_payment_intent_id = result['payment_intent_id']
    payment.save()

    return Response({
        'client_secret': result['client_secret'],
        'payment_intent_id': result['payment_intent_id'],
        'amount': payment.total_amount,
    })


@api_view(['POST'])
@permission_classes([IsClient])
def confirm_payment(request):
    """
    Confirmar que el pago fue exitoso (webhook alternativo desde cliente).
    Normalmente se maneja con webhook de Stripe, pero esto es un respaldo.
    """
    serializer = PaymentConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    payment_intent_id = serializer.validated_data['payment_intent_id']

    try:
        payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
    except Payment.DoesNotExist:
        return Response({'error': 'Pago no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    # Verificar que el cliente es dueño
    if payment.assignment.incident.client != request.user.client_profile:
        return Response({'error': 'No tienes acceso a este pago'}, status=status.HTTP_403_FORBIDDEN)

    # Marcar como pagado
    if payment.status == PaymentStatus.PENDING:
        payment.status = PaymentStatus.CLIENT_PAID
        payment.paid_at = timezone.now()
        payment.save()

        # Notificar al taller
        try:
            from apps.notifications.models import Notification, NotificationType
            from apps.notifications.firebase_service import FirebaseService

            workshop = payment.assignment.workshop
            owner_user = workshop.owner.user

            Notification.objects.create(
                user=owner_user,
                title='Pago recibido',
                body=f'Cliente pagó ${payment.total_amount} por servicio #{payment.assignment.incident.id}',
                notification_type=NotificationType.PAYMENT_CONFIRMED,
                incident=payment.assignment.incident,
                data={'payment_id': payment.id, 'amount': str(payment.total_amount)}
            )

            if owner_user.fcm_token:
                firebase = FirebaseService()
                firebase.send_notification(
                    token=owner_user.fcm_token,
                    title='Pago recibido',
                    body=f'${payment.total_amount} recibido',
                    data={'payment_id': str(payment.id), 'type': 'payment_confirmed'}
                )
        except Exception as e:
            print(f"Error sending notification: {e}")

    return Response({
        'message': 'Pago confirmado',
        'payment_id': payment.id,
        'status': payment.status,
    })


@api_view(['GET'])
@permission_classes([IsClient])
def payment_history(request):
    """Historial de pagos del cliente"""
    payments = Payment.objects.filter(
        assignment__incident__client=request.user.client_profile
    ).select_related('assignment', 'assignment__workshop').order_by('-created_at')

    data = []
    for payment in payments:
        data.append({
            'id': payment.id,
            'incident_id': payment.assignment.incident.id,
            'workshop_name': payment.assignment.workshop.name,
            'total_amount': payment.total_amount,
            'status': payment.get_status_display(),
            'paid_at': payment.paid_at,
            'created_at': payment.created_at,
        })

    return Response(data)


@api_view(['GET'])
@permission_classes([IsClient])
def payment_detail(request, pk):
    """Detalle de un pago"""
    try:
        payment = Payment.objects.select_related('assignment', 'assignment__workshop').get(id=pk)
    except Payment.DoesNotExist:
        return Response({'error': 'Pago no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    # Verificar acceso
    if payment.assignment.incident.client != request.user.client_profile:
        return Response({'error': 'No tienes acceso a este pago'}, status=status.HTTP_403_FORBIDDEN)

    serializer = PaymentSerializer(payment)
    return Response(serializer.data)
