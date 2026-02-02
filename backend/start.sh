#!/bin/bash
# start.sh - Script de inicio optimizado para Render

echo "========================================"
echo "🚀 REFINERYIQ BACKEND - INICIANDO"
echo "========================================"

# 1. Instalar dependencias
echo "📦 Instalando dependencias..."
pip install -r requirements.txt

# 2. Esperar 15 segundos para que PostgreSQL esté listo
echo "⏳ Esperando conexión a PostgreSQL (15 segundos)..."
sleep 15

# 3. Ejecutar la aplicación con el puerto dinámico de Render
echo "🌐 Iniciando servidor en puerto $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1