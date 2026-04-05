# 🔧 Backend – Especificación Técnica Django
## Plataforma Inteligente de Atención de Emergencias Vehiculares

---

## 1. STACK Y VERSIONES

| Tecnología | Versión recomendada | Rol |
|---|---|---|
| Python | 3.12+ | Runtime |
| Django | 5.1+ | Framework principal |
| Django REST Framework | 3.15+ | API REST |
| PostgreSQL | 16+ | Base de datos principal |
| TensorFlow | 2.17+ | Clasificación de imágenes |
| OpenAI SDK | 1.x | Whisper (audio→texto) + GPT (resumen) |
| Stripe | 10.x | Pagos y comisiones |
| Firebase Admin SDK | 6.x | Notificaciones push |
| Daphne / ASGI | 4.x | Servidor ASGI (SSE sin Redis) |
| django-eventstream | 5.x | Server-Sent Events (tiempo real, sin Redis) |
| django-q2 | 1.x | Tareas asíncronas (sin Redis, usa ORM) |
| drf-spectacular | 0.27+ | Documentación OpenAPI/Swagger |
| django-cors-headers | 4.x | Control CORS |
| django-filter | 24.x | Filtros en endpoints |
| psycopg2-binary | 2.9+ | Adaptador PostgreSQL |
| Pillow | 10.x | Procesamiento de imágenes |
| geopy | 2.x | Cálculo de distancias geográficas |
| python-dotenv | 1.x | Variables de entorno |
| whitenoise | 6.x | Archivos estáticos |
| djangorestframework-simplejwt | 5.x | Autenticación JWT |

---

## 2. ESTRUCTURA DEL PROYECTO

```
emergencias_vehiculares/
├── config/                         # Configuración principal del proyecto
│   ├── __init__.py
│   ├── settings/
│   │   ├── base.py                 # Configuración base
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py                     # URL raíz
│   ├── asgi.py                     # Servidor ASGI (para SSE)
│   └── wsgi.py
│
├── apps/
│   ├── users/                      # Gestión de usuarios y roles
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views_app.py            # Endpoints /api/app/
│   │   ├── views_web.py            # Endpoints /api/web/
│   │   ├── views_admin.py          # Endpoints /api/admin-api/
│   │   ├── permissions.py
│   │   └── urls.py
│   │
│   ├── workshops/                  # Talleres y técnicos
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views_app.py
│   │   ├── views_web.py
│   │   ├── views_admin.py
│   │   └── urls.py
│   │
│   ├── vehicles/                   # Vehículos de clientes
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views_app.py
│   │   └── urls.py
│   │
│   ├── incidents/                  # Incidentes / emergencias
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views_app.py
│   │   ├── views_web.py
│   │   ├── views_admin.py
│   │   └── urls.py
│   │
│   ├── ai_engine/                  # Motor de IA
│   │   ├── whisper_service.py      # Audio → Texto (OpenAI)
│   │   ├── classifier_service.py   # Clasificación imágenes (TensorFlow)
│   │   ├── summary_service.py      # Resumen estructurado (GPT)
│   │   └── pipeline.py             # Orquestador del flujo IA
│   │
│   ├── assignments/                # Asignación de talleres
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── engine.py               # Lógica de asignación inteligente
│   │   ├── views_app.py
│   │   ├── views_web.py
│   │   └── urls.py
│   │
│   ├── payments/                   # Pagos y comisiones (Stripe)
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── stripe_service.py
│   │   ├── views_app.py
│   │   ├── views_web.py
│   │   ├── views_admin.py
│   │   └── urls.py
│   │
│   └── notifications/              # Notificaciones push + SSE
│       ├── models.py
│       ├── serializers.py
│       ├── firebase_service.py
│       ├── sse_views.py
│       └── urls.py
│
├── media/                          # Archivos subidos (imágenes, audio) — LOCAL
│   ├── incidents/
│   │   ├── images/
│   │   └── audio/
│   └── profiles/
│
├── ml_models/                      # Modelos TensorFlow entrenados (.h5 / SavedModel)
│   └── incident_classifier/
│       ├── model.h5
│       └── labels.json
│
├── tasks.py                        # Tareas asíncronas (django-q2)
├── requirements.txt
├── .env
└── manage.py
```

---

## 3. MODELOS DE DATOS

### 3.1 App: `users`

