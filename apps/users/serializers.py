from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from apps.users.models import User, ClientProfile, WorkshopOwnerProfile
from apps.payments.stripe_service import StripeService


class ClientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientProfile
        fields = ['id', 'address', 'emergency_contact_name', 'emergency_contact_phone', 'stripe_customer_id']
        read_only_fields = ['id', 'stripe_customer_id']


class WorkshopOwnerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkshopOwnerProfile
        fields = ['id', 'national_id', 'stripe_account_id']
        read_only_fields = ['id', 'stripe_account_id']


class UserSerializer(serializers.ModelSerializer):
    client_profile = ClientProfileSerializer(read_only=True)
    owner_profile = WorkshopOwnerProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'avatar', 'fcm_token', 'is_verified',
            'created_at', 'updated_at', 'client_profile', 'owner_profile'
        ]
        read_only_fields = ['id', 'role', 'is_verified', 'created_at', 'updated_at']


class RegisterClientSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    # Client profile fields
    address = serializers.CharField(required=False, allow_blank=True)
    emergency_contact_name = serializers.CharField(required=False, allow_blank=True)
    emergency_contact_phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'fcm_token',
            'address', 'emergency_contact_name', 'emergency_contact_phone'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')

        # Extraer campos del perfil
        profile_data = {
            'address': validated_data.pop('address', ''),
            'emergency_contact_name': validated_data.pop('emergency_contact_name', ''),
            'emergency_contact_phone': validated_data.pop('emergency_contact_phone', ''),
        }

        # Crear usuario
        user = User.objects.create_user(
            **validated_data,
            role='client'
        )

        # Crear perfil de cliente
        profile = ClientProfile.objects.create(user=user, **profile_data)

        # Crear customer en Stripe para pagos futuros (si está configurado)
        full_name = f"{user.first_name} {user.last_name}".strip()
        stripe_result = StripeService.create_customer(
            email=user.email,
            name=full_name,
            phone=user.phone or '',
        )
        customer_id = stripe_result.get('customer_id')
        if customer_id:
            profile.stripe_customer_id = customer_id
            profile.save(update_fields=['stripe_customer_id'])

        return user


class RegisterWorkshopOwnerSerializer(serializers.ModelSerializer):
    # Sin validate_password de Django: no bloquea contraseñas "débiles", solo numéricas, comunes, etc.
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=6,
        max_length=128,
        error_messages={
            'min_length': 'La contraseña debe tener al menos 6 caracteres.',
        },
    )
    password_confirm = serializers.CharField(write_only=True, required=True)
    national_id = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'national_id'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        national_id = validated_data.pop('national_id')

        # Crear usuario
        user = User.objects.create_user(
            **validated_data,
            role='workshop_owner'
        )

        # Crear perfil de dueño de taller
        WorkshopOwnerProfile.objects.create(user=user, national_id=national_id)

        return user


class ProfileUpdateSerializer(serializers.ModelSerializer):
    # Campos de perfil según el rol
    address = serializers.CharField(required=False, allow_blank=True)
    emergency_contact_name = serializers.CharField(required=False, allow_blank=True)
    emergency_contact_phone = serializers.CharField(required=False, allow_blank=True)
    national_id = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'avatar',
            'address', 'emergency_contact_name', 'emergency_contact_phone',
            'national_id'
        ]

    def update(self, instance, validated_data):
        # Actualizar campos del usuario
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()

        # Actualizar perfil según el rol
        if instance.role == 'client' and hasattr(instance, 'client_profile'):
            profile = instance.client_profile
            profile.address = validated_data.get('address', profile.address)
            profile.emergency_contact_name = validated_data.get('emergency_contact_name', profile.emergency_contact_name)
            profile.emergency_contact_phone = validated_data.get('emergency_contact_phone', profile.emergency_contact_phone)
            profile.save()

        elif instance.role == 'workshop_owner' and hasattr(instance, 'owner_profile'):
            profile = instance.owner_profile
            if 'national_id' in validated_data:
                profile.national_id = validated_data['national_id']
                profile.save()

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Las contraseñas no coinciden"})
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Contraseña actual incorrecta")
        return value


class FCMTokenSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(required=True)
