from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from apps.users.models import User
from apps.users.serializers import (
    RegisterClientSerializer, UserSerializer, ProfileUpdateSerializer,
    ChangePasswordSerializer, FCMTokenSerializer
)
from apps.users.permissions import IsClient
from django.utils import timezone


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Registro de cliente"""
    serializer = RegisterClientSerializer(data=request.data)
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
    """Login de cliente"""
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)

    if user is None:
        return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

    if user.role != 'client':
        return Response({'error': 'Esta cuenta no es de cliente'}, status=status.HTTP_403_FORBIDDEN)

    refresh = RefreshToken.for_user(user)
    return Response({
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout - invalida el refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Logout exitoso'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
@permission_classes([IsClient])
def profile(request):
    """Ver y actualizar perfil del cliente"""
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
@permission_classes([IsClient])
def fcm_token(request):
    """Actualizar FCM token para notificaciones push"""
    serializer = FCMTokenSerializer(data=request.data)
    if serializer.is_valid():
        request.user.fcm_token = serializer.validated_data['fcm_token']
        request.user.save()
        return Response({'message': 'FCM token actualizado'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsClient])
def change_password(request):
    """Cambiar contraseña"""
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'message': 'Contraseña actualizada exitosamente'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsClient])
def test_push_notification(request):
    """
    Endpoint de prueba para enviar notificación push al usuario autenticado.
    Útil para testing de Firebase/Expo push.
    """
    if not request.user.fcm_token:
        return Response({
            'error': 'No tienes token FCM registrado. Registra uno primero con POST /auth/fcm-token/'
        }, status=status.HTTP_400_BAD_REQUEST)

    title = request.data.get('title', 'Prueba de notificación')
    body = request.data.get('body', 'Esta es una notificación de prueba desde el backend')

    try:
        from apps.notifications.firebase_service import FirebaseService
        firebase = FirebaseService()
        result = firebase.send_notification(
            token=request.user.fcm_token,
            title=title,
            body=body,
            data={
                'type': 'test',
                'user_id': str(request.user.id),
                'timestamp': str(timezone.now().isoformat())
            }
        )

        if result:
            return Response({
                'message': 'Notificación enviada exitosamente',
                'token_type': 'expo' if request.user.fcm_token.startswith('ExponentPushToken') else 'fcm',
                'result': str(result)[:200]
            })
        else:
            return Response({
                'error': 'Error al enviar notificación. Revisa logs del servidor.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        return Response({
            'error': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