```python
# apps/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.TextChoices):
    ADMIN = 'admin', 'Administrador'
    WORKSHOP_OWNER = 'workshop_owner', 'Dueño de Taller'
    CLIENT = 'client', 'Cliente'


class User(AbstractUser):
    """
    Usuario base unificado con rol.
    El perfil detallado se extiende en ClientProfile o WorkshopOwnerProfile.
    """
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='profiles/avatars/', null=True, blank=True)
    fcm_token = models.TextField(blank=True)  # Token Firebase para push notifications
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        indexes = [models.Index(fields=['role']), models.Index(fields=['email'])]


class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)  # ID en Stripe

    class Meta:
        db_table = 'client_profiles'


class WorkshopOwnerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owner_profile')
    national_id = models.CharField(max_length=30)  # NIT / cédula empresa
    stripe_account_id = models.CharField(max_length=100, blank=True)  # Stripe Connect

    class Meta:
        db_table = 'workshop_owner_profiles'
```

---

### 3.2 App: `workshops`

```python
# apps/workshops/models.py

class ServiceCategory(models.TextChoices):
    BATTERY = 'battery', 'Batería / Eléctrico'
    TIRE = 'tire', 'Llantas / Pinchazos'
    TOWING = 'towing', 'Remolque / Grúa'
    ENGINE = 'engine', 'Motor / Sobrecalentamiento'
    ACCIDENT = 'accident', 'Accidentes / Choque'
    LOCKSMITH = 'locksmith', 'Cerrajería (llaves)'
    GENERAL = 'general', 'Mecánica General'


class Workshop(models.Model):
    owner = models.ForeignKey(
        'users.WorkshopOwnerProfile', on_delete=models.CASCADE, related_name='workshops'
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to='workshops/logos/', null=True, blank=True)
    services = models.JSONField(default=list)       # Lista de ServiceCategory
    radius_km = models.PositiveIntegerField(default=15)  # Radio de servicio
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)  # Aprobado por admin
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_services = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workshops'
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['is_active', 'is_verified']),
        ]


class Technician(models.Model):
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name='technicians')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    specialties = models.JSONField(default=list)     # Lista de ServiceCategory
    is_available = models.BooleanField(default=True)
    current_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    current_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    last_location_update = models.DateTimeField(null=True)
    photo = models.ImageField(upload_to='technicians/', null=True, blank=True)

    class Meta:
        db_table = 'technicians'


class WorkshopRating(models.Model):
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name='ratings')
    client = models.ForeignKey('users.ClientProfile', on_delete=models.CASCADE)
    score = models.PositiveSmallIntegerField()  # 1–5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workshop_ratings'
        unique_together = [['workshop', 'client']]
```

---

### 3.3 App: `vehicles`

```python
# apps/vehicles/models.py

class VehicleType(models.TextChoices):
    CAR = 'car', 'Automóvil'
    MOTORCYCLE = 'motorcycle', 'Motocicleta'
    TRUCK = 'truck', 'Camión'
    VAN = 'van', 'Camioneta'
    BUS = 'bus', 'Bus'


class Vehicle(models.Model):
    client = models.ForeignKey(
        'users.ClientProfile', on_delete=models.CASCADE, related_name='vehicles'
    )
    brand = models.CharField(max_length=60)
    model = models.CharField(max_length=60)
    year = models.PositiveSmallIntegerField()
    plate = models.CharField(max_length=20, unique=True)
    color = models.CharField(max_length=40)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices)
    vin = models.CharField(max_length=17, blank=True)       # VIN / chasis
    is_active = models.BooleanField(default=True)
    photo = models.ImageField(upload_to='vehicles/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vehicles'
```

---

### 3.4 App: `incidents`

