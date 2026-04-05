# Guía de Migraciones y Setup - Backend Emergencias Vehiculares

## ✅ PROBLEMA RESUELTO

El error "relation 'users' does not exist" ocurría porque:
1. ❌ Faltaban archivos `apps.py` en cada aplicación
2. ❌ Faltaban archivos `admin.py`
3. ❌ No se habían creado las migraciones

**SOLUCIÓN APLICADA:**
- ✅ Creados todos los archivos `apps.py` con configuración correcta
- ✅ Creados todos los archivos `admin.py` para gestión en Django Admin
- ✅ Actualizado `config/settings.py` para usar configuraciones explícitas de apps

---

## 🚀 PASOS PARA EJECUTAR MIGRACIONES

### Opción 1: Script Automático (Recomendado)

```bash
# Ejecutar el script de setup
./setup_migrations.sh
```

### Opción 2: Manual

```bash
# 1. Activar virtual environment
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Verificar que no haya errores
python manage.py check

# 4. Crear migraciones para cada app
python manage.py makemigrations users
python manage.py makemigrations workshops
python manage.py makemigrations vehicles
python manage.py makemigrations incidents
python manage.py makemigrations assignments
python manage.py makemigrations payments
python manage.py makemigrations notifications

# 5. Aplicar todas las migraciones
python manage.py migrate

# 6. Crear superusuario
python manage.py createsuperuser
```

---

## 📋 ORDEN DE MIGRACIONES (Importante)

Django debe crear las migraciones en este orden debido a las dependencias:

1. **users** - Primero (AUTH_USER_MODEL)
2. **workshops** - Depende de users (WorkshopOwnerProfile)
3. **vehicles** - Depende de users (ClientProfile)
4. **incidents** - Depende de users y vehicles
5. **assignments** - Depende de incidents y workshops
6. **payments** - Depende de assignments
7. **notifications** - Depende de users e incidents

---

## 🔧 VERIFICACIONES POST-MIGRACIÓN

### 1. Verificar que todas las tablas se crearon:

```bash
python manage.py dbshell
```

```sql
-- Ver todas las tablas
\dt

-- Verificar tabla users
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Salir
\q
```

### 2. Verificar modelos en Django shell:

```bash
python manage.py shell
```

```python
from apps.users.models import User, ClientProfile, WorkshopOwnerProfile
from apps.workshops.models import Workshop, Technician
from apps.vehicles.models import Vehicle
from apps.incidents.models import Incident, Evidence
from apps.assignments.models import Assignment
from apps.payments.models import Payment, CommissionConfig
from apps.notifications.models import Notification

# Verificar que no haya errores de importación
print("✓ Todos los modelos importados correctamente")

# Verificar estructura de User
User.objects.all().count()

exit()
```

---

## 🐛 SOLUCIÓN DE PROBLEMAS COMUNES

### Error: "No module named 'django'"
```bash
# Solución: Instalar dependencias
pip install -r requirements.txt
```

### Error: "No changes detected"
```bash
# Solución: Especificar la app
python manage.py makemigrations nombre_app

# O forzar detección
python manage.py makemigrations --empty nombre_app
```

### Error: "Circular dependency"
```bash
# Solución: Crear migraciones en orden específico
python manage.py makemigrations users
python manage.py migrate users
python manage.py makemigrations workshops
python manage.py migrate workshops
# ... continuar en orden
```

### Error: "AUTH_USER_MODEL refers to model 'users.User' that has not been installed"
```bash
# Verificar que en INSTALLED_APPS esté:
'apps.users.apps.UsersConfig',  # ✓ Correcto
# No: 'apps.users',  # ✗ Incorrecto
```

### Error: "relation 'xxx' already exists"
```bash
# La tabla ya existe pero Django no lo sabe
# Solución: Fake migration
python manage.py migrate nombre_app --fake
```

### Error: "Multiple apps with same label"
```bash
# Verificar que cada AppConfig tenga un 'name' único
# En cada apps.py:
class UsersConfig(AppConfig):
    name = 'apps.users'  # Debe ser único
```

---

## 📦 ESTRUCTURA DE APPS CREADA

Cada app ahora tiene:

