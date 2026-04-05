from geopy.distance import geodesic
from apps.workshops.models import Workshop
from apps.assignments.models import Assignment
from decimal import Decimal


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

        workshops = Workshop.objects.filter(
            is_active=True,
            is_verified=True,
        ).prefetch_related('technicians')

        candidates = []

        for workshop in workshops:
            # Verificar si el taller tiene técnicos disponibles
            has_available_tech = workshop.technicians.filter(is_available=True).exists()
            if not has_available_tech:
                continue

            # Verificar que el incidente cabe en el tipo de servicio
            incident_type = incident.incident_type
            if incident_type not in workshop.services and 'general' not in workshop.services:
                continue

            # Calcular distancia
            workshop_location = (float(workshop.latitude), float(workshop.longitude))
            distance_km = geodesic(incident_location, workshop_location).km

            # Verificar si está dentro del radio de servicio
            if distance_km > workshop.radius_km:
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

        # Crear assignments en estado 'offered' y notificar
        for candidate in top_candidates:
            Assignment.objects.create(
                incident=incident,
                workshop=candidate['workshop'],
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

            except Exception as e:
                print(f"Error sending notification to workshop {candidate['workshop'].id}: {e}")

        return top_candidates