```python
# apps/incidents/models.py

class IncidentStatus(models.TextChoices):
    PENDING = 'pending', 'Pendiente'
    ANALYZING = 'analyzing', 'Analizando con IA'
    WAITING_WORKSHOP = 'waiting_workshop', 'Esperando taller'
    ASSIGNED = 'assigned', 'Taller asignado'
    IN_PROGRESS = 'in_progress', 'En atención'
    COMPLETED = 'completed', 'Completado'
    CANCELLED = 'cancelled', 'Cancelado'


class IncidentPriority(models.TextChoices):
    LOW = 'low', 'Baja'
    MEDIUM = 'medium', 'Media'
    HIGH = 'high', 'Alta'
    CRITICAL = 'critical', 'Crítica'


class IncidentType(models.TextChoices):
    BATTERY = 'battery', 'Batería'
    TIRE = 'tire', 'Llanta'
    ACCIDENT = 'accident', 'Choque / Accidente'
    ENGINE = 'engine', 'Motor'
    LOCKSMITH = 'locksmith', 'Llaves / Cerrajería'
    OVERHEATING = 'overheating', 'Sobrecalentamiento'
    OTHER = 'other', 'Otro'
    UNCERTAIN = 'uncertain', 'Incierto'


class Incident(models.Model):
    client = models.ForeignKey(
        'users.ClientProfile', on_delete=models.CASCADE, related_name='incidents'
    )
    vehicle = models.ForeignKey(
        'vehicles.Vehicle', on_delete=models.SET_NULL, null=True, related_name='incidents'
    )

    # Estado y clasificación
    status = models.CharField(
        max_length=30, choices=IncidentStatus.choices, default=IncidentStatus.PENDING
    )
    priority = models.CharField(
        max_length=20, choices=IncidentPriority.choices, null=True, blank=True
    )
    incident_type = models.CharField(
        max_length=20, choices=IncidentType.choices, default=IncidentType.UNCERTAIN
    )

    # Descripción manual
    description = models.TextField(blank=True)

    # Geolocalización del incidente
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    address_text = models.TextField(blank=True)

    # Resultados IA
    ai_transcription = models.TextField(blank=True)         # Whisper: audio → texto
    ai_classification_raw = models.JSONField(null=True)     # Output TensorFlow bruto
    ai_summary = models.TextField(blank=True)               # Ficha estructurada (GPT)
    ai_confidence = models.FloatField(null=True)            # Confianza clasificación

    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'incidents'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['client']),
        ]


class EvidenceType(models.TextChoices):
    IMAGE = 'image', 'Imagen'
    AUDIO = 'audio', 'Audio'
    TEXT = 'text', 'Texto adicional'


class Evidence(models.Model):
    """
    Evidencias adjuntas al incidente.
    Archivos físicos guardados en /media/incidents/ del servidor local.
    """
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='evidences')
    evidence_type = models.CharField(max_length=10, choices=EvidenceType.choices)

    # Archivo local — NUNCA AWS/S3
    file = models.FileField(upload_to='incidents/files/%Y/%m/%d/')

    # Para audios
    transcription = models.TextField(blank=True)     # Texto generado por Whisper
    transcription_done = models.BooleanField(default=False)

    # Para imágenes
    image_analysis = models.JSONField(null=True)     # Output análisis TF
    label = models.CharField(max_length=60, blank=True)  # Etiqueta principal detectada

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'evidences'


class IncidentStatusHistory(models.Model):
    """Trazabilidad completa de cambios de estado."""
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=30, choices=IncidentStatus.choices, blank=True)
    new_status = models.CharField(max_length=30, choices=IncidentStatus.choices)
    changed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'incident_status_history'
        ordering = ['-changed_at']
```

---

### 3.5 App: `assignments`

```python
# apps/assignments/models.py

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
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True)

    # Tiempo estimado de llegada
    estimated_arrival_minutes = models.PositiveIntegerField(null=True)

    # Costo del servicio (ingresado por el taller al cerrar)
    service_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    offered_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'assignments'
        indexes = [models.Index(fields=['status']), models.Index(fields=['incident'])]
```

---

### 3.6 App: `payments`

```python
# apps/payments/models.py

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
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)        # Lo que paga el cliente
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)       # % aplicado
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)    # Monto comisión
    workshop_net_amount = models.DecimalField(max_digits=10, decimal_places=2)  # total - comisión

    # Stripe
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)    # Cobro al cliente
    stripe_transfer_id = models.CharField(max_length=100, blank=True)          # Pago al taller
    stripe_charge_id = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=30, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    currency = models.CharField(max_length=3, default='usd')
    paid_at = models.DateTimeField(null=True)
    settled_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'
```

---

### 3.7 App: `notifications`

```python
# apps/notifications/models.py

class NotificationType(models.TextChoices):
    INCIDENT_CREATED = 'incident_created', 'Incidente creado'
    WORKSHOP_ASSIGNED = 'workshop_assigned', 'Taller asignado'
    TECHNICIAN_IN_ROUTE = 'technician_in_route', 'Técnico en camino'
    SERVICE_COMPLETED = 'service_completed', 'Servicio completado'
    PAYMENT_REQUIRED = 'payment_required', 'Pago requerido'
    PAYMENT_CONFIRMED = 'payment_confirmed', 'Pago confirmado'
    NEW_REQUEST = 'new_request', 'Nueva solicitud (taller)'
    STATUS_UPDATED = 'status_updated', 'Estado actualizado'


class Notification(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    body = models.TextField()
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices)
    incident = models.ForeignKey(
        'incidents.Incident', on_delete=models.SET_NULL, null=True, blank=True
    )
    data = models.JSONField(default=dict)    # Payload adicional para la app
    is_read = models.BooleanField(default=False)
    push_sent = models.BooleanField(default=False)   # Si se envió push Firebase
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
```

---

## 4. CONFIGURACIÓN DJANGO

### 4.1 `settings/base.py`

