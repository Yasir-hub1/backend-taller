from django.db import models


class AssignmentStatus(models.TextChoices):
    OFFERED = 'offered', 'Ofrecida al taller'
    ACCEPTED = 'accepted', 'Aceptada'
    REJECTED = 'rejected', 'Rechazada'
    IN_ROUTE = 'in_route', 'Técnico en camino'
    ARRIVED = 'arrived', 'Técnico llegó'
    IN_SERVICE = 'in_service', 'En servicio'
    COMPLETED = 'completed', 'Completada'


class Assignment(models.Model):
    incident = models.ForeignKey(
        'incidents.Incident', on_delete=models.CASCADE, related_name='assignments'
    )
    workshop = models.ForeignKey(
        'workshops.Workshop', on_delete=models.CASCADE, related_name='assignments'
    )
    technician = models.ForeignKey(
        'workshops.Technician', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assignments'
    )
    status = models.CharField(
        max_length=20, choices=AssignmentStatus.choices, default=AssignmentStatus.OFFERED
    )

    # Distancia calculada al momento de la asignación
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Tiempo estimado de llegada
    estimated_arrival_minutes = models.PositiveIntegerField(null=True, blank=True)

    # Costo del servicio (ingresado por el taller al cerrar)
    service_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    offered_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'assignments'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['incident']),
        ]

    def __str__(self):
        return f"Assignment #{self.id} - {self.workshop.name} - {self.get_status_display()}"
