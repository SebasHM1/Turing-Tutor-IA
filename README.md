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

------------------------------------------------------------------------

### 🏗️ Configuración General del Servicio

-   **Nombre del servicio:** `Turing-Tutor-IA`\
-   **Región:** `Oregon (US West)`\
-   **Plan:** `Free`
    -   **0.1 CPU**\
    -   **512 MB RAM**

------------------------------------------------------------------------

### 🔗 Build & Deploy

#### **Repositorio conectado**

-   `https://github.com/SebasHM1/Turing-Tutor-IA`

#### **Branch utilizada para el deploy**

-   `deploy-render`

#### **Credenciales Git**

-   Usuario conectado para el pull del repositorio:\
    `santiagoarbobledavelasco@gmail.com`

#### **Root Directory**

-   `src/turing`\
    Render ejecuta los comandos desde esta carpeta en lugar del root del
    repositorio.

------------------------------------------------------------------------

### ⚙️ Comandos configurados en Render

#### **Build Command**

``` bash
src/turing/ $ pip install -r requirements.txt
```

#### **Pre-Deploy Command**

*(Vacío --- no se ejecuta nada antes del arranque)*

#### **Start Command**

``` bash
src/turing/ $ gunicorn turing.wsgi:application --bind 0.0.0.0:$PORT
```

------------------------------------------------------------------------

### 🚀 Auto-Deploy

-   **Modo:** `On Commit`\
    Cada push al branch configurado (`deploy-render`) desencadena
    automáticamente un nuevo despliegue.

------------------------------------------------------------------------

### 🔄 Deploy Hook

-   Render generó un **Deploy Hook privado** con este formato:

``` text
https://api.render.com/deploy/srv-d3hj8jripnbc73chssag?key=6mc2_Znguk4
```

*(Se deberia actualizar este hook por seguridad).*

------------------------------------------------------------------------

## 🛠️ Flujo real del despliegue en Render

1.  Se conectó el repositorio de GitHub al servicio de Render.
2.  Se configuró `src/turing` como **Root Directory** para ejecutar los
    comandos desde allí.
3.  Se establecieron:
    -   **Build command:** instalación desde `requirements.txt`
    -   **Start command:** ejecución con Gunicorn enlazado al puerto
        asignado por Render
4.  Se activó Auto-Deploy en modo **On Commit**.
5.  Render realiza el deploy automáticamente usando Gunicorn y el
    entorno gestionado por la plataforma.

------------------------------------------------------------------------

## ⚙️ CI/CD con GitHub Actions (Workflow real utilizado)

Se configuró un pipeline automatizado para disparar el despliegue en
Render cada vez que hay un push a la rama `deploy-render`.\
Este flujo utiliza el **Deploy Hook URL** almacenado como un secreto en
GitHub.

### Archivo: `.github/workflows/deploy.yaml`

``` yaml
name: Trigger Render Deploy

on:
  push:
    branches:
      - deploy-render

jobs:
  deploy:
    name: Trigger Render Deploy
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Deploy Hook
        run: |
          curl -X POST "${{ secrets.RENDER_DEPLOY_HOOK_URL }}"
```

### Explicación del flujo CI/CD

-   Cada push a la rama `deploy-render` activa este workflow.
-   GitHub Actions ejecuta un job en una máquina Linux.
-   Se envía una petición POST al Deploy Hook privado de Render.
-   Render inicia un despliegue inmediato utilizando la configuración
    del servicio.

Este pipeline garantiza un despliegue consistente y automatizado sin
necesidad de usar el panel manualmente.

------------------------------------------------------------------------