```
apps/
├── users/
│   ├── __init__.py
│   ├── apps.py          ✅ NUEVO - Configuración de la app
│   ├── admin.py         ✅ NUEVO - Registro en Django Admin
│   ├── models.py        ✅ Ya existía
│   ├── serializers.py   ✅ Ya existía
│   └── permissions.py   ✅ Ya existía
├── workshops/
│   ├── __init__.py
│   ├── apps.py          ✅ NUEVO
│   ├── admin.py         ✅ NUEVO
│   └── models.py        ✅ Ya existía
├── vehicles/
│   ├── __init__.py
│   ├── apps.py          ✅ NUEVO
│   ├── admin.py         ✅ NUEVO
│   └── models.py        ✅ Ya existía
├── incidents/
│   ├── __init__.py
│   ├── apps.py          ✅ NUEVO
│   ├── admin.py         ✅ NUEVO
│   └── models.py        ✅ Ya existía
├── assignments/
│   ├── __init__.py
│   ├── apps.py          ✅ NUEVO
│   ├── admin.py         ✅ NUEVO
│   ├── models.py        ✅ Ya existía
│   └── engine.py        ✅ Ya existía
├── payments/
│   ├── __init__.py
│   ├── apps.py          ✅ NUEVO
│   ├── admin.py         ✅ NUEVO
│   ├── models.py        ✅ Ya existía
│   └── stripe_service.py ✅ Ya existía
├── notifications/
│   ├── __init__.py
│   ├── apps.py          ✅ NUEVO
│   ├── admin.py         ✅ NUEVO
│   ├── models.py        ✅ Ya existía
│   ├── firebase_service.py ✅ Ya existía
│   └── sse_views.py     ✅ Ya existía
└── ai_engine/
    ├── __init__.py
    ├── apps.py          ✅ NUEVO
    ├── admin.py         ✅ NUEVO
    ├── whisper_service.py ✅ Ya existía
    ├── classifier_service.py ✅ Ya existía
    ├── summary_service.py ✅ Ya existía
    └── pipeline.py      ✅ Ya existía
```

---

## ✨ DESPUÉS DE LAS MIGRACIONES

### 1. Crear Usuario Admin

```bash
python manage.py createsuperuser
```

Luego en Django shell:
```python
from apps.users.models import User

user = User.objects.get(username='tu_username')
user.role = 'admin'
user.save()
print(f"✓ Usuario {user.username} ahora es admin")
```

### 2. Acceder al Admin Panel

```bash
python manage.py runserver
```

Navega a: `http://localhost:8000/admin/`

Deberías ver todos los modelos registrados:
- Usuarios
- Talleres
- Vehículos
- Incidentes
- Asignaciones
- Pagos
- Notificaciones

---

## 🎯 DATOS DE PRUEBA (Opcional)

Puedes crear datos de prueba con Django shell:

```python
from apps.users.models import User, ClientProfile
from apps.vehicles.models import Vehicle

# Crear cliente de prueba
client_user = User.objects.create_user(
    username='cliente1',
    email='cliente@test.com',
    password='test123',
    role='client',
    first_name='Juan',
    last_name='Pérez'
)

# Crear perfil de cliente
client_profile = ClientProfile.objects.create(
    user=client_user,
    address='Calle 123',
    emergency_contact_name='María Pérez',
    emergency_contact_phone='1234567890'
)

# Crear vehículo
vehicle = Vehicle.objects.create(
    client=client_profile,
    brand='Toyota',
    model='Corolla',
    year=2020,
    plate='ABC123',
    color='Blanco',
    vehicle_type='car'
)

print("✓ Datos de prueba creados")
```

---

## 📊 ESTADO FINAL

Después de ejecutar las migraciones exitosamente:

✅ Base de datos PostgreSQL configurada
✅ 20+ tablas creadas
✅ Modelos sincronizados con BD
✅ Admin panel funcional
✅ Listo para crear endpoints (views/URLs)

---

## 🚨 SI ALGO SALE MAL

### Reset completo de base de datos:

```bash
# 1. Borrar base de datos
dropdb emergencias_vehiculares

# 2. Crear nueva
createdb emergencias_vehiculares

# 3. Borrar archivos de migración (CUIDADO!)
find apps -path "*/migrations/*.py" -not -name "__init__.py" -delete
find apps -path "*/migrations/*.pyc" -delete

# 4. Crear migraciones desde cero
python manage.py makemigrations
python manage.py migrate

# 5. Crear superusuario
python manage.py createsuperuser
```

---

**¡Éxito!** Las migraciones ahora deberían funcionar correctamente.
