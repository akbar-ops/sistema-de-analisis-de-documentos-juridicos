# 📚 DOCANA - Sistema de Análisis de Documentos Jurídicos

<p align="center">
  <img src="https://img.shields.io/badge/Django-5.1.4-092E20?style=for-the-badge&logo=django&logoColor=white" />
  <img src="https://img.shields.io/badge/Vue.js-3.5-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-336791?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Celery-5.4-37814A?style=for-the-badge&logo=celery&logoColor=white" />
  <img src="https://img.shields.io/badge/Ollama-LLM-000000?style=for-the-badge&logo=ollama&logoColor=white" />
</p>

Sistema inteligente para análisis, clasificación y búsqueda semántica de documentos jurídicos. Utiliza técnicas avanzadas de NLP, clustering y modelos de lenguaje (LLM) para ayudar a profesionales del derecho a encontrar precedentes, analizar jurisprudencia y redactar documentos.

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación](#-instalación)
  - [1. Base de Datos PostgreSQL con pgvector](#1-base-de-datos-postgresql-con-pgvector)
  - [2. Backend Django](#2-backend-django)
  - [3. Frontend Vue.js](#3-frontend-vuejs)
  - [4. Servicios Adicionales](#4-servicios-adicionales)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [Comandos de Gestión](#-comandos-de-gestión)
- [API Endpoints](#-api-endpoints)
- [Despliegue en Producción](#-despliegue-en-producción)
- [Personalización](#-personalización)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Solución de Problemas](#-solución-de-problemas)
- [Licencia](#-licencia)

---

## ✨ Características

### 📄 Procesamiento de Documentos

- **Extracción de texto** automática de PDFs, DOCX, DOC, TXT y RTF
- **Chunking inteligente** de documentos largos para procesamiento eficiente
- **Generación de embeddings** usando `paraphrase-multilingual-mpnet-base-v2` (768 dimensiones)
- **Extracción de metadatos** automática mediante LLM (partes, fechas, números de caso)

### 🔍 Búsqueda Semántica

- **Búsqueda por similitud vectorial** usando pgvector
- **Búsqueda híbrida** combinando metadatos legales y similitud semántica
- **Búsqueda por texto o documento** - sube un archivo y encuentra documentos similares
- **Soporte PDF** con extracción de texto mediante pdfjs-dist

### 📊 Visualización y Clustering

- **Clustering HDBSCAN** para agrupar documentos similares automáticamente
- **Reducción dimensional UMAP** para visualización 2D
- **BERTopic** para modelado de tópicos avanzado
- **Gráficos interactivos** con ECharts y zoom automático

### 💬 Chat Inteligente (RAG)

- **Chat con documentos** usando Ollama y RAG
- **Contexto de chunks relevantes** para respuestas precisas
- **Historial de conversación** para contexto continuo

### ✍️ Asistente de Redacción

- **Generación de borradores** de documentos jurídicos
- **Sugerencias basadas en documentos similares**

---

## 🏗 Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Vue 3)                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │  Home   │ │ Upload  │ │ Clusters│ │ Topics  │ │  Chat   │   │
│  │  View   │ │  View   │ │  View   │ │  View   │ │  View   │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│                    Vuetify 3 + ECharts                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
┌────────────────────────────▼────────────────────────────────────┐
│                      BACKEND (Django 5)                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Documents     │  │      Chat       │  │      Core       │  │
│  │   (API/Views)   │  │  (RAG Service)  │  │   (Services)    │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │           │
│  ┌────────▼────────────────────▼────────────────────▼────────┐  │
│  │                    SERVICES LAYER                          │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │  │
│  │  │  Embedding  │ │  Similarity │ │   Search    │          │  │
│  │  │   Service   │ │   Service   │ │   Service   │          │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘          │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │  │
│  │  │  Clustering │ │    RAG      │ │   Writing   │          │  │
│  │  │   Service   │ │   Service   │ │  Assistant  │          │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘          │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────┬──────────────────────┬──────────────────────┬────────────┘
       │                      │                      │
┌──────▼──────┐  ┌────────────▼────────────┐  ┌─────▼─────────────┐
│  PostgreSQL │  │     Celery Workers      │  │      Ollama       │
│  + pgvector │  │  ┌─────┐  ┌─────────┐   │  │   (llama3.2:1b)   │
│             │  │  │Redis│  │Beat/Beat│   │  │                   │
│  (Vectors)  │  │  └─────┘  └─────────┘   │  │   (Summarization) │
└─────────────┘  └─────────────────────────┘  └───────────────────┘
```

---

## 📦 Requisitos Previos

### Software Necesario

| Software    | Versión Mínima           | Propósito                             |
| ----------- | ------------------------ | ------------------------------------- |
| **Docker**  | 20.10+                   | Base de datos PostgreSQL con pgvector |
| **Python**  | 3.10+ (recomendado 3.11) | Backend Django                        |
| **Node.js** | 18+ (recomendado 20+)    | Frontend Vue.js                       |
| **Redis**   | 6+                       | Message broker para Celery            |
| **Ollama**  | Latest                   | LLM para resúmenes y chat             |

### Recursos de Hardware (Recomendado)

- **RAM**: 8GB mínimo (16GB recomendado para modelos grandes)
- **CPU**: 4 cores mínimo
- **Almacenamiento**: 20GB+ para modelos y documentos
- **GPU** (Opcional): NVIDIA para acelerar embeddings

---

## 🚀 Instalación

### 1. Base de Datos PostgreSQL con pgvector

```bash
# Clonar el repositorio
git clone <tu-repositorio>
cd docana

# Iniciar PostgreSQL con pgvector usando Docker
docker-compose up -d

# Verificar que el contenedor está corriendo
docker ps
```

**docker-compose.yml** ya está configurado con:

- Imagen: `ankane/pgvector:latest`
- Puerto: `5432`
- Base de datos: `main_database`
- Usuario: `vicari`
- Contraseña: `41818`
- Volume persistente: `pgdata_noollama`

La extensión pgvector se inicializa automáticamente con el script `init-db/01-create-pgvector.sql`.

### 2. Backend Django

```bash
# Navegar al directorio backend
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Linux/Mac:
source venv/bin/activate
# En Windows:
# venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Poblar catálogos (áreas legales y tipos de documento)
python manage.py populate_catalogs

# Crear superusuario (opcional, para admin)
python manage.py createsuperuser
```

### 3. Frontend Vue.js

```bash
# En otra terminal, navegar al directorio frontend
cd frontend

# Instalar dependencias
npm install

# Para desarrollo
npm run dev

# Para producción
npm run build
```

### 4. Servicios Adicionales

#### Redis (Message Broker para Celery)

```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# macOS con Homebrew
brew install redis
brew services start redis

# Docker (alternativa)
docker run -d --name redis -p 6379:6379 redis:alpine
```

#### Ollama (LLM para Resúmenes y Chat)

```bash
# Instalar Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Iniciar servicio Ollama
ollama serve

# En otra terminal, descargar el modelo (llama3.2:1b por defecto)
ollama pull llama3.2:1b

# Para mejor calidad (opcional, requiere más recursos):
ollama pull llama3.2:3b
```

---

## ⚙️ Configuración

### Archivo Principal: `backend/config/settings.py`

#### Base de Datos

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'main_database',      # Nombre de la base de datos
        'USER': 'vicari',             # Usuario PostgreSQL
        'PASSWORD': '41818',          # Contraseña
        'HOST': '127.0.0.1',          # Host (localhost para Docker local)
        'PORT': '5432',               # Puerto PostgreSQL
    }
}
```

#### Celery (Tareas Asíncronas)

```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Redis como broker
CELERY_RESULT_BACKEND = 'django-db'             # Resultados en DB
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/La_Paz'              # Tu zona horaria
```

#### Ollama (LLM)

```python
OLLAMA_BASE_URL = 'http://localhost:11434'      # URL de Ollama
OLLAMA_DEFAULT_MODEL = 'llama3.2:1b'            # Modelo por defecto (rápido)
# Alternativas: 'llama3.2:3b' (mejor), 'llama3.1:8b' (mejor aún), 'mixtral' (avanzado)
```

### Docker Compose: `docker-compose.yml`

Para cambiar credenciales de base de datos:

```yaml
services:
  db:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: main_database # Cambiar nombre de BD
      POSTGRES_USER: vicari # Cambiar usuario
      POSTGRES_PASSWORD: 41818 # Cambiar contraseña
    ports:
      - "5432:5432" # Cambiar puerto si es necesario
```

---

## 🎯 Uso

### Iniciar Todos los Servicios

```bash
# Terminal 1: Base de Datos
cd docana
docker-compose up -d

# Terminal 2: Redis (si no está como servicio del sistema)
redis-server

# Terminal 3: Ollama
ollama serve

# Terminal 4: Celery Worker (procesamiento de documentos)
cd backend
source venv/bin/activate
celery -A config worker -l info -Q celery,high_priority,low_priority

# Terminal 5: Celery Beat (tareas programadas, opcional)
celery -A config beat -l info

# Terminal 6: Backend Django
cd backend
source venv/bin/activate
python manage.py runserver

# Terminal 7: Frontend Vue.js
cd frontend
npm run dev
```

### Scripts de Utilidad (Backend)

```bash
# Iniciar todos los servicios de backend
./start_all.sh

# Ver estado de servicios
./status.sh

# Detener todos los servicios
./stop_all.sh

# Reiniciar servicios
./restart.sh
```

### Acceso a la Aplicación

- **Frontend**: http://localhost:5173 (desarrollo)
- **Backend API**: http://localhost:8000/api/
- **Admin Django**: http://localhost:8000/admin/

---

## 📜 Comandos de Gestión

### Poblar Catálogos

```bash
python manage.py populate_catalogs
```

Crea las áreas legales y tipos de documentos predefinidos:

- **Áreas Legales**: Civil, Penal, Laboral, Familia, Administrativa, Constitucional, etc.
- **Tipos de Documento**: Sentencia, Auto, Resolución, Demanda, etc.

### Subida Masiva de Documentos

```bash
# Uso básico
python manage.py bulk_upload_documents /ruta/a/carpeta/documentos

# Con opciones avanzadas
python manage.py bulk_upload_documents /ruta/carpeta \
    --batch-size 20 \           # Documentos por lote
    --processing-mode async \   # async o sync
    --skip-existing \           # No re-procesar existentes
    --workers 4 \               # Workers paralelos (modo sync)
    --use-celery                # Usar cola Celery
```

**Opciones Disponibles:**

| Opción              | Descripción                           | Default |
| ------------------- | ------------------------------------- | ------- |
| `--batch-size`      | Número de documentos por lote         | 10      |
| `--processing-mode` | `async` (Celery) o `sync` (inmediato) | async   |
| `--skip-existing`   | Omitir documentos ya cargados         | False   |
| `--workers`         | Workers paralelos en modo sync        | 2       |
| `--use-celery`      | Encolar en Celery                     | False   |

### Regenerar Chunks con Limpieza de Encabezados (NUEVO)

Los documentos judiciales del Poder Judicial del Perú contienen encabezados repetitivos en cada página:

- Logo y nombre de institución
- Número de expediente
- Número de página
- Sala/Juzgado

El comando `regenerate_chunks_clean` limpia estos encabezados antes de crear chunks:

```bash
# Ver qué se limpiaría (sin hacer cambios)
python manage.py regenerate_chunks_clean --dry-run

# Regenerar chunks para todos los documentos
python manage.py regenerate_chunks_clean --force

# Regenerar para un documento específico
python manage.py regenerate_chunks_clean --document-id <uuid>

# Regenerar chunks + embeddings del documento
python manage.py regenerate_chunks_clean --force --regenerate-embeddings

# Opciones avanzadas
python manage.py regenerate_chunks_clean \
    --force \
    --chunk-size 1000 \
    --chunk-overlap 200 \
    --regenerate-embeddings \
    --batch-size 20
```

**Opciones del comando:**

| Opción                    | Descripción                                      |
| ------------------------- | ------------------------------------------------ |
| `--dry-run`               | Solo muestra qué se limpiaría, sin hacer cambios |
| `--force`                 | Procesa todos los documentos                     |
| `--document-id`           | Procesa solo un documento específico             |
| `--chunk-size`            | Tamaño de chunk en caracteres (default: 1000)    |
| `--chunk-overlap`         | Solapamiento entre chunks (default: 200)         |
| `--regenerate-embeddings` | También regenera embedding del documento         |
| `--skip-chunk-embeddings` | No generar embeddings para chunks                |
| `--batch-size`            | Documentos por lote (default: 10)                |

### Regenerar Embeddings

```bash
# Regenerar embeddings limpios (768d) para todos los documentos
python manage.py regenerate_clean_embeddings

# Regenerar embedding para documento específico
python manage.py regenerate_clean_embeddings --document-id <uuid>
```

### Regenerar Embeddings de Chunks (NUEVO para RAG)

Los chunks ahora tienen embeddings de 768 dimensiones para mejorar la calidad del RAG:

```bash
# Regenerar embeddings 768d para chunks de todos los documentos
python manage.py regenerate_chunk_embeddings --force

# Regenerar para un documento específico
python manage.py regenerate_chunk_embeddings --document-id <uuid>

# Con tamaño de lote personalizado
python manage.py regenerate_chunk_embeddings --force --batch-size 100
```

**Opciones:**

| Opción          | Descripción                                   |
| --------------- | --------------------------------------------- |
| `--force`       | Regenera embeddings para todos los documentos |
| `--document-id` | Regenera solo para chunks de un documento     |
| `--batch-size`  | Número de chunks por lote (default: 50)       |

> **Nota**: El RAG usa automáticamente los embeddings de 768d si están disponibles,
> con fallback a 384d para chunks antiguos.

### Regenerar Clustering

```bash
# Regenerar clusters HDBSCAN y coordenadas UMAP
python regenerate_cluster_graph.py
```

---

## 🔌 API Endpoints

### Documentos

| Método | Endpoint                          | Descripción          |
| ------ | --------------------------------- | -------------------- |
| GET    | `/api/documents/`                 | Listar documentos    |
| POST   | `/api/documents/`                 | Subir documento      |
| GET    | `/api/documents/{id}/`            | Obtener documento    |
| DELETE | `/api/documents/{id}/`            | Eliminar documento   |
| GET    | `/api/documents/{id}/similar/`    | Documentos similares |
| POST   | `/api/documents/search/`          | Búsqueda avanzada    |
| POST   | `/api/documents/semantic_search/` | Búsqueda semántica   |
| GET    | `/api/documents/clusters_data/`   | Datos de clustering  |
| GET    | `/api/documents/bertopic_topics/` | Tópicos BERTopic     |
| POST   | `/api/documents/bulk_upload/`     | Subida masiva        |

### Chat

| Método | Endpoint                   | Descripción          |
| ------ | -------------------------- | -------------------- |
| POST   | `/api/chat/document_chat/` | Chat sobre documento |

### Tareas

| Método | Endpoint                  | Descripción          |
| ------ | ------------------------- | -------------------- |
| GET    | `/api/tasks/`             | Listar tareas        |
| GET    | `/api/tasks/{id}/`        | Estado de tarea      |
| GET    | `/api/tasks/queue_stats/` | Estadísticas de cola |

### Catálogos

| Método | Endpoint                      | Descripción        |
| ------ | ----------------------------- | ------------------ |
| GET    | `/api/documents/legal_areas/` | Áreas legales      |
| GET    | `/api/documents/doc_types/`   | Tipos de documento |

---

## 🌐 Despliegue en Producción

### 1. Variables de Entorno

Crear archivo `.env` en el directorio `backend`:

```env
# Django
DEBUG=False
SECRET_KEY=tu-clave-secreta-muy-segura
ALLOWED_HOSTS=tudominio.com,www.tudominio.com

# Base de Datos
DB_NAME=main_database
DB_USER=vicari
DB_PASSWORD=contraseña-segura
DB_HOST=localhost
DB_PORT=5432

# Celery/Redis
CELERY_BROKER_URL=redis://localhost:6379/0

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b

# CORS
CORS_ALLOWED_ORIGINS=https://tudominio.com
```

### 2. Configuración Nginx

```nginx
upstream django {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name tudominio.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name tudominio.com;

    ssl_certificate /etc/letsencrypt/live/tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tudominio.com/privkey.pem;

    # Frontend estático
    location / {
        root /var/www/docana/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API Backend
    location /api {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Media files
    location /media {
        alias /var/www/docana/backend/media;
    }

    # Static files (admin)
    location /static {
        alias /var/www/docana/backend/staticfiles;
    }
}
```

### 3. Gunicorn para Django

```bash
# Instalar Gunicorn
pip install gunicorn

# Ejecutar
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### 4. Supervisor para Servicios

Crear `/etc/supervisor/conf.d/docana.conf`:

```ini
[program:docana-django]
command=/var/www/docana/backend/venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
directory=/var/www/docana/backend
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/docana/django.log

[program:docana-celery]
command=/var/www/docana/backend/venv/bin/celery -A config worker -l info -Q celery,high_priority,low_priority
directory=/var/www/docana/backend
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/docana/celery.log

[program:docana-celery-beat]
command=/var/www/docana/backend/venv/bin/celery -A config beat -l info
directory=/var/www/docana/backend
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/docana/celery-beat.log
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

### 5. Build Frontend para Producción

```bash
cd frontend

# Configurar URL del API en .env.production
echo "VITE_API_URL=https://tudominio.com/api" > .env.production

# Build
npm run build

# Copiar a directorio de producción
cp -r dist /var/www/docana/frontend/
```

---

## 🎨 Personalización

### Cambiar Modelo de Embeddings

En `backend/apps/documents/services/clean_embeddings_service.py`:

```python
class CleanEmbeddingService:
    MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'  # 768d
    # Alternativas:
    # 'sentence-transformers/all-MiniLM-L6-v2'  # 384d, más rápido
    # 'sentence-transformers/all-mpnet-base-v2'  # 768d, solo inglés
```

### Cambiar Modelo LLM

En `backend/config/settings.py`:

```python
OLLAMA_DEFAULT_MODEL = 'llama3.2:1b'   # Rápido, recursos bajos
# Alternativas:
# 'llama3.2:3b'     # Mejor calidad, más recursos
# 'llama3.1:8b'     # Alta calidad, requiere 8GB+ RAM
# 'mixtral:8x7b'    # Muy alta calidad, requiere 32GB+ RAM
```

### Parámetros de Clustering

En `backend/apps/documents/services/clustering_service.py`:

```python
class DocumentClusteringService:
    # UMAP
    N_NEIGHBORS = 15      # Vecinos para UMAP (más = estructura global)
    MIN_DIST = 0.1        # Distancia mínima (más bajo = clusters más compactos)
    N_COMPONENTS = 2      # Dimensiones de salida

    # HDBSCAN
    MIN_CLUSTER_SIZE = 3  # Tamaño mínimo de cluster
    MIN_SAMPLES = 2       # Muestras mínimas para core point
```

### Personalizar Limpieza de Encabezados (NUEVO)

El servicio `HeaderCleanerService` detecta y elimina encabezados repetitivos de documentos judiciales.

En `backend/apps/documents/services/header_cleaner_service.py`:

```python
class HeaderCleanerService:
    # Patrones de institución (regex)
    INSTITUTION_PATTERNS = [
        r'(?i)CORTE\s+SUPERIOR\s+(DE\s+)?JUSTICIA\s+(DE\s+)?\w+',
        r'(?i)PODER\s+JUDICIAL\s+(DEL\s+)?PER[UÚ]',
        r'(?i)SALA\s+(LABORAL|PENAL|CIVIL).*',
        # Agregar más patrones aquí
    ]

    # Patrones de metadatos repetitivos
    METADATA_PATTERNS = [
        r'(?i)EXP\.?\s*N[°º.]?\s*:?\s*\d{4,5}-\d{4}.*',  # Expediente
        r'(?i)P[aá]gina\s+\d+\s+de\s+\d+',                 # Página X de Y
        r'(?i)PROCEDE\s*:\s*\w+',                          # Procedencia
        # Agregar más patrones aquí
    ]

    # Stopwords legales adicionales
    LEGAL_STOPWORDS = {
        'expediente', 'resolución', 'sala', 'corte', 'superior',
        # Agregar más palabras aquí
    }
```

Para probar la limpieza con tus propios documentos:

```bash
# Ejecutar script de prueba
cd backend
python test_header_cleaner.py

# Ver qué se limpiaría en documentos existentes
python manage.py regenerate_chunks_clean --dry-run
```

### Agregar Nuevas Áreas Legales

En `backend/apps/documents/management/commands/populate_catalogs.py`:

```python
LEGAL_AREAS = [
    {'name': 'Civil', 'description': 'Derecho Civil'},
    {'name': 'Penal', 'description': 'Derecho Penal'},
    # Agregar nuevas:
    {'name': 'Tributario', 'description': 'Derecho Tributario'},
    {'name': 'Ambiental', 'description': 'Derecho Ambiental'},
]
```

---

## 📁 Estructura del Proyecto

```
docana/
├── docker-compose.yml          # Configuración Docker (PostgreSQL + pgvector)
├── init-db/                    # Scripts de inicialización de BD
│   └── 01-create-pgvector.sql  # Crear extensión pgvector
├── backend/
│   ├── manage.py               # Django management
│   ├── requirements.txt        # Dependencias Python
│   ├── config/
│   │   ├── settings.py         # ⚙️ Configuración principal Django
│   │   ├── celery.py           # Configuración Celery
│   │   ├── urls.py             # URLs principales
│   │   └── wsgi.py             # WSGI para producción
│   ├── apps/
│   │   ├── documents/          # 📄 App principal de documentos
│   │   │   ├── models.py       # Modelos (Document, Chunk, Task)
│   │   │   ├── views.py        # ViewSets de API
│   │   │   ├── serializers.py  # Serializers DRF
│   │   │   ├── tasks.py        # Tareas Celery
│   │   │   ├── services/       # Servicios de negocio
│   │   │   │   ├── embedding_service.py      # Generación embeddings
│   │   │   │   ├── clean_embeddings_service.py
│   │   │   │   ├── similarity_service.py     # Búsqueda similar
│   │   │   │   ├── search_service.py         # Búsqueda semántica
│   │   │   │   ├── clustering_service.py     # HDBSCAN/UMAP
│   │   │   │   ├── rag_service.py            # RAG para chat
│   │   │   │   └── parsers/                  # Extractores de texto
│   │   │   └── management/commands/          # Comandos Django
│   │   │       ├── populate_catalogs.py      # Poblar catálogos
│   │   │       └── bulk_upload_documents.py  # Subida masiva
│   │   ├── chat/               # 💬 App de chat con documentos
│   │   │   └── views.py        # RAG chat endpoint
│   │   └── core/               # Servicios compartidos
│   │       └── services/
│   │           └── ollama_agent/  # Integración Ollama
│   └── media/                  # Archivos subidos
│       └── documentos/         # Documentos PDF/DOCX
├── frontend/
│   ├── package.json            # Dependencias npm
│   ├── vite.config.mjs         # Configuración Vite
│   ├── index.html              # Entry point HTML
│   └── src/
│       ├── main.js             # Entry point Vue
│       ├── App.vue             # Componente raíz
│       ├── router/index.js     # Configuración de rutas
│       ├── views/              # Páginas principales
│       │   ├── Home.vue        # Inicio
│       │   ├── SimpleUploadView.vue    # Subida/análisis
│       │   ├── ClustersViewECharts.vue # 📊 Vista de clusters
│       │   ├── TopicsViewECharts.vue   # BERTopic view
│       │   ├── QueueView.vue   # Cola de tareas
│       │   └── StatsView.vue   # Estadísticas
│       ├── components/         # Componentes reutilizables
│       │   ├── SearchPanel.vue         # Panel de búsqueda
│       │   ├── ClusterDocumentsList.vue
│       │   ├── ChatFloating.vue        # Chat flotante
│       │   └── WritingAssistant.vue    # Asistente redacción
│       └── composables/        # Composables Vue
│           ├── useDocuments.js
│           ├── useChatAnalysis.js
│           └── useCatalogs.js
└── README.md                   # Este archivo
```

---

## 🔧 Solución de Problemas

### Error: pgvector extension not found

```bash
# Verificar que el contenedor está corriendo
docker ps

# Reiniciar contenedor
docker-compose down
docker-compose up -d

# Verificar extensión
docker exec -it <container_id> psql -U vicari -d main_database -c "SELECT * FROM pg_extension;"
```

### Error: Celery no procesa tareas

```bash
# Verificar que Redis está corriendo
redis-cli ping  # Debería responder "PONG"

# Verificar worker Celery
celery -A config inspect active

# Reiniciar worker
pkill -f 'celery'
celery -A config worker -l info -Q celery,high_priority,low_priority
```

### Error: Ollama connection refused

```bash
# Verificar que Ollama está corriendo
curl http://localhost:11434/api/tags

# Si no está corriendo
ollama serve

# Verificar que el modelo está descargado
ollama list
ollama pull llama3.2:1b
```

### Error: Out of memory al generar embeddings

```python
# En clean_embeddings_service.py, reducir batch size:
BATCH_SIZE = 8  # Reducir de 32 a 8
```

### Error: CORS en producción

En `backend/config/settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    "https://tudominio.com",
    "https://www.tudominio.com",
]
```

---

## 📊 Modelos de Datos Principales

### Document

```python
- document_id: UUID (PK)
- title: CharField
- content: TextField (texto extraído)
- summary: TextField (resumen LLM)
- file_path: FileField
- status: enum (pending, processing, processed, error)
- clean_embedding: VectorField(768)  # Embedding principal
- enhanced_embedding: VectorField(384)
- hdbscan_cluster: IntegerField
- umap_x, umap_y: FloatField
- legal_area: ForeignKey
- doc_type: ForeignKey
- case_number, resolution_number: CharField
- parties: JSONField
- issue_date: DateField
```

### DocumentChunk

```python
- chunk_id: UUID (PK)
- document: ForeignKey(Document)
- content: TextField
- chunk_index: IntegerField
- embedding: VectorField(768)
```

### DocumentTask

```python
- task_id: CharField (PK)
- document: ForeignKey(Document)
- task_type: enum (upload, analysis, clustering, etc.)
- status: enum (pending, started, progress, completed, failed)
- progress_percent: IntegerField
- progress_message: TextField
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

---

## 👥 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

---

## 📞 Soporte

Si tienes preguntas o problemas:

1. Revisa la sección [Solución de Problemas](#-solución-de-problemas)
2. Busca en [Issues existentes](../../issues)
3. Crea un nuevo [Issue](../../issues/new)

---

<p align="center">
  Desarrollado con ❤️ para la comunidad jurídica
</p>
