from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.users.models import User
from apps.users.serializers import UserSerializer
from apps.users.permissions import IsAdmin


class UserAdminViewSet(viewsets.ModelViewSet):
    """CRUD de usuarios (solo admin)"""
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['role', 'is_active', 'is_verified']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    @action(detail=True, methods=['patch'])
    def toggle_active(self, request, pk=None):
        """Activar/desactivar usuario"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response({
            'message': f'Usuario {"activado" if user.is_active else "desactivado"}',
            'is_active': user.is_active
        })
