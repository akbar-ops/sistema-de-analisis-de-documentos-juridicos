#!/bin/bash

# 📊 Script para verificar el estado de todos los servicios
# Uso: ./status.sh

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   📊 Estado del Backend - Poder Judicial Docs              ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# ============================================================================
# 1. REDIS
# ============================================================================
echo -e "\n${CYAN}━━━ REDIS ━━━${NC}"

if pgrep redis-server > /dev/null; then
    REDIS_PID=$(pgrep redis-server)
    REDIS_MEM=$(ps -o rss= -p $REDIS_PID | awk '{printf "%.1f MB", $1/1024}')
    echo -e "${GREEN}✓ CORRIENDO${NC}"
    echo "  PID: $REDIS_PID"
    echo "  Memoria: $REDIS_MEM"
    
    # Verificar conectividad
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "  Conectividad: ${GREEN}OK${NC}"
    else
        echo -e "  Conectividad: ${RED}ERROR${NC}"
    fi
else
    echo -e "${RED}✗ NO CORRIENDO${NC}"
    echo "  Iniciar: redis-server --daemonize yes"
fi

# ============================================================================
# 2. CELERY HIGH PRIORITY
# ============================================================================
echo -e "\n${CYAN}━━━ CELERY WORKER - HIGH PRIORITY ━━━${NC}"

if pgrep -f "celery.*high_priority" > /dev/null; then
    CELERY_HIGH_PID=$(pgrep -f "celery.*high_priority" | head -1)
    CELERY_HIGH_MEM=$(ps -o rss= -p $CELERY_HIGH_PID | awk '{printf "%.1f MB", $1/1024}')
    echo -e "${GREEN}✓ CORRIENDO${NC}"
    echo "  PID: $CELERY_HIGH_PID"
    echo "  Memoria: $CELERY_HIGH_MEM"
    echo "  Queue: high_priority"
    echo "  Concurrency: 1"
else
    echo -e "${RED}✗ NO CORRIENDO${NC}"
    echo "  Iniciar: celery -A config worker -Q high_priority -l info -n worker_high@%h --concurrency=1"
fi

# ============================================================================
# 3. CELERY DEFAULT
# ============================================================================
echo -e "\n${CYAN}━━━ CELERY WORKER - DEFAULT ━━━${NC}"

if pgrep -f "celery.*worker.*default" > /dev/null; then
    CELERY_DEF_PID=$(pgrep -f "celery.*worker.*default" | head -1)
    CELERY_DEF_MEM=$(ps -o rss= -p $CELERY_DEF_PID | awk '{printf "%.1f MB", $1/1024}')
    echo -e "${GREEN}✓ CORRIENDO${NC}"
    echo "  PID: $CELERY_DEF_PID"
    echo "  Memoria: $CELERY_DEF_MEM"
    echo "  Queue: default"
    echo "  Concurrency: 1"
else
    echo -e "${RED}✗ NO CORRIENDO${NC}"
    echo "  Iniciar: celery -A config worker -Q default -l info -n worker_default@%h --concurrency=1"
fi

# ============================================================================
# 4. DJANGO
# ============================================================================
echo -e "\n${CYAN}━━━ DJANGO DEVELOPMENT SERVER ━━━${NC}"

if pgrep -f "manage.py runserver" > /dev/null; then
    DJANGO_PID=$(pgrep -f "manage.py runserver" | head -1)
    DJANGO_MEM=$(ps -o rss= -p $DJANGO_PID | awk '{printf "%.1f MB", $1/1024}')
    echo -e "${GREEN}✓ CORRIENDO${NC}"
    echo "  PID: $DJANGO_PID"
    echo "  Memoria: $DJANGO_MEM"
    echo "  URL: http://127.0.0.1:8000/"
    
    # Verificar conectividad HTTP
    if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
        echo -e "  HTTP: ${GREEN}RESPONDE${NC}"
    else
        echo -e "  HTTP: ${YELLOW}NO RESPONDE${NC}"
    fi
else
    echo -e "${RED}✗ NO CORRIENDO${NC}"
    echo "  Iniciar: python manage.py runserver"
fi

# ============================================================================
# 5. OLLAMA
# ============================================================================
echo -e "\n${CYAN}━━━ OLLAMA ━━━${NC}"

if pgrep ollama > /dev/null; then
    OLLAMA_PID=$(pgrep ollama)
    OLLAMA_MEM=$(ps -o rss= -p $OLLAMA_PID | awk '{printf "%.1f MB", $1/1024}')
    echo -e "${GREEN}✓ CORRIENDO${NC}"
    echo "  PID: $OLLAMA_PID"
    echo "  Memoria: $OLLAMA_MEM"
    
    # Verificar conectividad
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "  API: ${GREEN}RESPONDE${NC}"
        # Obtener modelo configurado
        OLLAMA_MODEL=$(grep "OLLAMA_MODEL" config/settings.py | grep -v "#" | cut -d"'" -f2)
        echo "  Modelo: $OLLAMA_MODEL"
    else
        echo -e "  API: ${RED}NO RESPONDE${NC}"
    fi
else
    echo -e "${RED}✗ NO CORRIENDO${NC}"
    echo "  Iniciar: ollama serve"
fi

# ============================================================================
# RESUMEN
# ============================================================================
echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"

# Contar servicios activos
SERVICES_UP=0
SERVICES_TOTAL=5

pgrep redis-server > /dev/null && ((SERVICES_UP++))
pgrep -f "celery.*high_priority" > /dev/null && ((SERVICES_UP++))
pgrep -f "celery.*worker.*default" > /dev/null && ((SERVICES_UP++))
pgrep -f "manage.py runserver" > /dev/null && ((SERVICES_UP++))
pgrep ollama > /dev/null && ((SERVICES_UP++))

echo -e "Servicios activos: ${GREEN}$SERVICES_UP${NC}/$SERVICES_TOTAL"

if [ $SERVICES_UP -eq $SERVICES_TOTAL ]; then
    echo -e "\n${GREEN}✓ TODOS LOS SERVICIOS ESTÁN CORRIENDO${NC}"
    echo -e "${GREEN}  Sistema listo para usar${NC}"
elif [ $SERVICES_UP -eq 0 ]; then
    echo -e "\n${RED}✗ NINGÚN SERVICIO ESTÁ CORRIENDO${NC}"
    echo -e "${YELLOW}  Ejecuta: ./start_all.sh${NC}"
else
    echo -e "\n${YELLOW}⚠ ALGUNOS SERVICIOS NO ESTÁN CORRIENDO${NC}"
    echo -e "${YELLOW}  Ejecuta: ./start_all.sh${NC}"
fi

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# ============================================================================
# GPU STATUS (BONUS)
# ============================================================================
if command -v nvidia-smi &> /dev/null; then
    echo -e "\n${CYAN}━━━ GPU NVIDIA ━━━${NC}"
    nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader | \
        awk -F', ' '{printf "  GPU: %s\n  Memoria: %s / %s\n  Uso: %s\n", $1, $2, $3, $4}'
fi
