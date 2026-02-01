@echo off
echo ==========================================
echo   REFINERYIQ - PostgreSQL 18
echo ==========================================

REM Configurar PATH temporalmente
set PATH=%PATH%;C:\Program Files\PostgreSQL\18\bin

REM 0. Verificar e instalar dependencias del frontend
echo Verificando dependencias del frontend...
cd /d C:\Users\Carlod\Desktop\refineryiq-system\frontend
if not exist "node_modules" (
    echo Instalando dependencias Node.js...
    call npm install
) else (
    echo Dependencias ya instaladas.
)

REM 1. Iniciar Backend
echo Iniciando Backend...
start "RefineryIQ Backend" cmd /k "cd /d C:\Users\Carlod\Desktop\refineryiq-system\backend && call venv\Scripts\activate && python main.py"

REM Esperar 7 segundos para que el backend inicie completamente
timeout /t 7 /nobreak >nul

REM 2. Iniciar Frontend
echo Iniciando Frontend...
start "RefineryIQ Frontend" cmd /k "cd /d C:\Users\Carlod\Desktop\refineryiq-system\frontend && npm start"

REM Esperar 5 segundos
timeout /t 5 /nobreak >nul

REM 3. Iniciar Generador de Datos
echo Iniciando Generador de Datos...
start "RefineryIQ Data Gen" cmd /k "cd /d C:\Users\Carlod\Desktop\refineryiq-system\scripts\data_generator && python simple_generator.py"

echo.
echo ==========================================
echo   SISTEMA INICIADO
echo ==========================================
echo PostgreSQL 18 - Contraseña: 307676
echo Dashboard: http://localhost:3000
echo API:      http://localhost:8000
echo.
echo Problemas conocidos y soluciones:
echo 1. Si el frontend no carga: Espera 1 minuto y actualiza F5
echo 2. Si hay errores de conexión: El backend puede estar reiniciando
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause >nul