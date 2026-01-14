#!/bin/bash

# 🔄 Script para reiniciar todos los servicios
# Uso: ./restart.sh

# Colores
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🔄 Reiniciando Backend - Poder Judicial Docs            ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$BACKEND_DIR"

# Detener servicios
echo -e "\n⏸️  Deteniendo servicios..."
./stop_all.sh

# Esperar 3 segundos
echo -e "\n⏳ Esperando 3 segundos..."
sleep 3

# Iniciar servicios
echo -e "\n▶️  Iniciando servicios..."
./start_all.sh