```python
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = False

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceros
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'django_eventstream',       # SSE sin Redis
    'django_q',                 # Tareas asíncronas sin Redis

    # Propias
    'apps.users',
    'apps.workshops',
    'apps.vehicles',
    'apps.incidents',
    'apps.assignments',
    'apps.payments',
    'apps.notifications',
    'apps.ai_engine',
]

AUTH_USER_MODEL = 'users.User'

# ─── Base de datos
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# ─── Archivos media (imágenes y audio — SERVIDOR LOCAL)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Límites de upload
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800   # 50 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800

# ─── REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ─── JWT
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'ALGORITHM': 'HS256',
}

# ─── Django Q2 (sin Redis — usa ORM PostgreSQL como broker)
Q_CLUSTER = {
    'name': 'emergencias',
    'workers': 4,
    'timeout': 120,
    'retry': 200,
    'queue_limit': 50,
    'orm': 'default',       # Usa la base de datos PostgreSQL, NO Redis
}

# ─── Stripe
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# ─── OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# ─── Firebase (push notifications)
FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH')

# ─── TensorFlow modelo
TF_MODEL_PATH = BASE_DIR / 'ml_models' / 'incident_classifier' / 'model.h5'
TF_LABELS_PATH = BASE_DIR / 'ml_models' / 'incident_classifier' / 'labels.json'

# ─── CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",    # Angular dev
]

# ─── DRF Spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'Emergencias Vehiculares API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
```

---

## 5. ENDPOINTS — ESTRUCTURA COMPLETA CON PREFIJOS

### Prefijos base:
- **App móvil (Flutter):** `/api/app/`
- **Web (Angular):** `/api/web/`
- **Admin panel:** `/api/admin-api/`
- **Compartidos:** `/api/`

---

### 5.1 Autenticación — App (`/api/app/auth/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/app/auth/register/` | Registro cliente (con perfil + FCM token) |
| POST | `/api/app/auth/login/` | Login → devuelve access + refresh JWT |
| POST | `/api/app/auth/refresh/` | Renovar access token |
| POST | `/api/app/auth/logout/` | Invalida refresh token |
| POST | `/api/app/auth/fcm-token/` | Actualizar token FCM (push) |
| GET/PUT | `/api/app/auth/profile/` | Ver y editar perfil del cliente |
| POST | `/api/app/auth/change-password/` | Cambiar contraseña |

---

### 5.2 Autenticación — Web (`/api/web/auth/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/web/auth/register/` | Registro dueño de taller |
| POST | `/api/web/auth/login/` | Login taller → JWT |
| POST | `/api/web/auth/refresh/` | Renovar token |
| POST | `/api/web/auth/logout/` | Logout |
| GET/PUT | `/api/web/auth/profile/` | Perfil del dueño |

---

### 5.3 Vehículos — App (`/api/app/vehicles/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/app/vehicles/` | Listar vehículos del cliente |
| POST | `/api/app/vehicles/` | Registrar nuevo vehículo |
| GET | `/api/app/vehicles/{id}/` | Detalle de vehículo |
| PUT/PATCH | `/api/app/vehicles/{id}/` | Actualizar vehículo |
| DELETE | `/api/app/vehicles/{id}/` | Eliminar vehículo |

---

### 5.4 Incidentes — App (`/api/app/incidents/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/app/incidents/` | Historial de incidentes del cliente |
| POST | `/api/app/incidents/` | **Crear incidente** (dispara pipeline IA async) |
| GET | `/api/app/incidents/{id}/` | Detalle + estado actual |
| POST | `/api/app/incidents/{id}/evidence/` | Subir evidencia (imagen/audio/texto) |
| GET | `/api/app/incidents/{id}/evidence/` | Listar evidencias |
| GET | `/api/app/incidents/{id}/assignment/` | Ver asignación activa |
| POST | `/api/app/incidents/{id}/cancel/` | Cancelar incidente |
| GET | `/api/app/incidents/{id}/status-history/` | Historial de estados |

---

### 5.5 Talleres — App (`/api/app/workshops/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/app/workshops/nearby/` | **Radar:** talleres cercanos (lat, lng, radio) |
| GET | `/api/app/workshops/{id}/` | Detalle de taller |
| POST | `/api/app/workshops/{id}/rate/` | Calificar taller post-servicio |

---

### 5.6 Notificaciones — App (`/api/app/notifications/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/app/notifications/` | Listar notificaciones del cliente |
| POST | `/api/app/notifications/{id}/read/` | Marcar como leída |
| POST | `/api/app/notifications/read-all/` | Marcar todas como leídas |
| GET | `/api/app/notifications/stream/` | **SSE stream** (tiempo real) |

---

