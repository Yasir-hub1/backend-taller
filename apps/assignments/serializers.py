from rest_framework import serializers
from apps.assignments.models import Assignment
from apps.workshops.serializers import WorkshopSerializer, TechnicianSerializer
from apps.incidents.serializers import IncidentSerializer


class AssignmentSerializer(serializers.ModelSerializer):
    workshop_name = serializers.CharField(source='workshop.name', read_only=True)
    technician_name = serializers.CharField(source='technician.name', read_only=True, allow_null=True)
    incident_type = serializers.CharField(source='incident.get_incident_type_display', read_only=True)
    client_rating = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            'id', 'incident', 'incident_type', 'workshop', 'workshop_name',
            'technician', 'technician_name', 'status', 'distance_km',
            'estimated_arrival_minutes', 'service_cost', 'offered_at',
            'accepted_at', 'arrived_at', 'completed_at', 'rejection_reason',
            'client_rating',
        ]
        read_only_fields = [
            'id', 'offered_at', 'accepted_at', 'arrived_at', 'completed_at',
            'distance_km', 'rejection_reason'
        ]

    def get_client_rating(self, obj):
        r = getattr(obj, 'client_rating', None)
        if r is None:
            return None
        return {'score': r.score, 'comment': r.comment}


class AssignmentDetailSerializer(AssignmentSerializer):
    workshop = WorkshopSerializer(read_only=True)
    technician = TechnicianSerializer(read_only=True)
    incident = IncidentSerializer(read_only=True)

    class Meta(AssignmentSerializer.Meta):
        fields = AssignmentSerializer.Meta.fields


class AssignmentAcceptSerializer(serializers.Serializer):
    technician_id = serializers.IntegerField(required=True)
    estimated_arrival_minutes = serializers.IntegerField(required=False, min_value=1, max_value=300)


class AssignmentRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=True, max_length=500)


class AssignmentStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        ('in_route', 'En camino'),
        ('arrived', 'Llegó'),
        ('in_service', 'En servicio'),
        ('completed', 'Completada')
    ])
