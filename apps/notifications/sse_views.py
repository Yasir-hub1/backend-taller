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
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from apps.incidents.models import Incident


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


@api_view(['GET'])
def incident_stream(request, incident_id: int):
    """
    SSE por incidente para clientes móviles.
    Acepta JWT por query param `token` para facilitar EventSource en React Native.
    """
    user = None

    # 1) Intentar auth estándar (Authorization: Bearer ...)
    if getattr(request, 'user', None) and request.user.is_authenticated:
        user = request.user

    # 2) Fallback: token por query param
    if user is None:
        raw_token = request.query_params.get('token')
        if not raw_token:
            return HttpResponse('Unauthorized', status=401)
        try:
            jwt_auth = JWTAuthentication()
            validated = jwt_auth.get_validated_token(raw_token)
            user = jwt_auth.get_user(validated)
        except (InvalidToken, AuthenticationFailed):
            return HttpResponse('Unauthorized', status=401)

    # Verificar que el incidente pertenezca al cliente autenticado
    exists = Incident.objects.filter(id=incident_id, client=user.client_profile).exists()
    if not exists:
        return HttpResponse('Forbidden', status=403)

    channel = f'incident-{incident_id}'
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
