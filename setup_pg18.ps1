# setup_pg18.ps1
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "CONFIGURANDO POSTGRESQL 18 PARA REFINERYIQ" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Definir ruta completa de psql
$psqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"

# 1. Verificar que PostgreSQL está corriendo
Write-Host "`n1. Verificando servicio PostgreSQL..." -ForegroundColor Yellow
try {
    $service = Get-Service postgresql* -ErrorAction Stop
    if ($service.Status -eq "Running") {
        Write-Host "   ✓ PostgreSQL está ejecutándose" -ForegroundColor Green
    } else {
        Write-Host "   ✗ PostgreSQL no está corriendo" -ForegroundColor Red
        Start-Service $service.Name
        Write-Host "   ✓ PostgreSQL iniciado" -ForegroundColor Green
    }
} catch {
    Write-Host "   ✗ No se encontró el servicio PostgreSQL" -ForegroundColor Red
    exit 1
}

# 2. Crear base de datos si no existe
Write-Host "`n2. Creando base de datos 'refineryiq'..." -ForegroundColor Yellow
try {
    & $psqlPath -U postgres -c "SELECT 1 FROM pg_database WHERE datname = 'refineryiq';" 2>$null | Out-Null
    
    $dbExists = $LASTEXITCODE
    if ($dbExists -eq 0) {
        Write-Host "   ✓ Base de datos ya existe" -ForegroundColor Green
    } else {
        & $psqlPath -U postgres -c "CREATE DATABASE refineryiq;"
        Write-Host "   ✓ Base de datos creada" -ForegroundColor Green
    }
} catch {
    Write-Host "   ✗ Error al verificar/crear base de datos" -ForegroundColor Red
}

# 3. Ejecutar script de inicialización
Write-Host "`n3. Ejecutando script de inicialización..." -ForegroundColor Yellow
if (Test-Path "database\init\01-init.sql") {
    try {
        & $psqlPath -U postgres -d refineryiq -f database\init\01-init.sql 2>$null
        Write-Host "   ✓ Script ejecutado exitosamente" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠ Error ejecutando script (puede que ya esté ejecutado)" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ✗ No se encontró database\init\01-init.sql" -ForegroundColor Red
}

# 4. Configurar backend
Write-Host "`n4. Configurando backend..." -ForegroundColor Yellow
cd backend

# Crear archivo .env
$envContent = @"
DATABASE_URL=postgresql://postgres:307676@localhost:5432/refineryiq
SECRET_KEY=refineryiq_secret_key_2024
"@
Set-Content -Path .env -Value $envContent
Write-Host "   ✓ Archivo .env creado" -ForegroundColor Green

# 5. Crear entorno virtual si no existe
if (!(Test-Path "venv")) {
    python -m venv venv
    Write-Host "   ✓ Entorno virtual creado" -ForegroundColor Green
}

# Activar entorno virtual e instalar dependencias
Write-Host "`n5. Instalando dependencias Python..." -ForegroundColor Yellow
.\venv\Scripts\Activate
pip install fastapi uvicorn asyncpg pydantic python-dotenv aiohttp numpy
Write-Host "   ✓ Dependencias instaladas" -ForegroundColor Green

# 6. Verificar conexión
Write-Host "`n6. Verificando conexión a la base de datos..." -ForegroundColor Yellow
try {
    # Crear un script de prueba
    $testScript = @"
import asyncio
import asyncpg

async def test_db():
    try:
        conn = await asyncpg.connect(
            user='postgres',
            password='307676',
            host='localhost',
            port=5432,
            database='refineryiq'
        )
        print('✓ Conexión exitosa a PostgreSQL 18')
        await conn.close()
        return True
    except Exception as e:
        print(f'✗ Error de conexión: {e}')
        return False

asyncio.run(test_db())
"@
    
    Set-Content -Path "test_db.py" -Value $testScript
    python test_db.py
    Remove-Item -Path "test_db.py" -Force
} catch {
    Write-Host "   ✗ Error en la verificación" -ForegroundColor Red
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "CONFIGURACIÓN COMPLETADA" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "`nInformación:" -ForegroundColor Yellow
Write-Host "• PostgreSQL 18 en: C:\Program Files\PostgreSQL\18" -ForegroundColor White
Write-Host "• Contraseña: 307676" -ForegroundColor White
Write-Host "• Base de datos: refineryiq" -ForegroundColor White
Write-Host "• Puerto: 5432" -ForegroundColor White
Write-Host "`nPara agregar psql al PATH permanentemente:" -ForegroundColor Yellow
Write-Host "1. Abre PowerShell como Administrador" -ForegroundColor White
Write-Host "2. Ejecuta: [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';C:\Program Files\PostgreSQL\18\bin', 'Machine')" -ForegroundColor Gray
Write-Host "3. Reinicia PowerShell" -ForegroundColor White