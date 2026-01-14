#!/bin/bash

# 🛑 Script para detener todos los servicios del backend
# Uso: ./stop_all.sh

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🛑 Deteniendo Backend - Poder Judicial Docs              ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# ============================================================================
# 1. DJANGO
# ============================================================================
echo -e "\n${YELLOW}[1/4]${NC} Deteniendo Django..."

if pgrep -f "manage.py runserver" > /dev/null; then
    pkill -f "manage.py runserver"
    sleep 1
    if pgrep -f "manage.py runserver" > /dev/null; then
        echo -e "${RED}❌ Django no se detuvo, forzando...${NC}"
        pkill -9 -f "manage.py runserver"
    fi
    echo -e "${GREEN}✓${NC} Django detenido"
else
    echo -e "${YELLOW}⚠${NC}  Django no estaba corriendo"
fi

# ============================================================================
# 2. CELERY HIGH PRIORITY
# ============================================================================
echo -e "\n${YELLOW}[2/4]${NC} Deteniendo Celery high_priority..."

if pgrep -f "celery.*high_priority" > /dev/null; then
    pkill -f "celery.*high_priority"
    sleep 1
    if pgrep -f "celery.*high_priority" > /dev/null; then
        echo -e "${RED}❌ Celery high no se detuvo, forzando...${NC}"
        pkill -9 -f "celery.*high_priority"
    fi
    echo -e "${GREEN}✓${NC} Celery high_priority detenido"
else
    echo -e "${YELLOW}⚠${NC}  Celery high_priority no estaba corriendo"
fi

# ============================================================================
# 3. CELERY DEFAULT
# ============================================================================
echo -e "\n${YELLOW}[3/4]${NC} Deteniendo Celery default..."

if pgrep -f "celery.*worker.*default" > /dev/null; then
    pkill -f "celery.*worker.*default"
    sleep 1
    if pgrep -f "celery.*worker.*default" > /dev/null; then
        echo -e "${RED}❌ Celery default no se detuvo, forzando...${NC}"
        pkill -9 -f "celery.*worker.*default"
    fi
    echo -e "${GREEN}✓${NC} Celery default detenido"
else
    echo -e "${YELLOW}⚠${NC}  Celery default no estaba corriendo"
fi

# ============================================================================
# 4. REDIS (OPCIONAL - Descomentar si quieres detener Redis también)
# ============================================================================
echo -e "\n${YELLOW}[4/4]${NC} Redis..."

# Descomenta las siguientes líneas si quieres detener Redis también:
# if pgrep redis-server > /dev/null; then
#     redis-cli shutdown
#     echo -e "${GREEN}✓${NC} Redis detenido"
# else
#     echo -e "${YELLOW}⚠${NC}  Redis no estaba corriendo"
# fi

echo -e "${BLUE}⚠${NC}  Redis sigue corriendo (detener manualmente: redis-cli shutdown)"

echo -e "\n${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✓ Todos los servicios detenidos                          ${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"

# Verificar que todo esté detenido
sleep 1
echo -e "\nVerificando procesos restantes..."
REMAINING=$(ps aux | grep -E "celery|manage.py runserver" | grep -v grep | wc -l)

if [ $REMAINING -gt 0 ]; then
    echo -e "${RED}⚠ Advertencia: Aún hay $REMAINING proceso(s) corriendo:${NC}"
    ps aux | grep -E "celery|manage.py runserver" | grep -v grep
    echo -e "\nPara forzar detención: ${YELLOW}pkill -9 -f 'celery|manage.py'${NC}"
else
    echo -e "${GREEN}✓ No hay procesos del backend corriendo${NC}"
fi
