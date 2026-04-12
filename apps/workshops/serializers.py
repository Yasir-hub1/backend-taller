import json

from rest_framework import serializers
from apps.workshops.models import Workshop, Technician, WorkshopRating
from decimal import Decimal


def parse_services_list(value):
    """Multipart/form-data envía `services` como string JSON; normaliza a lista."""
    if value is None or value == '':
        return []
    if isinstance(value, str):
        try:
            data = json.loads(value)
        except json.JSONDecodeError as e:
            raise serializers.ValidationError(
                'services debe ser un JSON válido (lista de categorías).'
            ) from e
        if not isinstance(data, list):
            raise serializers.ValidationError('services debe ser una lista.')
        return data
    if isinstance(value, list):
        return value
    raise serializers.ValidationError('Formato de services inválido.')


class TechnicianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Technician
        fields = [
            'id', 'name', 'phone', 'specialties', 'is_available',
            'current_latitude', 'current_longitude', 'last_location_update', 'photo'
        ]
        read_only_fields = ['id']


class WorkshopRatingSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.user.get_full_name', read_only=True)

    class Meta:
        model = WorkshopRating
        fields = ['id', 'workshop', 'client', 'assignment', 'client_name', 'score', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']


class RateWorkshopSerializer(serializers.Serializer):
    assignment_id = serializers.IntegerField(required=True)
    score = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class WorkshopSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.user.get_full_name', read_only=True)

    class Meta:
        model = Workshop
        fields = [
            'id', 'owner', 'owner_name', 'name', 'description', 'address',
            'latitude', 'longitude', 'phone', 'email', 'logo', 'services',
            'radius_km', 'is_active', 'is_verified', 'rating_avg',
            'total_services', 'created_at'
        ]
        read_only_fields = [
            'id', 'owner', 'rating_avg', 'total_services', 'created_at', 'is_verified',
        ]

    def validate_services(self, value):
        return parse_services_list(value)


class WorkshopDetailSerializer(WorkshopSerializer):
    technicians = TechnicianSerializer(many=True, read_only=True)
    recent_ratings = serializers.SerializerMethodField()

    class Meta(WorkshopSerializer.Meta):
        fields = WorkshopSerializer.Meta.fields + ['technicians', 'recent_ratings']

    def get_recent_ratings(self, obj):
        ratings = obj.ratings.order_by('-created_at')[:5]
        return WorkshopRatingSerializer(ratings, many=True).data


class WorkshopCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workshop
        fields = [
            'name', 'description', 'address', 'latitude', 'longitude',
            'phone', 'email', 'logo', 'services', 'radius_km'
        ]

    def validate_services(self, value):
        return parse_services_list(value)

    def create(self, validated_data):
        # El owner viene del request.user.owner_profile
        return Workshop.objects.create(**validated_data)


class NearbyWorkshopsSerializer(serializers.ModelSerializer):
    distance = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    distance_km = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    available_technicians = serializers.IntegerField(read_only=True)

    class Meta:
        model = Workshop
        fields = [
            'id', 'name', 'description', 'address', 'latitude', 'longitude',
            'phone', 'logo', 'services', 'rating_avg', 'total_services',
            'distance', 'distance_km', 'available_technicians'
        ]


class WorkshopDashboardSerializer(serializers.Serializer):
    total_services = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    active_services = serializers.IntegerField()
    completed_this_month = serializers.IntegerField()
    rating_avg = serializers.DecimalField(max_digits=3, decimal_places=2)
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    earnings_this_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    available_technicians = serializers.IntegerField()


class TechnicianCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Technician
        fields = ['name', 'phone', 'specialties', 'photo']


class TechnicianLocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=True)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=True)


class TechnicianAvailabilitySerializer(serializers.Serializer):
    is_available = serializers.BooleanField(required=True)
