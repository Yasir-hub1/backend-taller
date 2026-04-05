# 🎯 INSTRUCCIONES FINALES - Setup Backend

## ✅ LO QUE SE HA CORREGIDO

**Problema original:** `relation "users" does not exist`

**Causa raíz:**
1. ❌ Faltaban archivos `apps.py` en cada aplicación Django
2. ❌ Faltaban archivos `admin.py`
3. ❌ Las migraciones no se habían creado
4. ❌ INSTALLED_APPS usaba nombres cortos en lugar de configuraciones explícitas

**Solución aplicada:**
1. ✅ Creados 8 archivos `apps.py` (uno por cada app)
2. ✅ Creados 8 archivos `admin.py` con registro de modelos
3. ✅ Actualizado `config/settings.py` para usar `apps.users.apps.UsersConfig` etc.
4. ✅ Script automático de setup creado

---

## 🚀 PASOS PARA EJECUTAR (Orden Exacto)

### 1. Verificar que PostgreSQL esté corriendo

Tu `.env` está configurado para:
- Puerto: **5433** (no es el estándar 5432)
- Base de datos: **emergencias_vehiculares**
- Usuario: **defectdojo**
- Password: **12345678**

```bash
# Verificar que PostgreSQL responda en puerto 5433
psql -U defectdojo -h localhost -p 5433 -d emergencias_vehiculares -c "SELECT version();"

# Si la BD no existe, créala:
createdb -U defectdojo -p 5433 emergencias_vehiculares
```

### 2. Activar Virtual Environment e Instalar Dependencias

```bash
# Desde el directorio backend/
source venv/bin/activate

# Instalar todas las dependencias
pip install -r requirements.txt
```

**Tiempo estimado:** 5-10 minutos (depende de tu conexión)

### 3. Verificar Configuración de Django

```bash
# Esto NO debe dar errores
python manage.py check
```

**Salida esperada:**
```
System check identified no issues (0 silenced).
```

### 4. Crear Migraciones

```bash
# IMPORTANTE: Crear en este orden específico
python manage.py makemigrations users
python manage.py makemigrations workshops
python manage.py makemigrations vehicles
python manage.py makemigrations incidents
python manage.py makemigrations assignments
python manage.py makemigrations payments
python manage.py makemigrations notifications
```

**Salida esperada para cada comando:**
```
Migrations for 'users':
  apps/users/migrations/0001_initial.py
    - Create model User
    - Create model ClientProfile
    - Create model WorkshopOwnerProfile
```

### 5. Aplicar Migraciones

```bash
python manage.py migrate
```

**Salida esperada:**
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, django_eventstream, django_q, sessions, users, workshops, vehicles, incidents, assignments, payments, notifications
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying users.0001_initial... OK
  Applying admin.0001_initial... OK
  ...
  (unas 30-40 migraciones en total)
```

✅ **Si ves "OK" en todas las líneas, ¡éxito!**

### 6. Crear Superusuario Admin

```bash
python manage.py createsuperuser
```

**Ejemplo de interacción:**
```
Username: admin
Email: admin@example.com
Password: ********
Password (again): ********
Superuser created successfully.
```

### 7. Asignar Role de Admin

```bash
python manage.py shell
```

Dentro del shell de Python:
```python
from apps.users.models import User

# Obtener el usuario que acabas de crear
user = User.objects.get(username='admin')  # Cambia 'admin' por tu username

# Asignar role de admin
user.role = 'admin'
user.save()

# Verificar
print(f"✓ Usuario: {user.username}")
print(f"✓ Role: {user.role}")
print(f"✓ Is superuser: {user.is_superuser}")

# Salir
exit()
```

### 8. Ejecutar el Servidor

```bash
# Terminal 1: Django development server
python manage.py runserver
```

**Salida esperada:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
April 04, 2026 - 15:30:00
Django version 5.1.4, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

### 9. Ejecutar Worker de Django-Q2 (Segunda Terminal)

```bash
# Terminal 2: Worker para tareas asíncronas
source venv/bin/activate
python manage.py qcluster
```

**Salida esperada:**
```
[Q] INFO Watching 4 workers
[Q] INFO Starting worker 1
[Q] INFO Starting worker 2
[Q] INFO Starting worker 3
[Q] INFO Starting worker 4
```

---

## 🎉 VERIFICACIÓN FINAL

### 1. Acceder al Admin Panel

Abre tu navegador: `http://localhost:8000/admin/`

