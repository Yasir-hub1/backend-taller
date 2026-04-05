from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from apps.incidents.models import Incident, Evidence, EvidenceType, IncidentStatus
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
        return Incident.objects.filter(client=self.request.user.client_profile).order_by('-created_at')

    def perform_create(self, serializer):
        incident = serializer.save(
            client=self.request.user.client_profile,
            status=IncidentStatus.PENDING
        )
        # Disparar pipeline de IA asíncrono
        enqueue_incident_pipeline(incident.id)

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
        assignment = incident.assignments.filter(status__in=['accepted', 'in_route', 'arrived', 'in_service']).first()
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
