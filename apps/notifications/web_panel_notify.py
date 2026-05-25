"""
Entrega de notificaciones al panel web (taller + admin).
Usa BD + SSE + Web Push (VAPID). No invoca Firebase ni fcm_token.
"""
import logging

from apps.notifications.models import Notification, NotificationType
from apps.notifications.sse_views import notify_user
from apps.notifications.web_push_service import send_web_push_to_user
from apps.users.models import Role, User

logger = logging.getLogger(__name__)

WEB_PANEL_ROLES = ('workshop_owner', 'admin')


def send_web_push_only(*, user, title: str, body: str, data: dict | None = None) -> int:
    """Solo push web; el caller ya creó registro en BD y/o SSE (flujos móvil existentes)."""
    if user.role not in WEB_PANEL_ROLES:
        return 0
    return send_web_push_to_user(user, title, body, data)


def deliver_to_web_panel_user(
    *,
    user,
    title: str,
    body: str,
    notification_type: str,
    incident=None,
    data: dict | None = None,
    sse_payload: dict | None = None,
) -> None:
    """BD + SSE + Web Push para un usuario del panel."""
    if user.role not in WEB_PANEL_ROLES:
        return

    payload = data or {}
    Notification.objects.create(
        user=user,
        title=title,
        body=body,
        notification_type=notification_type,
        incident=incident,
        data=payload,
        push_sent=False,
    )
    stream_data = {
        'event': notification_type,
        'type': payload.get('type', notification_type),
        'title': title,
        'body': body,
        **payload,
    }
    if sse_payload:
        stream_data.update(sse_payload)
        stream_data.setdefault('title', title)
        stream_data.setdefault('body', body)
    notify_user(user.id, stream_data)
    send_web_push_to_user(user, title, body, payload)


def notify_web_panel_admins(
    *,
    title: str,
    body: str,
    notification_type: str,
    incident=None,
    data: dict | None = None,
    sse_payload: dict | None = None,
) -> None:
    admins = User.objects.filter(role=Role.ADMIN, is_active=True)
    for admin in admins:
        try:
            deliver_to_web_panel_user(
                user=admin,
                title=title,
                body=body,
                notification_type=notification_type,
                incident=incident,
                data=data,
                sse_payload=sse_payload,
            )
        except Exception as exc:
            logger.warning('notify admin %s failed: %s', admin.id, exc)
