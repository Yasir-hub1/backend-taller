import stripe
from django.conf import settings
from apps.payments.models import CommissionConfig
from datetime import date


stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """
    Servicio de integración con Stripe para pagos y comisiones.
    """

    @staticmethod
    def get_active_commission() -> float:
        """Obtiene el porcentaje de comisión activo actual."""
        config = CommissionConfig.objects.filter(
            is_active=True,
            effective_from__lte=date.today()
        ).order_by('-effective_from').first()

        return float(config.percentage) if config else 10.0

    @staticmethod
    def create_payment_intent(amount_usd: float, customer_id: str, metadata: dict) -> dict:
        """
        Crea el intento de pago para el cliente.

        Args:
            amount_usd: Monto en dólares
            customer_id: ID del customer en Stripe
            metadata: Datos adicionales (incident_id, assignment_id, etc.)

        Returns:
            dict con client_secret y payment_intent_id
        """
        if not settings.STRIPE_SECRET_KEY:
            return {
                'error': 'Stripe not configured',
                'client_secret': None,
                'payment_intent_id': None
            }

        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount_usd * 100),  # Stripe usa centavos
                currency='usd',
                customer=customer_id,
                metadata=metadata,
                automatic_payment_methods={'enabled': True},
            )
            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            }
        except Exception as e:
            return {
                'error': str(e),
                'client_secret': None,
                'payment_intent_id': None
            }

    @staticmethod
    def transfer_to_workshop(amount_usd: float, stripe_account_id: str, metadata: dict) -> dict:
        """
        Transfiere el monto neto al taller vía Stripe Connect.

        Args:
            amount_usd: Monto neto a transferir
            stripe_account_id: ID de la cuenta Connect del taller
            metadata: Datos adicionales

        Returns:
            dict con transfer_id o error
        """
        if not settings.STRIPE_SECRET_KEY:
            return {'error': 'Stripe not configured', 'transfer_id': None}

        try:
            transfer = stripe.Transfer.create(
                amount=int(amount_usd * 100),
                currency='usd',
                destination=stripe_account_id,
                metadata=metadata,
            )
            return {'transfer_id': transfer.id}
        except Exception as e:
            return {'error': str(e), 'transfer_id': None}

    @staticmethod
    def create_stripe_account_link(account_id: str, refresh_url: str, return_url: str) -> dict:
        """
        Crea un enlace para que el taller conecte su cuenta Stripe (onboarding).

        Args:
            account_id: ID de la cuenta Connect
            refresh_url: URL de refresco si expira
            return_url: URL de retorno al completar

        Returns:
            dict con url del onboarding o error
        """
        if not settings.STRIPE_SECRET_KEY:
            return {'error': 'Stripe not configured', 'url': None}

        try:
            link = stripe.AccountLink.create(
                account=account_id,
                refresh_url=refresh_url,
                return_url=return_url,
                type='account_onboarding',
            )
            return {'url': link.url}
        except Exception as e:
            return {'error': str(e), 'url': None}

    @staticmethod
    def create_connected_account(email: str, country: str = 'US') -> dict:
        """
        Crea una cuenta Connect para un taller.

        Args:
            email: Email del dueño del taller
            country: Código de país (US, CO, etc.)

        Returns:
            dict con account_id o error
        """
        if not settings.STRIPE_SECRET_KEY:
            return {'error': 'Stripe not configured', 'account_id': None}

        try:
            account = stripe.Account.create(
                type='express',
                email=email,
                country=country,
                capabilities={
                    'transfers': {'requested': True},
                },
            )
            return {'account_id': account.id}
        except Exception as e:
            return {'error': str(e), 'account_id': None}

    @staticmethod
    def handle_webhook(payload: bytes, sig_header: str):
        """
        Verifica y procesa un webhook de Stripe.

        Args:
            payload: Cuerpo de la petición (bytes)
            sig_header: Header 'Stripe-Signature'

        Returns:
            stripe.Event object

        Raises:
            ValueError si la firma es inválida
        """
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise ValueError('Stripe webhook secret not configured')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError as e:
            raise ValueError(f'Invalid payload: {e}')
        except stripe.error.SignatureVerificationError as e:
            raise ValueError(f'Invalid signature: {e}')