### 5.7 Pagos — App (`/api/app/payments/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/app/payments/create-intent/` | Crear PaymentIntent Stripe |
| POST | `/api/app/payments/confirm/` | Confirmar pago |
| GET | `/api/app/payments/history/` | Historial de pagos del cliente |
| GET | `/api/app/payments/{id}/` | Detalle de pago |

---

### 5.8 Taller — Web (`/api/web/workshop/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/web/workshop/` | Datos del taller del dueño autenticado |
| PUT/PATCH | `/api/web/workshop/` | Actualizar información del taller |
| GET | `/api/web/workshop/dashboard/` | Métricas: servicios, ingresos, calificación |
| GET | `/api/web/workshop/technicians/` | Listar técnicos |
| POST | `/api/web/workshop/technicians/` | Crear técnico |
| GET | `/api/web/workshop/technicians/{id}/` | Detalle técnico |
| PUT/PATCH | `/api/web/workshop/technicians/{id}/` | Actualizar técnico |
| DELETE | `/api/web/workshop/technicians/{id}/` | Eliminar técnico |
| PATCH | `/api/web/workshop/technicians/{id}/availability/` | Cambiar disponibilidad |
| PATCH | `/api/web/workshop/technicians/{id}/location/` | Actualizar ubicación técnico |
| GET | `/api/web/workshop/earnings/` | Resumen de ingresos y comisiones |

---

### 5.9 Incidentes — Web (`/api/web/incidents/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/web/incidents/available/` | Solicitudes disponibles para el taller |
| GET | `/api/web/incidents/{id}/` | Detalle + resumen IA |
| POST | `/api/web/incidents/{id}/accept/` | Aceptar y asignar técnico |
| POST | `/api/web/incidents/{id}/reject/` | Rechazar con motivo |
| PATCH | `/api/web/incidents/{id}/status/` | Actualizar estado del servicio |
| POST | `/api/web/incidents/{id}/complete/` | Cerrar servicio + ingresar costo |
| GET | `/api/web/incidents/history/` | Historial de servicios del taller |

---

### 5.10 Notificaciones — Web (`/api/web/notifications/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/web/notifications/` | Notificaciones del taller |
| POST | `/api/web/notifications/{id}/read/` | Marcar como leída |
| GET | `/api/web/notifications/stream/` | **SSE stream** tiempo real |

---

### 5.11 Admin (`/api/admin-api/`)

> Acceso exclusivo: `role = 'admin'`

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET/POST | `/api/admin-api/users/` | Listar/crear usuarios |
| GET/PUT/DELETE | `/api/admin-api/users/{id}/` | Gestión de usuario |
| PATCH | `/api/admin-api/users/{id}/toggle-active/` | Activar/desactivar |
| GET/POST | `/api/admin-api/workshops/` | Listar talleres |
| PATCH | `/api/admin-api/workshops/{id}/verify/` | Verificar/aprobar taller |
| PATCH | `/api/admin-api/workshops/{id}/toggle-active/` | Activar/desactivar taller |
| GET | `/api/admin-api/commission/` | Ver historial de comisiones |
| POST | `/api/admin-api/commission/` | **Configurar nueva comisión** (%) |
| GET | `/api/admin-api/commission/current/` | Comisión activa actual |
| GET | `/api/admin-api/incidents/` | Todos los incidentes |
| GET | `/api/admin-api/payments/` | Todos los pagos |
| GET | `/api/admin-api/metrics/` | Métricas globales de la plataforma |

---

### 5.12 Stripe Webhook (`/api/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/stripe/webhook/` | Webhook Stripe (sin autenticación JWT) |

---

## 6. MÓDULOS DE INTELIGENCIA ARTIFICIAL

### 6.1 Servicio Whisper — Audio a Texto

```python
# apps/ai_engine/whisper_service.py
import openai
from django.conf import settings

class WhisperService:
    """
    Transcribe audio a texto usando OpenAI Whisper API.
    Compatible con: mp3, mp4, mpeg, mpga, m4a, wav, webm.
    Máximo 25 MB por archivo.
    """

    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def transcribe(self, audio_file_path: str, language: str = 'es') -> dict:
        """
        Retorna: {'transcription': str, 'duration': float, 'success': bool}
        """
        try:
            with open(audio_file_path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model='whisper-1',
                    file=audio_file,
                    language=language,
                    response_format='verbose_json',   # Incluye duración y segmentos
                )
            return {
                'transcription': response.text,
                'duration': response.duration,
                'success': True,
                'segments': response.segments,
            }
        except Exception as e:
            return {'transcription': '', 'success': False, 'error': str(e)}
```

---

### 6.2 Clasificador de Imágenes — TensorFlow

