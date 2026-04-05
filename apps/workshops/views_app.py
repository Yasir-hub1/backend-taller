from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.workshops.models import Workshop, WorkshopRating
from apps.workshops.serializers import (
    WorkshopDetailSerializer, NearbyWorkshopsSerializer,
    WorkshopRatingSerializer
)
from geopy.distance import geodesic
from decimal import Decimal


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nearby_workshops(request):
    """Buscar talleres cercanos"""
    lat = request.query_params.get('latitude')
    lng = request.query_params.get('longitude')
    radius = request.query_params.get('radius', 15)  # km

    if not lat or not lng:
        return Response({'error': 'Se requieren latitude y longitude'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_location = (float(lat), float(lng))
        radius = float(radius)
    except ValueError:
        return Response({'error': 'Coordenadas inválidas'}, status=status.HTTP_400_BAD_REQUEST)

    workshops = Workshop.objects.filter(is_active=True, is_verified=True)

    nearby = []
    for workshop in workshops:
        workshop_location = (float(workshop.latitude), float(workshop.longitude))
        distance = geodesic(user_location, workshop_location).km

        if distance <= min(radius, workshop.radius_km):
            workshop.distance = Decimal(str(round(distance, 2)))
            workshop.available_technicians = workshop.technicians.filter(is_available=True).count()
            nearby.append(workshop)

    # Ordenar por distancia
    nearby.sort(key=lambda x: x.distance)

    serializer = NearbyWorkshopsSerializer(nearby[:20], many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workshop_detail(request, pk):
    """Detalle de un taller"""
    try:
        workshop = Workshop.objects.get(pk=pk, is_active=True, is_verified=True)
    except Workshop.DoesNotExist:
        return Response({'error': 'Taller no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    serializer = WorkshopDetailSerializer(workshop)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_workshop(request, pk):
    """Calificar taller post-servicio"""
    try:
        workshop = Workshop.objects.get(pk=pk)
    except Workshop.DoesNotExist:
        return Response({'error': 'Taller no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    if not hasattr(request.user, 'client_profile'):
        return Response({'error': 'Solo los clientes pueden calificar'}, status=status.HTTP_403_FORBIDDEN)

    data = request.data.copy()
    data['workshop'] = workshop.id
    data['client'] = request.user.client_profile.id

    serializer = WorkshopRatingSerializer(data=data)
    if serializer.is_valid():
        serializer.save()

        # Actualizar rating promedio del taller
        ratings = workshop.ratings.all()
        avg_rating = sum(r.score for r in ratings) / len(ratings)
        workshop.rating_avg = round(avg_rating, 2)
        workshop.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