Credenciales: Las que creaste en paso 6

Deberías ver:
- ✅ Users
- ✅ Client profiles
- ✅ Workshop owner profiles
- ✅ Workshops
- ✅ Technicians
- ✅ Workshop ratings
- ✅ Vehicles
- ✅ Incidents
- ✅ Evidences
- ✅ Incident status history
- ✅ Assignments
- ✅ Payments
- ✅ Commission configs
- ✅ Notifications

### 2. Acceder a la Documentación API

- **Swagger UI:** `http://localhost:8000/api/docs/`
- **OpenAPI Schema:** `http://localhost:8000/api/schema/`

### 3. Verificar SSE

`http://localhost:8000/api/events/`

---

## 📊 TABLAS CREADAS EN LA BASE DE DATOS

Total: **~25 tablas**

```sql
-- Conectar a PostgreSQL
psql -U defectdojo -h localhost -p 5433 -d emergencias_vehiculares

-- Ver todas las tablas
\dt

-- Deberías ver:
users
client_profiles
workshop_owner_profiles
workshops
technicians
workshop_ratings
vehicles
incidents
evidences
incident_status_history
assignments
payments
commission_configs
notifications
django_q_*
django_eventstream_*
auth_*
django_*
```

---

## 🔧 SI ALGO SALE MAL

### Error: "Could not connect to server"
```bash
# PostgreSQL no está corriendo en puerto 5433
# Verifica:
pg_isready -h localhost -p 5433

# O revisa tu .env y ajusta DB_PORT
```

### Error: "FATAL: database does not exist"
```bash
# Crear la base de datos
createdb -U defectdojo -p 5433 emergencias_vehiculares
```

### Error: "FATAL: password authentication failed"
```bash
# Verificar password en .env
# Asegúrate que coincida con tu PostgreSQL
```

### Error: "No module named 'django'"
```bash
# No activaste el venv o no instalaste dependencias
source venv/bin/activate
pip install -r requirements.txt
```

### Error: "Circular dependency in migrations"
```bash
# Crear migraciones una por una en orden:
python manage.py makemigrations users
python manage.py migrate users
python manage.py makemigrations workshops
python manage.py migrate workshops
# etc...
```

### Reset completo (ÚLTIMA OPCIÓN)
```bash
# Borrar migraciones
find apps -path "*/migrations/*.py" -not -name "__init__.py" -delete

# Borrar BD
dropdb -U defectdojo -p 5433 emergencias_vehiculares
createdb -U defectdojo -p 5433 emergencias_vehiculares

# Recrear migraciones
python manage.py makemigrations
python manage.py migrate
```

---

## 📝 NOTAS IMPORTANTES

1. **Puerto PostgreSQL:** Tu configuración usa **5433** (no el estándar 5432). Esto es correcto si así lo configuraste.

2. **APIs Key:** Las siguientes claves en `.env` están con valores placeholder:
   - `OPENAI_API_KEY` - Necesario para IA (Whisper/GPT)
   - `STRIPE_SECRET_KEY` - Necesario para pagos
   - `FIREBASE_CREDENTIALS_PATH` - Necesario para notificaciones push

   El sistema funcionará sin ellas pero con limitaciones.

3. **Django-Q2:** Necesita estar corriendo para procesar incidentes con IA. Ejecuta `python manage.py qcluster` en una terminal separada.

4. **Media Files:** Se guardan en `/media/` localmente. Para producción considera S3.

---

## ✨ PRÓXIMOS PASOS (Después del Setup)

1. **Crear datos de prueba** - Ver `MIGRACIONES_GUIA.md` sección "Datos de Prueba"

2. **Completar Views y URLs** - Ver `IMPLEMENTATION_STATUS.md`

3. **Probar endpoints** - Usar Postman o Swagger UI

4. **Configurar APIs reales** - Agregar claves de OpenAI, Stripe, Firebase

---

## 🎯 COMANDOS RÁPIDOS (Resumen)

```bash
# Setup completo
source venv/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py makemigrations users workshops vehicles incidents assignments payments notifications
python manage.py migrate
python manage.py createsuperuser

# Ejecutar
python manage.py runserver          # Terminal 1
python manage.py qcluster           # Terminal 2
```

---

**¡Éxito!** El backend ahora debería estar completamente funcional para migraciones.

Si encuentras algún error específico, revisa `MIGRACIONES_GUIA.md` para soluciones detalladas.