```python
# apps/ai_engine/classifier_service.py
import numpy as np
import json
from django.conf import settings

class IncidentClassifier:
    """
    Clasifica imágenes de vehículos usando TensorFlow.
    Modelo: MobileNetV2 con transfer learning.
    Clases: battery, tire, accident, engine, locksmith, overheating, other
    
    El modelo .h5 se carga UNA VEZ al iniciar (singleton).
    """
    _instance = None
    _model = None
    _labels = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        import tensorflow as tf
        self._model = tf.keras.models.load_model(settings.TF_MODEL_PATH)
        with open(settings.TF_LABELS_PATH) as f:
            self._labels = json.load(f)

    def predict(self, image_path: str) -> dict:
        """
        Retorna:
        {
            'label': 'tire',
            'confidence': 0.87,
            'all_scores': {'battery': 0.05, 'tire': 0.87, ...},
            'success': True
        }
        """
        try:
            import tensorflow as tf
            img = tf.keras.preprocessing.image.load_img(image_path, target_size=(224, 224))
            arr = tf.keras.preprocessing.image.img_to_array(img)
            arr = tf.keras.applications.mobilenet_v2.preprocess_input(arr)
            arr = np.expand_dims(arr, axis=0)

            predictions = self._model.predict(arr)[0]
            scores = {self._labels[i]: float(predictions[i]) for i in range(len(self._labels))}
            best_label = max(scores, key=scores.get)

            return {
                'label': best_label,
                'confidence': scores[best_label],
                'all_scores': scores,
                'success': True,
            }
        except Exception as e:
            return {'label': 'uncertain', 'confidence': 0.0, 'success': False, 'error': str(e)}
```

---

### 6.3 Generador de Resumen — GPT

```python
# apps/ai_engine/summary_service.py
import openai
from django.conf import settings

class SummaryService:
    """
    Genera una ficha estructurada del incidente usando GPT-4o-mini.
    """

    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_summary(self, incident_data: dict) -> str:
        """
        incident_data: {
            'transcription': str,
            'classification': str,
            'confidence': float,
            'description': str,
            'vehicle': {'brand', 'model', 'year'},
            'address': str,
        }
        """
        prompt = f"""
Eres un asistente de emergencias vehiculares. Genera una ficha técnica estructurada 
y concisa del siguiente incidente:

- Descripción del usuario: {incident_data.get('description', 'No proporcionada')}
- Transcripción de audio: {incident_data.get('transcription', 'No disponible')}
- Clasificación IA: {incident_data.get('classification')} (confianza: {incident_data.get('confidence', 0):.0%})
- Vehículo: {incident_data.get('vehicle', {}).get('brand')} {incident_data.get('vehicle', {}).get('model')} {incident_data.get('vehicle', {}).get('year')}
- Ubicación: {incident_data.get('address', 'No especificada')}

Genera la ficha en formato JSON con:
- tipo_incidente, prioridad (baja/media/alta/crítica), resumen_breve, 
  servicios_requeridos (lista), notas_tecnicas, requiere_grua (bool)
Responde SOLO el JSON, sin explicaciones adicionales.
"""
        try:
            response = self.client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=500,
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception as e:
            return '{}'
```

---

### 6.4 Pipeline IA

