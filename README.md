# Backend - Plataforma Inteligente de Emergencias Vehiculares

Sistema backend completo para plataforma de asistencia vehicular con IA, pagos y notificaciones en tiempo real.

## 🚀 Stack Tecnológico

- **Django 5.1.4** + **Django REST Framework 3.15.2**
- **PostgreSQL 16+** (base de datos)
- **OpenAI API** (Whisper + GPT-4o-mini)
- **TensorFlow 2.17** (clasificación de imágenes)
- **Stripe** (pagos y comisiones)
- **Firebase** (push notifications)
- **Django-Q2** (tareas asíncronas sin Redis)
- **django-eventstream** (SSE para tiempo real)

## 📁 Estructura del Proyecto

```
backend/
├── config/              # Configuración principal
│   ├── settings.py      # Settings unificado
│   ├── urls.py          # Rutas principales
│   ├── asgi.py          # ASGI con soporte SSE
│   └── wsgi.py
├── apps/
│   ├── users/           # Usuarios y perfiles (admin, client, workshop_owner)
│   ├── workshops/       # Talleres y técnicos
│   ├── vehicles/        # Vehículos de clientes
│   ├── incidents/       # Incidentes/emergencias
│   ├── ai_engine/       # Motor IA (Whisper, TF, GPT)
│   ├── assignments/     # Asignación de talleres
│   ├── payments/        # Pagos con Stripe
│   └── notifications/   # Notificaciones (Firebase + SSE)
├── media/               # Archivos subidos (local)
├── ml_models/           # Modelos TensorFlow
└── tasks.py             # Tareas asíncronas
```

## 🛠️ Setup e Instalación

### 1. Requisitos Previos
- Python 3.12+
- PostgreSQL 16+
- Git

### 2. Clonar e Instalar

```bash
# Navegar al directorio del proyecto
cd backend

# Crear entorno virtual (si no existe)
python -m venv venv

# Activar entorno virtual
source venv/bin/activate  # macOS/Linux
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno

```bash
# Copiar template
cp .env.example .env

# Editar .env con tus credenciales
nano .env
```

Variables requeridas:
```env
# Django
SECRET_KEY=tu-secret-key-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
DB_NAME=emergencias_vehiculares
DB_USER=tu_usuario_postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432

# OpenAI (para IA)
OPENAI_API_KEY=sk-tu-api-key-aqui

# Stripe (para pagos)
STRIPE_SECRET_KEY=sk_test_tu-secret-key
STRIPE_PUBLISHABLE_KEY=pk_test_tu-publishable-key
STRIPE_WEBHOOK_SECRET=whsec_tu-webhook-secret

# Firebase (para push notifications)
FIREBASE_CREDENTIALS_PATH=/ruta/a/firebase-credentials.json

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:4200
```

### 4. Configurar Base de Datos

```bash
# Crear base de datos en PostgreSQL
createdb emergencias_vehiculares

# O desde psql:
# psql -U postgres
# CREATE DATABASE emergencias_vehiculares;

# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario admin
python manage.py createsuperuser
# Importante: Asignar role='admin' manualmente en la BD o vía shell
```

### 5. Crear Usuario Admin con Role

```bash
python manage.py shell
```

```python
from apps.users.models import User

# Cambiar role del superuser a admin
user = User.objects.get(username='tu_username')
user.role = 'admin'
user.save()
exit()
```

## 🏃 Ejecutar el Proyecto

### Servidor de Desarrollo

```bash
# Terminal 1: Django server
python manage.py runserver
```

### Worker de Tareas Asíncronas

```bash
# Terminal 2: Django-Q2 worker
python manage.py qcluster
```

El servidor estará disponible en: `http://localhost:8000`

## 📚 Documentación API

Una vez el servidor esté corriendo:

- **Swagger UI**: http://localhost:8000/api/docs/
- **OpenAPI Schema**: http://localhost:8000/api/schema/
- **Admin Panel**: http://localhost:8000/admin/

## 🧪 Testing

```bash
# Ejecutar tests
pytest

# Con cobertura
pytest --cov=apps
```

## 🔄 Flujo de Trabajo del Sistema

### 1. Creación de Incidente
```
Cliente reporta emergencia →
API crea Incident + Evidence →
Pipeline IA se dispara (async)
```

### 2. Procesamiento IA
```
Audio → Whisper (transcripción) →
Imagen → TensorFlow (clasificación) →
GPT (genera resumen estructurado) →
Determina tipo y prioridad
```

