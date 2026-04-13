from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from apps.users.models import User
from apps.users.serializers import (
    RegisterWorkshopOwnerSerializer, UserSerializer, ProfileUpdateSerializer
)
from apps.users.permissions import IsWorkshopOwner
from rest_framework.permissions import IsAuthenticated


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Registro de dueño de taller"""
    serializer = RegisterWorkshopOwnerSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login de dueño de taller"""
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)

    if user is None:
        return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

    if user.role not in ('workshop_owner', 'admin'):
        return Response({'error': 'Esta cuenta no puede acceder al panel web'}, status=status.HTTP_403_FORBIDDEN)

    refresh = RefreshToken.for_user(user)
    return Response({
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    })


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Ver y actualizar perfil (dueño de taller o administrador)"""
    if request.method == 'GET':
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_fcm_token(request):
    """
    Actualizar FCM token para notificaciones push.
    Usado por talleres en el panel web (si implementan push web).
    """
    from apps.users.serializers import FCMTokenSerializer

    serializer = FCMTokenSerializer(data=request.data)
    if serializer.is_valid():
        request.user.fcm_token = serializer.validated_data['fcm_token']
        request.user.save(update_fields=['fcm_token'])
        return Response({
            'message': 'Token FCM actualizado',
            'token_type': 'expo' if request.user.fcm_token.startswith('ExponentPushToken') else 'fcm'
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