```python
# apps/ai_engine/pipeline.py
"""
Orquesta el procesamiento asíncrono de un incidente recién creado.
Se ejecuta via django-q2 en background.
"""
from apps.ai_engine.whisper_service import WhisperService
from apps.ai_engine.classifier_service import IncidentClassifier
from apps.ai_engine.summary_service import SummaryService
from apps.incidents.models import Incident, Evidence, EvidenceType, IncidentType, IncidentPriority

PRIORITY_MAP = {
    'accident': IncidentPriority.HIGH,
    'engine': IncidentPriority.HIGH,
    'overheating': IncidentPriority.HIGH,
    'battery': IncidentPriority.MEDIUM,
    'tire': IncidentPriority.MEDIUM,
    'locksmith': IncidentPriority.LOW,
    'other': IncidentPriority.LOW,
    'uncertain': IncidentPriority.MEDIUM,
}

def process_incident_pipeline(incident_id: int):
    """Función principal ejecutada por django-q2."""
    incident = Incident.objects.get(id=incident_id)
    incident.status = 'analyzing'
    incident.save(update_fields=['status'])

    whisper = WhisperService()
    classifier = IncidentClassifier()

    transcriptions = []
    best_classification = {'label': 'uncertain', 'confidence': 0.0}

    for evidence in incident.evidences.all():
        if evidence.evidence_type == EvidenceType.AUDIO and not evidence.transcription_done:
            result = whisper.transcribe(evidence.file.path)
            if result['success']:
                evidence.transcription = result['transcription']
                evidence.transcription_done = True
                evidence.save()
                transcriptions.append(result['transcription'])

        elif evidence.evidence_type == EvidenceType.IMAGE:
            result = classifier.predict(evidence.file.path)
            evidence.image_analysis = result
            evidence.label = result.get('label', '')
            evidence.save()
            if result['confidence'] > best_classification['confidence']:
                best_classification = result

    # Determinar tipo de incidente
    incident_type = best_classification['label'] if best_classification['confidence'] > 0.5 else 'uncertain'

    # Generar resumen GPT
    summary_svc = SummaryService()
    vehicle = incident.vehicle
    summary_json = summary_svc.generate_summary({
        'transcription': ' '.join(transcriptions),
        'classification': incident_type,
        'confidence': best_classification['confidence'],
        'description': incident.description,
        'vehicle': {'brand': vehicle.brand, 'model': vehicle.model, 'year': vehicle.year} if vehicle else {},
        'address': incident.address_text,
    })

    # Actualizar incidente
    incident.incident_type = incident_type
    incident.ai_transcription = ' '.join(transcriptions)
    incident.ai_classification_raw = best_classification
    incident.ai_summary = summary_json
    incident.ai_confidence = best_classification['confidence']
    incident.priority = PRIORITY_MAP.get(incident_type, IncidentPriority.MEDIUM)
    incident.status = 'waiting_workshop'
    incident.save()

    # Disparar motor de asignación
    from apps.assignments.engine import AssignmentEngine
    AssignmentEngine.find_and_notify_workshops(incident)
```

---

### 6.5 Motor de Asignación

```python
# apps/assignments/engine.py
from geopy.distance import geodesic
from apps.workshops.models import Workshop
from apps.assignments.models import Assignment
from apps.notifications.firebase_service import FirebaseService

class AssignmentEngine:

    @staticmethod
    def find_and_notify_workshops(incident) -> list:
        """
        Encuentra talleres candidatos según:
        - Distancia al incidente (dentro del radio de servicio del taller)
        - Tipo de servicio requerido
        - Taller activo y verificado
        - Disponibilidad de técnicos
        
        Retorna lista de talleres ordenados por score.
        """
        incident_location = (float(incident.latitude), float(incident.longitude))

        workshops = Workshop.objects.filter(
            is_active=True,
            is_verified=True,
        ).prefetch_related('technicians')

        candidates = []
        for workshop in workshops:
            # Verificar si el taller tiene técnicos disponibles
            has_available_tech = workshop.technicians.filter(is_available=True).exists()
            if not has_available_tech:
                continue

            # Verificar que el incidente cabe en el tipo de servicio
            if incident.incident_type not in workshop.services and 'general' not in workshop.services:
                continue

            # Calcular distancia
            workshop_location = (float(workshop.latitude), float(workshop.longitude))
            distance_km = geodesic(incident_location, workshop_location).km

            if distance_km > workshop.radius_km:
                continue

            # Score: menor distancia + mayor rating = mejor score
            score = (1 / (distance_km + 0.1)) * float(workshop.rating_avg or 3.0)
            candidates.append({
                'workshop': workshop,
                'distance_km': round(distance_km, 2),
                'score': score,
            })

        # Ordenar por score descendente
        candidates.sort(key=lambda x: x['score'], reverse=True)
        top_candidates = candidates[:5]  # Top 5

        # Crear assignments en estado 'offered' y notificar
        firebase = FirebaseService()
        for candidate in top_candidates:
            Assignment.objects.create(
                incident=incident,
                workshop=candidate['workshop'],
                distance_km=candidate['distance_km'],
                status='offered',
            )
            # Notificar al dueño del taller
            owner_user = candidate['workshop'].owner.user
            firebase.send_notification(
                token=owner_user.fcm_token,
                title='Nueva solicitud de emergencia',
                body=f"Incidente tipo {incident.incident_type} a {candidate['distance_km']} km",
                data={'incident_id': str(incident.id), 'type': 'new_request'},
            )

        return top_candidates
```

---

## 7. SERVICIO DE NOTIFICACIONES

### 7.1 Firebase Push

```python
# apps/notifications/firebase_service.py
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

class FirebaseService:
    _initialized = False

    def __init__(self):
        if not FirebaseService._initialized:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            FirebaseService._initialized = True

    def send_notification(self, token: str, title: str, body: str, data: dict = None):
        if not token:
            return
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        messaging.send(message)
```

### 7.2 SSE — Tiempo Real (sin Redis)

