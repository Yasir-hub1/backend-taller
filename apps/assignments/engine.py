from geopy.distance import geodesic
from django.conf import settings
from apps.workshops.models import Workshop
from apps.assignments.models import Assignment
from decimal import Decimal


def _workshop_handles_incident_type(workshop, incident_type: str) -> bool:
    """
    Comprueba si el taller puede atender el tipo de incidente.
    'uncertain' y 'other' no filtran por rubro (cualquier taller con equipo puede recibir la oferta).
    """
    it = (incident_type or '').strip().lower()
    if it in ('uncertain', 'other', ''):
        return True
    services = workshop.services or []
    if not isinstance(services, list):
        return False
    if len(services) == 0:
        return True
    if 'general' in services:
        return True
    return it in services


class AssignmentEngine:
    """
    Motor inteligente de asignación de talleres a incidentes.
    """

    @staticmethod
    def find_and_notify_workshops(incident) -> list:
        """
        Encuentra talleres candidatos según:
        - Distancia al incidente (dentro del radio de servicio del taller)
        - Tipo de servicio requerido
        - Taller activo y verificado
        - Disponibilidad de técnicos

        Retorna lista de talleres ordenados por score.
        """
        incident_location = (float(incident.latitude), float(incident.longitude))

        qs = Workshop.objects.filter(is_active=True)
        if not getattr(settings, 'ASSIGNMENT_ALLOW_UNVERIFIED', False):
            qs = qs.filter(is_verified=True)
        workshops = qs.prefetch_related('technicians')

        candidates = []

        for workshop in workshops:
            # Verificar si el taller tiene técnicos disponibles
            has_available_tech = workshop.technicians.filter(is_available=True).exists()
            if not has_available_tech:
                continue

            incident_type = str(incident.incident_type or '').strip()
            if not _workshop_handles_incident_type(workshop, incident_type):
                continue

            # Calcular distancia
            workshop_location = (float(workshop.latitude), float(workshop.longitude))
            distance_km = geodesic(incident_location, workshop_location).km

            # Verificar si está dentro del radio de servicio (cap máximo 20km)
            max_radius_km = min(float(workshop.radius_km), 20.0)
            if distance_km > max_radius_km:
                continue

            # Score: menor distancia + mayor rating = mejor score
            # Formula: (1 / (distancia + 0.1)) * rating
            score = (1 / (distance_km + 0.1)) * float(workshop.rating_avg or 3.0)

            candidates.append({
                'workshop': workshop,
                'distance_km': round(distance_km, 2),
                'score': score,
            })

        # Ordenar por score descendente
        candidates.sort(key=lambda x: x['score'], reverse=True)

        # Tomar los top 5 candidatos
        top_candidates = candidates[:5]

        # Crear assignments en estado 'offered' y notificar (idempotente por incidente+taller)
        for candidate in top_candidates:
            w = candidate['workshop']
            if Assignment.objects.filter(incident=incident, workshop=w).exists():
                continue
            assignment_row = Assignment.objects.create(
                incident=incident,
                workshop=w,
                distance_km=Decimal(str(candidate['distance_km'])),
                status='offered',
            )

            # Notificar al dueño del taller (Firebase push)
            try:
                owner_user = candidate['workshop'].owner.user

                # Solo enviar notificación si hay token FCM
                if owner_user.fcm_token:
                    from apps.notifications.firebase_service import FirebaseService
                    firebase = FirebaseService()
                    firebase.send_notification(
                        token=owner_user.fcm_token,
                        title='Nueva solicitud de emergencia',
                        body=f"Incidente tipo {incident.get_incident_type_display()} a {candidate['distance_km']} km",
                        data={
                            'incident_id': str(incident.id),
                            'type': 'new_request',
                            'distance_km': str(candidate['distance_km'])
                        },
                    )

                # Crear notificación en BD
                from apps.notifications.models import Notification, NotificationType
                Notification.objects.create(
                    user=owner_user,
                    title='Nueva solicitud de emergencia',
                    body=f"Incidente tipo {incident.get_incident_type_display()} a {candidate['distance_km']} km",
                    notification_type=NotificationType.NEW_REQUEST,
                    incident=incident,
                    data={
                        'incident_id': incident.id,
                        'distance_km': candidate['distance_km']
                    },
                    push_sent=bool(owner_user.fcm_token)
                )

                from apps.notifications.sse_views import notify_user
                notify_user(owner_user.id, {
                    'event': 'new_assignment_offer',
                    'incident_id': incident.id,
                    'assignment_id': assignment_row.id,
                    'distance_km': float(candidate['distance_km']),
                })

            except Exception as e:
                print(f"Error sending notification to workshop {candidate['workshop'].id}: {e}")

        if not top_candidates:
            print(
                f"[AssignmentEngine] Sin candidatos para incidente {incident.id}: "
                f"talleres activos={'+unverif' if getattr(settings, 'ASSIGNMENT_ALLOW_UNVERIFIED', False) else 'verif.'}, "
                f"tipo={incident.incident_type}, ubicación=({incident.latitude},{incident.longitude}). "
                "Revisa: técnicos disponibles, radio_km, services que incluyan el tipo o 'general', "
                "y que django-q (qcluster) esté ejecutando el pipeline."
            )

        return top_candidates
