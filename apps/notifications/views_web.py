from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.users.permissions import IsAdminOrWorkshopOwner
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


@api_view(['GET'])
@permission_classes([IsAdminOrWorkshopOwner])
def unread_count_web(request):
    """Contador de notificaciones no leídas (panel taller / badge en tiempo real)."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({'unread_count': count})


@api_view(['GET'])
@permission_classes([IsAdminOrWorkshopOwner])
def notification_list(request):
    """Lista de notificaciones del panel web (taller o admin)"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminOrWorkshopOwner])
def mark_as_read(request, pk):
    """Marcar notificación como leída"""
    try:
        notification = Notification.objects.get(id=pk, user=request.user)
    except Notification.DoesNotExist:
        return Response({'error': 'Notificación no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    notification.is_read = True
    notification.save()

    return Response({'message': 'Notificación marcada como leída'})


@api_view(['POST'])
@permission_classes([IsAdminOrWorkshopOwner])
def mark_all_as_read(request):
    """Marcar todas las notificaciones como leídas"""
    updated_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    return Response({
        'message': f'{updated_count} notificaciones marcadas como leídas',
        'count': updated_count
    })