```python
# apps/notifications/sse_views.py
"""
Server-Sent Events usando django-eventstream.
El cliente Angular/Flutter se suscribe a este endpoint
y recibe actualizaciones en tiempo real del incidente.

django-eventstream usa la base de datos internamente (sin Redis).
"""
from django_eventstream import send_event

def notify_incident_update(incident_id: int, data: dict):
    """Llamar desde cualquier parte del backend para emitir un evento."""
    channel = f'incident-{incident_id}'
    send_event(channel, 'message', data)

def notify_user(user_id: int, data: dict):
    channel = f'user-{user_id}'
    send_event(channel, 'message', data)
```

---

## 8. INTEGRACIÓN STRIPE

```python
# apps/payments/stripe_service.py
import stripe
from django.conf import settings
from apps.payments.models import CommissionConfig

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:

    @staticmethod
    def get_active_commission() -> float:
        config = CommissionConfig.objects.filter(is_active=True).first()
        return float(config.percentage) if config else 10.0

    @staticmethod
    def create_payment_intent(amount_usd: float, customer_id: str, metadata: dict) -> dict:
        """Crea el intento de pago para el cliente."""
        intent = stripe.PaymentIntent.create(
            amount=int(amount_usd * 100),   # Stripe usa centavos
            currency='usd',
            customer=customer_id,
            metadata=metadata,
            automatic_payment_methods={'enabled': True},
        )
        return {'client_secret': intent.client_secret, 'payment_intent_id': intent.id}

    @staticmethod
    def transfer_to_workshop(amount_usd: float, stripe_account_id: str, metadata: dict) -> str:
        """Transfiere el monto neto al taller vía Stripe Connect."""
        transfer = stripe.Transfer.create(
            amount=int(amount_usd * 100),
            currency='usd',
            destination=stripe_account_id,
            metadata=metadata,
        )
        return transfer.id

    @staticmethod
    def create_stripe_account_link(account_id: str, refresh_url: str, return_url: str) -> str:
        """Para que el taller conecte su cuenta Stripe (onboarding)."""
        link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type='account_onboarding',
        )
        return link.url

    @staticmethod
    def handle_webhook(payload: bytes, sig_header: str) -> stripe.Event:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
```

---

## 9. TAREAS ASÍNCRONAS (django-q2)

```python
# tasks.py — Registro de tareas para django-q2
from django_q.tasks import async_task, schedule
from django_q.models import Schedule

def enqueue_incident_pipeline(incident_id: int):
    """Encola el procesamiento IA del incidente."""
    async_task(
        'apps.ai_engine.pipeline.process_incident_pipeline',
        incident_id,
        hook='tasks.on_pipeline_complete',
    )

def on_pipeline_complete(task):
    """Callback cuando termina el pipeline IA."""
    from apps.notifications.sse_views import notify_incident_update
    if task.success:
        notify_incident_update(task.result, {'event': 'ai_complete'})
```

---

## 10. PERMISOS PERSONALIZADOS

```python
# apps/users/permissions.py
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class IsWorkshopOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'workshop_owner'

class IsClient(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'client'

class IsAdminOrWorkshopOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'workshop_owner']
```

---

## 11. `requirements.txt`

```txt
# Core
Django==5.1.4
djangorestframework==3.15.2
psycopg2-binary==2.9.9

# Auth
djangorestframework-simplejwt==5.3.1

# API utils
django-cors-headers==4.4.0
django-filter==24.3
drf-spectacular==0.27.2
whitenoise==6.7.0

# Async (sin Redis)
django-q2==1.7.3
django-eventstream==5.3.0
daphne==4.1.2

# IA
openai==1.43.0
tensorflow==2.17.0
numpy==1.26.4
Pillow==10.4.0

# Pagos
stripe==10.7.0

# Geolocalización
geopy==2.4.1

# Firebase
firebase-admin==6.5.0

# Utils
python-dotenv==1.0.1

# Dev / Testing
pytest-django==4.8.0
factory-boy==3.3.1
```

---

## 12. CONSIDERACIONES DE SEGURIDAD

- **JWT rotativo:** refresh tokens con rotación habilitada y lista negra en BD.
- **Rate limiting:** usar `django-ratelimit` en endpoints de auth y subida de archivos.
- **Validación de archivos:** verificar MIME type real (magic bytes) antes de procesar, no solo la extensión.
- **Stripe webhook:** siempre verificar firma `stripe-signature` antes de procesar.
- **Tamaño máximo archivos:** imágenes 10 MB, audio 25 MB (límite Whisper).
- **Sanitización:** limpiar nombres de archivos subidos con `django.utils.text.get_valid_filename`.
- **HTTPS:** obligatorio en producción. Usar certificado TLS (Let's Encrypt o similar).
- **Variables de entorno:** NUNCA hardcodear claves en código. Usar `.env` con `python-dotenv`.
