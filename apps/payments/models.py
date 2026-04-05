from django.db import models


class CommissionConfig(models.Model):
    """
    Configuración de comisión gestionada SOLO por el Admin.
    Porcentaje que el taller paga a la plataforma.
    """
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    description = models.CharField(max_length=200, blank=True)
    effective_from = models.DateField()
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'commission_configs'
        ordering = ['-effective_from']

    def __str__(self):
        return f"Commission {self.percentage}% - Effective from {self.effective_from}"


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pendiente'
    CLIENT_PAID = 'client_paid', 'Cliente pagó'
    COMMISSION_SETTLED = 'commission_settled', 'Comisión liquidada'
    FAILED = 'failed', 'Fallido'
    REFUNDED = 'refunded', 'Reembolsado'


class Payment(models.Model):
    """
    Flujo Stripe:
    1. Cliente paga el total del servicio (PaymentIntent al cliente).
    2. La plataforma retiene la comisión.
    3. El taller recibe el neto (Transfer vía Stripe Connect).
    """
    assignment = models.OneToOneField(
        'assignments.Assignment', on_delete=models.CASCADE, related_name='payment'
    )
    commission_config = models.ForeignKey(
        CommissionConfig, on_delete=models.SET_NULL, null=True
    )

    # Montos
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Lo que paga el cliente
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)  # % aplicado
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Monto comisión
    workshop_net_amount = models.DecimalField(max_digits=10, decimal_places=2)  # total - comisión

    # Stripe
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)  # Cobro al cliente
    stripe_transfer_id = models.CharField(max_length=100, blank=True)  # Pago al taller
    stripe_charge_id = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=30, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    currency = models.CharField(max_length=3, default='usd')
    paid_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'

    def __str__(self):
        return f"Payment #{self.id} - ${self.total_amount} - {self.get_status_display()}"
