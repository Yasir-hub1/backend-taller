from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Prefetch
from django.utils import timezone
from apps.incidents.models import Incident, Evidence, EvidenceType, IncidentStatus
from apps.assignments.models import Assignment, AssignmentStatus, ServiceQuote, ServiceQuoteStatus
from apps.assignments.serializers import ServiceQuoteSerializer
from apps.incidents.serializers import (
    IncidentSerializer, IncidentDetailSerializer, IncidentCreateSerializer,
    EvidenceSerializer, IncidentStatusHistorySerializer
)
from apps.users.permissions import IsClient
from tasks import enqueue_incident_pipeline


class IncidentViewSet(viewsets.ModelViewSet):
    """Gestión de incidentes del cliente"""
    permission_classes = [IsClient]

    def get_serializer_class(self):
        if self.action == 'create':
            return IncidentCreateSerializer
        elif self.action == 'retrieve':
            return IncidentDetailSerializer
        return IncidentSerializer

    def get_queryset(self):
        aq = Assignment.objects.select_related(
            'workshop', 'technician', 'client_rating', 'payment'
        )
        qs = (
            Incident.objects.filter(client=self.request.user.client_profile)
            .select_related('vehicle', 'client__user')
            .prefetch_related(Prefetch('assignments', queryset=aq))
        )
        # La app móvil envía ?status=a,b,c (p. ej. activos o un solo estado)
        raw = self.request.query_params.get('status')
        if raw:
            allowed = {c[0] for c in IncidentStatus.choices}
            statuses = [s for s in (p.strip() for p in raw.split(',')) if s and s in allowed]
            if statuses:
                qs = qs.filter(status__in=statuses)
        return qs.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """Idempotencia: client_request_id evita duplicar incidentes al sincronizar offline."""
        raw_id = (request.data.get('client_request_id') or '').strip()
        if raw_id:
            existing = Incident.objects.filter(
                client=request.user.client_profile,
                client_request_id=raw_id,
            ).first()
            if existing:
                out = IncidentCreateSerializer(existing, context={'request': request})
                return Response(out.data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        raw_id = (self.request.data.get('client_request_id') or '').strip() or None
        incident = serializer.save(
            client=self.request.user.client_profile,
            status=IncidentStatus.PENDING,
            client_request_id=raw_id,
        )
        # El pipeline IA + motor de asignación se ejecutan tras subir evidencias
        # (upload_evidence), cuando hay datos para clasificar y ofrecer talleres.

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_evidence(self, request, pk=None):
        """
        Subir evidencias desde la app móvil.
        Acepta multipart con claves repetidas `photos` (imágenes) y opcional `audio`.
        """
        incident = self.get_object()
        photos = request.FILES.getlist('photos')
        audio_file = request.FILES.get('audio')

        if not photos and not audio_file:
            return Response(
                {'error': 'Envía al menos una foto (photos) o un archivo de audio (audio).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        for f in photos:
            if not f:
                continue
            created.append(
                Evidence.objects.create(
                    incident=incident,
                    evidence_type=EvidenceType.IMAGE,
                    file=f,
                )
            )

        if audio_file:
            created.append(
                Evidence.objects.create(
                    incident=incident,
                    evidence_type=EvidenceType.AUDIO,
                    file=audio_file,
                )
            )

        if created:
            enqueue_incident_pipeline(incident.id)

        serializer = EvidenceSerializer(created, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def evidences(self, request, pk=None):
        """Listar evidencias del incidente"""
        incident = self.get_object()
        evidences = incident.evidences.all()
        serializer = EvidenceSerializer(evidences, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def assignment(self, request, pk=None):
        """Ver asignación activa del incidente"""
        incident = self.get_object()
        assignment = (
            incident.assignments.filter(status__in=['accepted', 'in_route', 'arrived', 'in_service'])
            .select_related('workshop', 'technician', 'client_rating', 'payment')
            .first()
        )
        if assignment:
            from apps.assignments.serializers import AssignmentDetailSerializer
            return Response(AssignmentDetailSerializer(assignment).data)
        return Response({'message': 'No hay asignación activa'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancelar incidente"""
        incident = self.get_object()
        if incident.status in [IncidentStatus.COMPLETED, IncidentStatus.CANCELLED]:
            return Response({'error': 'El incidente ya está finalizado'}, status=status.HTTP_400_BAD_REQUEST)

        incident.status = IncidentStatus.CANCELLED
        incident.save()
        return Response({'message': 'Incidente cancelado'})

    @action(detail=True, methods=['get'])
    def status_history(self, request, pk=None):
        """Historial de cambios de estado"""
        incident = self.get_object()
        history = incident.status_history.all()
        serializer = IncidentStatusHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='offered-workshops')
    def offered_workshops(self, request, pk=None):
        """Talleres con oferta activa para que el cliente elija."""
        incident = self.get_object()
        rows = (
            incident.assignments.filter(status=AssignmentStatus.OFFERED)
            .select_related('workshop')
            .order_by('distance_km', '-client_selected_at')
        )
        data = []
        for a in rows:
            w = a.workshop
            data.append({
                'assignment_id': a.id,
                'workshop_id': w.id,
                'workshop_name': w.name,
                'distance_km': str(a.distance_km) if a.distance_km is not None else None,
                'rating_avg': str(w.rating_avg),
                'services': w.services or [],
                'client_selected': a.client_selected_at is not None,
                'estimated_arrival_minutes': a.estimated_arrival_minutes,
            })
        return Response(data)

    @action(detail=True, methods=['post'], url_path='select-workshop')
    def select_workshop(self, request, pk=None):
        """El cliente indica el taller preferido entre las ofertas."""
        incident = self.get_object()
        assignment_id = request.data.get('assignment_id')
        if not assignment_id:
            return Response({'error': 'assignment_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
        chosen = incident.assignments.filter(
            id=assignment_id, status=AssignmentStatus.OFFERED
        ).select_related('workshop').first()
        if not chosen:
            return Response({'error': 'Oferta no encontrada o ya no disponible'}, status=status.HTTP_404_NOT_FOUND)
        now = timezone.now()
        incident.assignments.filter(status=AssignmentStatus.OFFERED).update(client_selected_at=None)
        chosen.client_selected_at = now
        chosen.save(update_fields=['client_selected_at'])
        try:
            owner = chosen.workshop.owner.user
            from apps.notifications.models import Notification, NotificationType
            Notification.objects.create(
                user=owner,
                title='Cliente eligió tu taller',
                body=f'El cliente prefirió {chosen.workshop.name} para el incidente #{incident.id}.',
                notification_type=NotificationType.NEW_REQUEST,
                incident=incident,
                data={'incident_id': incident.id, 'assignment_id': chosen.id},
            )
        except Exception:
            pass
        return Response({
            'message': 'Taller seleccionado',
            'assignment_id': chosen.id,
            'workshop_name': chosen.workshop.name,
        })

    @action(detail=True, methods=['get'], url_path='quotes')
    def quotes(self, request, pk=None):
        """Cotizaciones de talleres para este incidente."""
        incident = self.get_object()
        qs = ServiceQuote.objects.filter(
            assignment__incident=incident,
            status__in=[ServiceQuoteStatus.SENT, ServiceQuoteStatus.APPROVED, ServiceQuoteStatus.REJECTED],
        ).select_related('assignment__workshop')
        return Response(ServiceQuoteSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='quotes/respond')
    def respond_quote(self, request, pk=None):
        """Aprobar o rechazar cotización: { quote_id, action: approve|reject }."""
        incident = self.get_object()
        quote_id = request.data.get('quote_id')
        action = (request.data.get('action') or '').strip().lower()
        if not quote_id or action not in ('approve', 'reject'):
            return Response(
                {'error': 'quote_id y action (approve|reject) son requeridos'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        quote = ServiceQuote.objects.filter(
            assignment__incident=incident, id=quote_id, status=ServiceQuoteStatus.SENT
        ).first()
        if not quote:
            return Response({'error': 'Cotización no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        quote.client_responded_at = timezone.now()
        if action == 'approve':
            quote.status = ServiceQuoteStatus.APPROVED
            quote.save(update_fields=['status', 'client_responded_at'])
            ServiceQuote.objects.filter(
                assignment__incident=incident,
                status=ServiceQuoteStatus.SENT,
            ).exclude(id=quote.id).update(status=ServiceQuoteStatus.SUPERSEDED)
        else:
            quote.status = ServiceQuoteStatus.REJECTED
            quote.save(update_fields=['status', 'client_responded_at'])
        return Response(ServiceQuoteSerializer(quote).data)
