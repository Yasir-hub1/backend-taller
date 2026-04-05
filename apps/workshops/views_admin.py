from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.workshops.models import Workshop
from apps.workshops.serializers import WorkshopSerializer, WorkshopDetailSerializer
from apps.users.permissions import IsAdmin


class WorkshopAdminViewSet(viewsets.ModelViewSet):
    """CRUD de talleres (solo admin)"""
    queryset = Workshop.objects.all().order_by('-created_at')
    serializer_class = WorkshopSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['is_active', 'is_verified']
    search_fields = ['name', 'address', 'phone', 'email']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkshopDetailSerializer
        return WorkshopSerializer

    @action(detail=True, methods=['patch'])
    def verify(self, request, pk=None):
        """Verificar/aprobar taller"""
        workshop = self.get_object()
        is_verified = request.data.get('is_verified', True)
        workshop.is_verified = is_verified
        workshop.save()
        return Response({
            'message': f'Taller {"verificado" if is_verified else "marcado como no verificado"}',
            'is_verified': workshop.is_verified
        })

    @action(detail=True, methods=['patch'])
    def toggle_active(self, request, pk=None):
        """Activar/desactivar taller"""
        workshop = self.get_object()
        workshop.is_active = not workshop.is_active
        workshop.save()
        return Response({
            'message': f'Taller {"activado" if workshop.is_active else "desactivado"}',
            'is_active': workshop.is_active
        })
