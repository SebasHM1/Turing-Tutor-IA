# Turing-Tutor-IA

Sistema de tutoría inteligente con IA para estudiantes universitarios. Incluye chatbot con RAG (Retrieval-Augmented Generation), gestión de cursos, grupos, inscripciones y análisis de temas de estudio.

## 📁 Estructura del Proyecto

### **users/**
Gestión de usuarios (estudiantes y profesores):
- Autenticación personalizada con roles (Student/Teacher)
- Registro, login, y recuperación de contraseña
- Modelo de usuario con cédula, código universitario y grupo

### **courses/**
Gestión de cursos y grupos:
- Cursos con códigos únicos
- Grupos por curso (cada grupo tiene un profesor y horario)
- Inscripciones de estudiantes a grupos
- Base de conocimiento (PDFs vectorizados para RAG)
- Prompts personalizados por curso
- Temas y palabras clave para análisis estadístico
- Horarios de monitorías

### **teachers/**
Panel de profesores:
- Dashboard con sus grupos y estudiantes
- Creación y gestión de cursos y grupos
- Gestión de inscripciones (añadir/eliminar estudiantes)
- Configuración de prompts de IA por grupo
- Subida de horarios de monitorías (PDF)
- Gestión de slots de monitoría personalizados

### **chatbot/**
Sistema de chat inteligente:
- Sesiones de chat por curso
- Integración con OpenAI GPT-4
- RAG sobre PDFs subidos por profesores
- Análisis automático de temas en conversaciones
- Historial de mensajes
- Prompts específicos por grupo

## 🚀 Instalación y Configuración

### 1. Crear entorno virtual

```powershell
# Crear venv
python -m venv venv

# Activar venv (Windows PowerShell)
.\venv\Scripts\Activate

# Activar venv (Windows CMD)
venv\Scripts\activate.bat

# Activar venv (Linux/Mac)
source venv/bin/activate
```

### 2. Instalar dependencias

```powershell
cd src/turing
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Crear archivo `.env` en `src/turing/` con las siguientes variables:

```env
# ========================================
# CONFIGURACIÓN DE DJANGO
# ========================================
SECRET_KEY=                    # Clave secreta de Django (genera una con: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
DEBUG=True                     # True para desarrollo, False para producción
ALLOWED_HOSTS=localhost,127.0.0.1  # Hosts permitidos, separados por coma

# ========================================
# CONFIGURACIÓN DE BASE DE DATOS (PostgreSQL)
# ========================================
DB_NAME=                       # Nombre de la base de datos
DB_USER=                       # Usuario de PostgreSQL
DB_PASSWORD=                   # Contraseña del usuario
DB_HOST=localhost              # Host de la base de datos (localhost para desarrollo)
DB_PORT=5432                   # Puerto de PostgreSQL (5432 por defecto)

# ========================================
# CONFIGURACIÓN DE EMAIL (SMTP)
# ========================================
EMAIL_HOST=smtp.gmail.com      # Servidor SMTP (ejemplo: Gmail)
EMAIL_PORT=587                 # Puerto SMTP (587 para TLS)
EMAIL_HOST_USER=               # Correo del remitente
EMAIL_HOST_PASSWORD=           # Contraseña de aplicación (no la contraseña normal)
EMAIL_USE_TLS=True             # Usar TLS para conexión segura

# ========================================
# CONFIGURACIÓN DE OPENAI
# ========================================
OPENAI_API_KEY=                # API Key de OpenAI para GPT-4

# ========================================
# CONFIGURACIÓN DE SUPABASE STORAGE (S3)
# Usado para almacenar archivos (PDFs, horarios, etc.)
# ========================================
SUPABASE_URL=                  # URL de tu proyecto Supabase
SUPABASE_BUCKET_NAME=          # Nombre del bucket para almacenar archivos
SUPABASE_S3_REGION_NAME=       # Región de S3 (ej: us-east-1)
SUPABASE_S3_SECRET_ACCESS_KEY= # Secret key de S3
SUPABASE_S3_ACCESS_KEY_ID=     # Access key ID de S3
SUPABASE_PROJECT_ID=           # ID de tu proyecto en Supabase
```

### 4. Ejecutar migraciones

```powershell
python manage.py migrate
```

### 5. Crear superusuario (opcional)

```powershell
python manage.py createsuperuser
```

## 🏃 Ejecutar el Proyecto

### Modo desarrollo

```powershell
python manage.py runserver
```

El servidor estará disponible en: `http://localhost:8000`

### Modo producción (con Gunicorn)

```powershell
gunicorn turing.wsgi:application --bind 0.0.0.0:8000
```

## 🧪 Ejecutar Tests

```powershell
# Ejecutar todos los tests
pytest

# Ejecutar tests con verbose
pytest -v

# Ejecutar tests de una app específica
pytest users/tests.py
pytest courses/tests.py
pytest teachers/tests.py
pytest chatbot/tests.py

# Ejecutar tests con cobertura
pytest --cov=. --cov-report=html
```

## 📦 Despliegue

### Preparación para producción

1. **Configurar variables de entorno en producción:**
   - `DEBUG=False`
   - `ALLOWED_HOSTS=tudominio.com,www.tudominio.com`
   - Configurar DB_HOST con la IP/dominio de tu base de datos en producción

2. **Recopilar archivos estáticos:**
   ```powershell
   python manage.py collectstatic --noinput
   ```

3. **Ejecutar migraciones:**
   ```powershell
   python manage.py migrate
   ```

### Despliegue en Render/Railway/Heroku

1. Conectar repositorio de Git
2. Configurar variables de entorno desde el panel
3. Comando de build: `pip install -r requirements-deploy.txt`
4. Comando de inicio: `gunicorn turing.wsgi:application`

### Despliegue en servidor VPS

1. Instalar dependencias del sistema:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv postgresql nginx
   ```

2. Configurar Nginx como reverse proxy
3. Configurar Gunicorn como servicio systemd
4. Configurar SSL con Let's Encrypt (certbot)

## 🔑 Acceso al Sistema

- **Admin:** `/admin/`
- **Login:** `/login/`
- **Dashboard Profesor:** `/teachers/dashboard/`
- **Grupos Estudiante:** `/courses/my-groups/`
- **Chat:** `/chat/course/<course_id>/`

## 📝 Notas Importantes

- Los tests usan SQLite en memoria automáticamente (configurado en `settings.py`)
- Los archivos multimedia en desarrollo se guardan localmente, en producción en Supabase
- Para usar el chatbot necesitas créditos en tu cuenta de OpenAI
- Los PDFs se procesan automáticamente para RAG al subirlos

## 🛠️ Tecnologías Utilizadas

- **Backend:** Django 5.2
- **Base de datos:** PostgreSQL
- **IA:** OpenAI o3-mini, scikit-learn
- **Storage:** Supabase S3
- **Frontend:** HTML, CSS, JavaScript (vanilla)
- **Testing:** pytest, pytest-django