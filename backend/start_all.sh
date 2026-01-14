#!/bin/bash

# 🚀 Script para iniciar todo el backend (Django + Celery + Redis)
# Uso: ./start_all.sh

set -e  # Salir si hay error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$BACKEND_DIR/venv"
PYTHON="$VENV_PATH/bin/python"
CELERY="$VENV_PATH/bin/celery"

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🚀 Iniciando Backend - Poder Judicial Docs               ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# Verificar que estamos en el directorio correcto
if [ ! -f "$BACKEND_DIR/manage.py" ]; then
    echo -e "${RED}❌ Error: manage.py no encontrado${NC}"
    echo "Ejecuta desde el directorio backend"
    exit 1
fi

# Verificar virtualenv
if [ ! -f "$PYTHON" ]; then
    echo -e "${RED}❌ Error: virtualenv no encontrado en $VENV_PATH${NC}"
    exit 1
fi

echo -e "\n${GREEN}✓${NC} Directorio backend: $BACKEND_DIR"
echo -e "${GREEN}✓${NC} Python: $PYTHON"

# ============================================================================
# 1. VERIFICAR REDIS
# ============================================================================
echo -e "\n${YELLOW}[1/4]${NC} Verificando Redis..."

if pgrep redis-server > /dev/null; then
    echo -e "${GREEN}✓${NC} Redis ya está corriendo"
else
    echo -e "${YELLOW}⚠${NC}  Redis no está corriendo"
    echo "Iniciando Redis en background..."
    redis-server --daemonize yes --port 6379
    sleep 2
    if pgrep redis-server > /dev/null; then
        echo -e "${GREEN}✓${NC} Redis iniciado correctamente"
    else
        echo -e "${RED}❌ Error al iniciar Redis${NC}"
        echo "Instala Redis: sudo dnf install redis"
        exit 1
    fi
fi

# ============================================================================
# 2. CELERY WORKER - HIGH PRIORITY QUEUE
# ============================================================================
echo -e "\n${YELLOW}[2/4]${NC} Iniciando Celery Worker (high_priority)..."

# Verificar si ya está corriendo
if pgrep -f "celery.*high_priority" > /dev/null; then
    echo -e "${YELLOW}⚠${NC}  Celery high_priority ya está corriendo"
    echo "Para reiniciar: ./stop_all.sh && ./start_all.sh"
else
    nohup $CELERY -A config worker \
        -Q high_priority \
        -l info \
        -n worker_high@%h \
        --concurrency=1 \
        > "$BACKEND_DIR/logs/celery_high.log" 2>&1 &
    
    sleep 2
    echo -e "${GREEN}✓${NC} Celery high_priority iniciado (PID: $(pgrep -f 'celery.*high_priority' | head -1))"
    echo "   Log: $BACKEND_DIR/logs/celery_high.log"
fi

# ============================================================================
# 3. CELERY WORKER - DEFAULT QUEUE
# ============================================================================
echo -e "\n${YELLOW}[3/4]${NC} Iniciando Celery Worker (default)..."

if pgrep -f "celery.*worker.*default" > /dev/null; then
    echo -e "${YELLOW}⚠${NC}  Celery default ya está corriendo"
else
    nohup $CELERY -A config worker \
        -Q default \
        -l info \
        -n worker_default@%h \
        --concurrency=1 \
        > "$BACKEND_DIR/logs/celery_default.log" 2>&1 &
    
    sleep 2
    echo -e "${GREEN}✓${NC} Celery default iniciado (PID: $(pgrep -f 'celery.*worker.*default' | head -1))"
    echo "   Log: $BACKEND_DIR/logs/celery_default.log"
fi

# ============================================================================
# 4. DJANGO DEVELOPMENT SERVER
# ============================================================================
echo -e "\n${YELLOW}[4/4]${NC} Iniciando Django..."

if pgrep -f "manage.py runserver" > /dev/null; then
    echo -e "${YELLOW}⚠${NC}  Django ya está corriendo"
    DJANGO_PID=$(pgrep -f "manage.py runserver" | head -1)
    echo "   PID: $DJANGO_PID"
else
    echo "Iniciando Django en foreground (Ctrl+C para detener)..."
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    
    cd "$BACKEND_DIR"
    $PYTHON manage.py runserver
fi

# Nota: Este script se queda corriendo con Django en foreground
# Para detener todo: Ctrl+C aquí + ejecutar ./stop_all.sh
