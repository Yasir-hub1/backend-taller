"""
Server-Sent Events usando django-eventstream.
El cliente Angular/Flutter se suscribe a este endpoint
y recibe actualizaciones en tiempo real.

django-eventstream usa la base de datos internamente (sin Redis).
"""
from django_eventstream import send_event
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django_eventstream.views import events as eventstream_events


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_stream(request):
    """
    SSE endpoint para notificaciones en tiempo real.
    El cliente se conecta a este endpoint y recibe eventos push.
    """
    # Canal único por usuario
    channel = f'user-{request.user.id}'
    return eventstream_events(request, [channel])


def notify_incident_update(incident_id: int, data: dict):
    """
    Emitir evento de actualización de incidente.
    Llamar desde cualquier parte del backend.
    """
    channel = f'incident-{incident_id}'
    send_event(channel, 'message', data)


def notify_user(user_id: int, data: dict):
    """
    Emitir evento a un usuario específico.
    Llamar desde cualquier parte del backend.
    """
    channel = f'user-{user_id}'
    send_event(channel, 'message', data)


def notify_workshop(workshop_id: int, data: dict):
    """
    Emitir evento a un taller específico.
    """
    channel = f'workshop-{workshop_id}'
    send_event(channel, 'message', data)