### 3. Asignación de Taller
```
Motor busca talleres cercanos →
Calcula distancia y score →
Crea Assignments →
Notifica (Firebase Push + SSE)
```

### 4. Pago
```
Taller completa servicio →
Cliente paga vía Stripe →
Plataforma retiene comisión →
Taller recibe neto (Stripe Connect)
```

## 🌐 Endpoints Principales

### App (Clientes - Flutter)
- `POST /api/app/auth/register/` - Registro
- `POST /api/app/auth/login/` - Login
- `GET/POST /api/app/vehicles/` - Vehículos
- `POST /api/app/incidents/` - Crear emergencia
- `GET /api/app/workshops/nearby/` - Talleres cercanos

### Web (Talleres - Angular)
- `POST /api/web/auth/register/` - Registro taller
- `POST /api/web/auth/login/` - Login
- `GET /api/web/incidents/available/` - Solicitudes disponibles
- `POST /api/web/incidents/{id}/accept/` - Aceptar servicio
- `GET /api/web/workshop/dashboard/` - Dashboard

### Admin
- `GET /api/admin-api/users/` - Gestión usuarios
- `GET /api/admin-api/workshops/` - Gestión talleres
- `POST /api/admin-api/commission/` - Configurar comisión

### SSE (Tiempo Real)
- `GET /api/events/incident-{id}/` - Updates del incidente
- `GET /api/events/user-{id}/` - Notificaciones usuario
- `GET /api/events/workshop-{id}/` - Notificaciones taller

## 🔧 Comandos Útiles

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Shell interactivo
python manage.py shell

# Limpiar base de datos
python manage.py flush

# Colectar archivos estáticos
python manage.py collectstatic

# Ejecutar worker Django-Q2
python manage.py qcluster
```

## 📊 Estado de Implementación

Ver `IMPLEMENTATION_STATUS.md` para detalles completos sobre:
- ✅ Componentes implementados (modelos, servicios, IA, etc.)
- 🚧 Pendientes (views, URLs, serializers restantes)
- 📋 Próximos pasos

## 🔐 Seguridad

- JWT con rotación de refresh tokens
- Validación de contraseñas con Django validators
- Permisos basados en roles (IsAdmin, IsClient, IsWorkshopOwner)
- Validación de tipos MIME en archivos subidos
- Verificación de firma en webhooks de Stripe
- HTTPS requerido en producción

## 🐛 Troubleshooting

### Error: "OpenAI API key not configured"
- Verifica que `OPENAI_API_KEY` esté en tu `.env`
- El sistema funcionará sin ella (con limitaciones en IA)

### Error: "TensorFlow model not found"
- Esto es normal - el modelo usa predicciones placeholder
- Para usar modelo real: coloca `model.h5` en `ml_models/incident_classifier/`

### Error: "Firebase not initialized"
- Verifica que `FIREBASE_CREDENTIALS_PATH` apunte al JSON correcto
- Las notificaciones funcionarán parcialmente sin Firebase (solo BD)

### Error de migración
```bash
# Resetear migraciones
python manage.py migrate --fake users zero
python manage.py migrate --fake
python manage.py migrate
```

## 📝 Notas Adicionales

### Sin Redis
Este proyecto **NO usa Redis**. Django-Q2 y django-eventstream usan PostgreSQL como backend.

### Media Files
Los archivos se guardan **localmente** en `/media/`. Para producción, considera usar S3 o similar.

### Modelo TensorFlow
El clasificador está implementado con soporte para placeholder. Puedes:
1. Usar tal cual (predicciones simuladas)
2. Entrenar tu propio modelo y colocarlo en `ml_models/incident_classifier/model.h5`

### Comisiones
El admin puede configurar múltiples comisiones con fecha efectiva. El sistema siempre usa la más reciente activa.

## 🤝 Contribuir

Para completar la implementación, ver `IMPLEMENTATION_STATUS.md` y seguir los patrones establecidos en:
- `apps/users/serializers.py` (ejemplo de serializers)
- Modelos existentes (todos completos)
- Servicios (todos completos)

## 📄 Licencia

[Especificar licencia]

## 👨‍💻 Autor

Proyecto desarrollado para sistema de emergencias vehiculares.

---

**Estado**: Core funcional implementado. Pendiente: views, URLs y serializers complementarios.
