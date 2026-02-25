import os
import sys
import time
import json
import random
import asyncio
import logging
import threading
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

# --- LIBRERÍAS DE SERVIDOR (FASTAPI) ---
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Body, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

# --- LIBRERÍAS DE BASE DE DATOS (SQLALCHEMY + ASYNCPG) ---
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError, OperationalError

# --- LIBRERÍAS DE TAREAS Y ML ---
from apscheduler.schedulers.asyncio import AsyncIOScheduler
try:
    from ml_optimization import optimizer
    ML_OPTIMIZER_AVAILABLE = True
except ImportError:
    print("⚠️ Advertencia: No se encontró ml_optimization.py")
    ML_OPTIMIZER_AVAILABLE = False

# --- AI CORE: Motor de IA Tier-1 ---
try:
    from ai_core.routes import router as ai_router, engine as ai_engine
    AI_CORE_AVAILABLE = True
    print("✅ AI Core v2.0 cargado correctamente")
except ImportError as e:
    AI_CORE_AVAILABLE = False
    ai_engine = None
    print(f"⚠️ AI Core no disponible: {e}")
# ==============================================================================
# 1. CONFIGURACIÓN PROFESIONAL DE LOGGING Y ENTORNO
# ==============================================================================

# Configuración de logs detallada para depuración en nube
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("RefineryIQ_Core")

# Añadir directorio actual al path para asegurar importaciones locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# LÓGICA DE CONEXIÓN DE BASE DE DATOS
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:307676@localhost:5432/refineryiq")

# Fix crítico para SQLAlchemy: Render da URLs con 'postgres://' pero SQLAlchemy 1.4+ exige 'postgresql://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

logger.info(f"🔌 Entorno detectado: {'NUBE (Render)' if 'onrender' in str(DATABASE_URL) else 'LOCAL'}")

# ==============================================================================
# 2. DEFINICIÓN DE MODELOS DE DATOS (PYDANTIC SCHEMAS)
# ==============================================================================
# ==============================================================================
# FUNCIÓN AUXILIAR: GENERACIÓN DE DATOS INICIALES DE KPIs
# ==============================================================================

async def generate_initial_kpis(conn):
    """Genera datos iniciales de KPIs si la base de datos está vacía."""
    from datetime import datetime, timedelta
    import random
    
    logger.info("📊 Generando datos iniciales de KPIs...")
    
    try:
        # Verificar si ya hay datos
        count = await conn.fetchval("SELECT COUNT(*) FROM kpis")
        if count > 10:
            logger.info(f"✅ Ya existen {count} registros de KPIs, omitiendo generación inicial.")
            return
        
        # Generar datos de las últimas 24 horas
        now = datetime.now()
        units = ["CDU-101", "FCC-201", "HT-305", "ALK-400"]
        
        # Generar 24 puntos de datos (uno por hora)
        for i in range(24):
            timestamp = now - timedelta(hours=i)
            
            for unit_id in units:
                # Valores realistas con cierta variación
                energy_efficiency = random.uniform(85.0, 97.0)
                throughput = random.uniform(10000, 15000)
                quality_score = random.uniform(98.5, 99.9)
                maintenance_score = random.uniform(90.0, 99.0)
                
                await conn.execute("""
                    INSERT INTO kpis (timestamp, unit_id, energy_efficiency, throughput, quality_score, maintenance_score)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, timestamp, unit_id, energy_efficiency, throughput, quality_score, maintenance_score)
        
        logger.info(f"✅ Generados {24 * len(units)} registros iniciales de KPIs.")
        
    except Exception as e:
        logger.error(f"❌ Error generando datos iniciales de KPIs: {e}")
class UserLogin(BaseModel):
    """Esquema para recepción de credenciales de login."""
    username: str
    password: str

class TokenResponse(BaseModel):
    """Esquema de respuesta de autenticación exitosa."""
    token: str
    user: str
    role: str
    expires_in: int = 3600

class KPIItem(BaseModel):
    """Esquema para datos de Key Performance Indicators."""
    unit_id: str
    efficiency: float
    throughput: float
    quality: float
    status: str
    last_updated: str

class TankItem(BaseModel):
    """Esquema para visualización de tanques."""
    id: int
    name: str
    product: str
    capacity: float
    current_level: float
    status: str

class InventoryItem(BaseModel):
    """Esquema para items de inventario."""
    item: str
    sku: str
    quantity: float
    unit: str
    status: str

class EquipmentItem(BaseModel):
    """Esquema complejo para activos con sensores anidados."""
    equipment_id: str
    equipment_name: str
    equipment_type: str
    status: str
    unit_id: str
    unit_name: Optional[str] = "N/A"
    sensors: List[Dict[str, Any]] = []

class AlertItem(BaseModel):
    """Esquema para alertas del sistema."""
    id: int
    time: str
    unit_id: str
    unit_name: str
    message: str
    severity: str
    acknowledged: bool

class DBStatsResponse(BaseModel):
    """Esquema para estadísticas de la base de datos."""
    total_process_records: int
    total_alerts: int
    total_units: int
    total_equipment: int
    total_tags: int
    database_normalized: bool
    last_updated: str

class EquipmentResponse(BaseModel):
    """Response model para equipos."""
    equipment_id: str
    equipment_name: str
    equipment_type: str
    status: str
    unit_id: str
    unit_name: Optional[str] = None
    sensors: List[Dict[str, Any]] = []
# ... después del último modelo existente ...

class InventoryUpdate(BaseModel):
    """Esquema para actualizar un ítem del inventario."""
    item: Optional[str] = None
    sku: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None

class InventoryCreate(BaseModel):
    """Esquema para crear un nuevo ítem en el inventario."""
    item: str
    sku: str
    quantity: float
    unit: str
    status: str = "OK"
    location: str = "Almacén Central"

class OptimizationRequest(BaseModel):
    unit_id: str
    current_temperature: float
    current_pressure: float
    current_flow: float
# ==============================================================================
# 3. GESTIÓN DE BASE DE DATOS (CONEXIÓN Y MIGRACIÓN)
# ==============================================================================

# Motor Síncrono (SQLAlchemy) para operaciones DDL (Crear tablas)
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True, 
    pool_size=20, 
    max_overflow=30,
    connect_args={"connect_timeout": 15}
)

# Motor Asíncrono (AsyncPG) para operaciones de API (Alta velocidad)
async def get_db_conn():
    """Establece una conexión asíncrona de alto rendimiento."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"⚠️ Error Crítico conectando a DB Async: {e}")
        return None

def create_tables_if_not_exist():
    """
    Sistema de Auto-Migración 'Self-Healing'.
    Crea todas las tablas necesarias con la estructura CORRECTA V12.
    """
    try:
        with engine.connect() as conn:
            logger.info("🔧 [BOOT] Verificando esquema de Base de Datos...")
            
            # 1. USUARIOS
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY, 
                    username TEXT UNIQUE, 
                    hashed_password TEXT, 
                    full_name TEXT, 
                    role TEXT, 
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """))

            # 2. OPERACIONES
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS kpis (
                    id SERIAL PRIMARY KEY, 
                    timestamp TIMESTAMP, 
                    unit_id TEXT, 
                    energy_efficiency FLOAT, 
                    throughput FLOAT, 
                    quality_score FLOAT, 
                    maintenance_score FLOAT
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY, 
                    timestamp TIMESTAMP, 
                    unit_id TEXT, 
                    tag_id TEXT, 
                    value FLOAT, 
                    threshold FLOAT, 
                    severity TEXT, 
                    message TEXT, 
                    acknowledged BOOLEAN DEFAULT FALSE
                );
            """))
            
            # 3. LOGÍSTICA
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tanks (
                    id SERIAL PRIMARY KEY, 
                    name TEXT UNIQUE, 
                    product TEXT, 
                    capacity FLOAT, 
                    current_level FLOAT, 
                    status TEXT, 
                    last_updated TIMESTAMP DEFAULT NOW()
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY, 
                    item TEXT, 
                    sku TEXT UNIQUE, 
                    quantity FLOAT, 
                    unit TEXT, 
                    status TEXT, 
                    location TEXT, 
                    last_updated TIMESTAMP DEFAULT NOW()
                );
            """))
            
            # 4. NORMALIZACIÓN
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS process_units (
                    unit_id TEXT PRIMARY KEY, 
                    name TEXT, 
                    type TEXT, 
                    description TEXT,
                    capacity FLOAT,
                    unit_status TEXT DEFAULT 'ACTIVE'
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS process_tags (
                    tag_id TEXT PRIMARY KEY, 
                    tag_name TEXT, 
                    unit_id TEXT, 
                    engineering_units TEXT, 
                    min_val FLOAT, 
                    max_val FLOAT, 
                    description TEXT,
                    tag_type TEXT DEFAULT 'GENERAL',
                    is_critical BOOLEAN DEFAULT FALSE
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS equipment (
                    equipment_id TEXT PRIMARY KEY, 
                    equipment_name TEXT, 
                    equipment_type TEXT, 
                    unit_id TEXT, 
                    status TEXT, 
                    manufacturer TEXT,
                    installation_date TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS process_data (
                    id SERIAL PRIMARY KEY, 
                    timestamp TIMESTAMP, 
                    unit_id TEXT, 
                    tag_id TEXT, 
                    value FLOAT, 
                    quality INTEGER
                );
            """))
            
            # 5. ML & ENERGY
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS maintenance_predictions (
                    id SERIAL PRIMARY KEY, 
                    equipment_id TEXT, 
                    failure_probability FLOAT, 
                    prediction TEXT, 
                    recommendation TEXT, 
                    timestamp TIMESTAMP, 
                    confidence FLOAT
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS energy_analysis (
                    id SERIAL PRIMARY KEY, 
                    unit_id TEXT, 
                    efficiency_score FLOAT, 
                    consumption_kwh FLOAT, 
                    savings_potential FLOAT, 
                    recommendation TEXT, 
                    analysis_date TIMESTAMP, 
                    status TEXT
                );
            """))
            
            conn.commit()
            logger.info("✅ [BOOT] Esquema de Base de Datos verificado.")
            
    except Exception as e:
        logger.critical(f"❌ [BOOT] Error crítico en migración inicial: {e}")
# ==============================================================================
# 4. SISTEMA DE RESPALDO EN MEMORIA (FAIL-SAFE DATA)
# ==============================================================================

def get_mock_kpis():
    """Datos simulados para KPIs si falla la DB."""
    return [
        {"unit_id": "CDU-101", "efficiency": 92.5, "throughput": 12500, "quality": 99.8, "status": "normal", "last_updated": datetime.now().isoformat()},
        {"unit_id": "FCC-201", "efficiency": 88.2, "throughput": 15200, "quality": 98.5, "status": "warning", "last_updated": datetime.now().isoformat()},
        {"unit_id": "HT-305",  "efficiency": 95.0, "throughput": 8500,  "quality": 99.9, "status": "normal", "last_updated": datetime.now().isoformat()}
    ]

def get_mock_supplies():
    """Datos simulados para Suministros si falla la DB."""
    return {
        "tanks": [
            {"id": 1, "name": "TK-101 (Modo Seguro)", "product": "Crudo Maya", "capacity": 50000, "current_level": 25000, "status": "STABLE"},
            {"id": 2, "name": "TK-102 (Modo Seguro)", "product": "Gasolina", "capacity": 30000, "current_level": 15000, "status": "FILLING"}
        ],
        "inventory": [
            {"item": "Catalizador (Backup)", "sku": "CAT-SAFE", "quantity": 1000, "unit": "kg", "status": "OK"},
            {"item": "Aditivo (Backup)", "sku": "ADD-SAFE", "quantity": 500, "unit": "L", "status": "OK"}
        ]
    }

def get_mock_alerts():
    """Datos simulados para Alertas si falla la DB."""
    return [
        {"id": 1, "time": datetime.now().isoformat(), "unit_id": "SYS", "unit_name": "Sistema", "message": "Modo de Recuperación Activo", "severity": "WARNING", "acknowledged": False}
    ]

# ==============================================================================
# 5. GESTIÓN DE TAREAS EN SEGUNDO PLANO (SIMULACIÓN V12)
# ==============================================================================

# Intentamos importar el generador avanzado
try:
    from auto_generator import run_simulation_cycle
    SIMULATOR_AVAILABLE = True
    logger.info("✅ Generador V8 detectado.")
except ImportError as e:
    SIMULATOR_AVAILABLE = False
    logger.warning(f"⚠️ Generador no encontrado: {e}. Modo pasivo.")
    
    def run_simulation_cycle():
        logger.info("Simulador no disponible - modo dummy")

# Módulos IA — Usa AI Core si está disponible, sino fallback a Dummy
class DummyML:
    async def get_recent_predictions(self, *args, **kwargs): 
        return []
    async def get_recent_analysis(self, *args, **kwargs): 
        return []

if AI_CORE_AVAILABLE and ai_engine is not None:
    pm_system = ai_engine  # PredictiveMaintenanceEngine tiene stubs compatibles
    logger.info("🧠 AI Core Engine asignado como sistema de mantenimiento predictivo")
else:
    pm_system = DummyML()
    logger.warning("⚠️ Usando DummyML como fallback para mantenimiento predictivo")
energy_system = DummyML()

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=5)
def scheduled_job():
    """Ejecuta el ciclo de simulación cada 5 minutos."""
    if SIMULATOR_AVAILABLE:
        try:
            logger.info("⏰ [SCHEDULER] Ejecutando simulación programada...")
            run_simulation_cycle()
        except Exception as e:
            logger.error(f"Error en tarea programada: {e}")
async def train_ml_models():
    """Entrena los modelos de Machine Learning con los datos más recientes."""
    if ML_OPTIMIZER_AVAILABLE:
        try:
            logger.info("🧠 Ejecutando entrenamiento programado de modelos ML...")
            result = await optimizer.train_optimization_model("CDU-101")
            logger.info(f"✅ Entrenamiento completado: {result}")
        except Exception as e:
            logger.error(f"❌ Error en entrenamiento ML: {e}")
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("==================================================")
    logger.info("🚀 REFINERYIQ SYSTEM V13.0 AI-POWERED - INICIANDO")
    logger.info("==================================================")
    
    # 1. Crear tablas
    create_tables_if_not_exist()
    
    # 2. Inicializar AI Core Engine
    if AI_CORE_AVAILABLE and ai_engine is not None:
        try:
            await ai_engine.initialize()
            logger.info("🧠 AI Core Engine inicializado correctamente")
        except Exception as e:
            logger.warning(f"⚠️ AI Core Engine init parcial: {e}")
    
    # 3. Programar tareas (sin iniciar aún)
    if SIMULATOR_AVAILABLE:
        # Tareas del simulador (ej. la que ya tenías)
        scheduler.add_job(scheduled_job, 'interval', minutes=5)
        # Simulación inicial en hilo (esto no es del scheduler, es un thread aparte)
        def delayed_start():
            time.sleep(15)
            run_simulation_cycle()
        threading.Thread(target=delayed_start, daemon=True).start()
    
    if ML_OPTIMIZER_AVAILABLE:
        scheduler.add_job(train_ml_models, 'interval', hours=1, id='train_ml_hourly')
        scheduler.add_job(train_ml_models, 'date', 
                          run_date=datetime.now() + timedelta(seconds=60), 
                          id='train_ml_initial')
    
    # 4. Iniciar el scheduler (solo si hay trabajos)
    if scheduler.get_jobs():
        scheduler.start()
        logger.info("🤖 Scheduler iniciado.")
    
    yield
    
    # Apagado
    logger.info("🛑 Deteniendo servicios...")
    if scheduler.running:
        scheduler.shutdown()

# ==============================================================================
# 6. API PRINCIPAL (FASTAPI APP)
# ==============================================================================

app = FastAPI(
    title="RefineryIQ Enterprise API",
    description="Backend industrial Full-Stack V13.0 AI-Powered. Gestión integral de refinería con IA predictiva Tier-1.",
    version="13.0.0",
    lifespan=lifespan
)

# --- Montar Router AI Core ---
if AI_CORE_AVAILABLE:
    app.include_router(ai_router)
    logger.info("🧠 AI Core Router montado en /api/ai")

# Configuración CORS EXTREMADAMENTE PERMISIVA para Render
# IMPORTANTE: "*" NO funciona con allow_credentials=True — el browser lo rechaza.
origins = [
    # Desarrollo local
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8000",
    
    # Render URLs
    "https://refineryiq-frontend.onrender.com",
    "https://refineryiq-system.onrender.com",
    
    # Dominios personalizados
    "https://refineryiq.dev",
    "https://www.refineryiq.dev",
    "https://api.refineryiq.dev",
    "https://system.refineryiq.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.refineryiq\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
# Middleware de Logging y Manejo de Errores Global
@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"🔥 UNHANDLED ERROR en {request.url.path}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error (Recovered)", "error_msg": str(e)},
            headers={"Access-Control-Allow-Origin": "*"}
        )

# ==============================================================================
# 7. ENDPOINTS: AUTHENTICATION
# ==============================================================================

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(creds: UserLogin):
    """Endpoint de login con validación de DB y Backdoor admin."""
    if creds.username == "admin" and creds.password == "admin123":
        return {"token": "master-token", "user": "Admin", "role": "admin"}
    
    conn = await get_db_conn()
    if conn:
        try:
            user = await conn.fetchrow("SELECT * FROM users WHERE username = $1", creds.username)
            if user and user['hashed_password'] == creds.password:
                return {"token": "db-token", "user": user['full_name'], "role": user['role']}
        except Exception as e:
            logger.error(f"Auth DB Error: {e}")
        finally: 
            await conn.close()
            
    raise HTTPException(status_code=401, detail="Credenciales incorrectas")

# ==============================================================================
# 8. ENDPOINTS: DASHBOARD & KPIS
# ==============================================================================

@app.get("/api/kpis", response_model=List[KPIItem])
async def get_kpis():
    """Devuelve los KPIs más recientes. Con Fail-safe."""
    conn = await get_db_conn()
    if not conn: 
        return get_mock_kpis()
    
    try:
        rows = await conn.fetch("SELECT DISTINCT ON (unit_id) * FROM kpis ORDER BY unit_id, timestamp DESC")
        if not rows: 
            return get_mock_kpis()
        
        return [{
            "unit_id": r['unit_id'], 
            "efficiency": r['energy_efficiency'],
            "throughput": r['throughput'], 
            "quality": r.get('quality_score', 99.0),
            "status": "normal" if r['energy_efficiency'] > 90 else "warning",
            "last_updated": r['timestamp'].isoformat()
        } for r in rows]
    except Exception as e:
        logger.error(f"KPI Fetch Error: {e}")
        return get_mock_kpis()
    finally: 
        await conn.close()

@app.get("/api/dashboard/history")
async def get_dashboard_history():
    """Devuelve historial 24h para gráficos."""
    conn = await get_db_conn()
    if not conn: 
        return []
    
    try:
        # Verificar si hay datos, si no, generar algunos
        count = await conn.fetchval("SELECT COUNT(*) FROM kpis WHERE timestamp >= NOW() - INTERVAL '24 HOURS'")
        
        if count < 10:
            logger.info("📊 Generando datos históricos iniciales para dashboard...")
            await generate_initial_kpis(conn)
        
        rows = await conn.fetch("""
            SELECT 
                to_char(date_trunc('hour', timestamp), 'HH24:00') as time_label,
                ROUND(AVG(energy_efficiency)::numeric, 1) as efficiency,
                ROUND(AVG(throughput)::numeric, 0) as production
            FROM kpis 
            WHERE timestamp >= NOW() - INTERVAL '24 HOURS'
            GROUP BY 1 
            ORDER BY 1 ASC
        """)
        
        # Si no hay resultados, crear algunos datos de ejemplo
        if not rows:
            logger.warning("⚠️ No hay datos históricos, generando datos de ejemplo...")
            example_data = []
            now = datetime.now()
            for i in range(24, 0, -1):
                hour = (now - timedelta(hours=i)).strftime('%H:00')
                production = 12000 + random.randint(-1000, 1000)
                example_data.append({
                    "time_label": hour,
                    "efficiency": random.uniform(85, 95),
                    "production": production
                })
            return example_data
        
        logger.info(f"📈 Historial obtenido: {len(rows)} puntos de datos")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"History Fetch Error: {e}")
        return []
    finally: 
        await conn.close()
@app.get("/api/stats/advanced")
async def get_advanced_stats():
    """Estadísticas avanzadas para OEE y Radar Chart."""
    conn = await get_db_conn()
    
    # Primero, verificar si hay datos
    try:
        if conn:
            # Generar datos iniciales si no existen
            count_result = await conn.fetchval("SELECT COUNT(*) FROM kpis WHERE timestamp > NOW() - INTERVAL '24 hours'")
            if not count_result or count_result < 5:
                logger.info("📊 Generando datos de KPIs iniciales para estadísticas...")
                await generate_initial_kpis(conn)
    except Exception as e:
        logger.error(f"Error verificando datos: {e}")
    
    # Valores por defecto que se usarán si hay error
    default = {
        "oee": {
            "score": 87.5, 
            "quality": 99.2, 
            "availability": 96.8, 
            "performance": 89.3
        },
        "stability": {
            "index": 88.7, 
            "trend": "stable"
        },
        "financial": {
            "daily_loss_usd": 4350
        }
    }
    
    if not conn: 
        return default
    
    try:
        # 1. Obtener KPIs de las últimas 24 horas
        kpis_query = """
            SELECT 
                AVG(energy_efficiency) as avg_efficiency,
                AVG(throughput) as avg_throughput,
                AVG(quality_score) as avg_quality,
                COUNT(*) as record_count
            FROM kpis 
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """
        
        kpis_result = await conn.fetchrow(kpis_query)
        
        # Si no hay datos, usar los valores por defecto
        if not kpis_result or kpis_result['record_count'] == 0:
            logger.warning("⚠️ No se encontraron datos de KPIs, usando valores por defecto")
            return default
        
        avg_efficiency = float(kpis_result['avg_efficiency'] or 88.0)
        avg_throughput = float(kpis_result['avg_throughput'] or 12000)
        avg_quality = float(kpis_result['avg_quality'] or 99.0)
        record_count = int(kpis_result['record_count'] or 1)
        
        logger.info(f"📈 Datos reales encontrados: {record_count} registros, eficiencia: {avg_efficiency:.2f}%")
        
        # 2. Obtener alertas activas para calcular estabilidad
        alerts_query = """
            SELECT COUNT(*) as active_alerts
            FROM alerts 
            WHERE acknowledged = FALSE 
            AND timestamp > NOW() - INTERVAL '24 hours'
        """
        
        alerts_result = await conn.fetchrow(alerts_query)
        active_alerts = int(alerts_result['active_alerts'] or 0) if alerts_result else 0
        
        # 3. Calcular OEE (Overall Equipment Effectiveness)
        # OEE = Disponibilidad × Rendimiento × Calidad
        availability = max(70, min(100, 100 - (active_alerts * 2)))  # Cada alerta reduce disponibilidad
        performance = avg_efficiency
        quality = avg_quality
        
        oee_score = round((availability/100) * (performance/100) * (quality/100) * 100, 1)
        
        # 4. Calcular estabilidad
        stability_score = max(0, min(100, 100 - (active_alerts * 3)))
        
        # 5. Calcular impacto financiero
        efficiency_factor = max(0, 100 - avg_efficiency)
        base_loss = efficiency_factor * 50
        alerts_penalty = active_alerts * 100
        throughput_penalty = 0
        
        if avg_throughput < 11500:
            throughput_penalty = (11500 - avg_throughput) * 0.1
            
        daily_loss = round(base_loss + alerts_penalty + throughput_penalty, 0)
        
        # 6. Determinar tendencia
        if active_alerts > 5:
            trend = "deteriorating"
        elif active_alerts > 2:
            trend = "stable"
        else:
            trend = "improving"
        
        logger.info(f"📊 Estadísticas calculadas: OEE={oee_score}%, Estabilidad={stability_score}%, Pérdida=${daily_loss}")
            
        return {
            "oee": {
                "score": oee_score,
                "quality": round(quality, 1),
                "availability": round(availability, 1),
                "performance": round(performance, 1)
            },
            "stability": {
                "index": round(stability_score, 1),
                "trend": trend
            },
            "financial": {
                "daily_loss_usd": int(daily_loss)
            }
        }
        
    except Exception as e:
        logger.error(f"Advanced Stats Error: {e}")
        return default
    finally: 
        if conn:
            await conn.close()
# ==============================================================================
# 9. ENDPOINTS: SUPPLY & INVENTORY (BLINDAJE TOTAL)
# ==============================================================================

@app.get("/api/supplies/data")
async def get_supplies_data():
    """
    Recupera tanques e inventario. 
    Protegido contra columnas faltantes ('item', 'sku').
    """
    conn = await get_db_conn()
    if not conn: 
        return get_mock_supplies()
    
    try:
        # 1. Tanques
        tanks = []
        try:
            tanks_rows = await conn.fetch("SELECT * FROM tanks ORDER BY name")
            tanks = [dict(t) for t in tanks_rows]
        except Exception as e:
            logger.error(f"Tanks Fetch Error: {e}")
            tanks = get_mock_supplies()['tanks']

        # 2. Inventario (Crítico)
        inv = []
        try:
            inv_rows = await conn.fetch("SELECT * FROM inventory ORDER BY quantity ASC")
            for r in inv_rows:
                d = dict(r)
                # Validación manual: Si el diccionario tiene 'item', lo usamos
                if d.get('item'): 
                    inv.append(d)
        except Exception as e:
            logger.warning(f"⚠️ Error Inventario: {e}")
            inv = get_mock_supplies()['inventory'] 

        if not tanks: 
            tanks = get_mock_supplies()['tanks']
        if not inv: 
            inv = get_mock_supplies()['inventory']

        return {"tanks": tanks, "inventory": inv}
    
    except Exception as e:
        logger.error(f"❌ Error Supply: {e}")
        return get_mock_supplies()
    finally: 
        await conn.close()
@app.get("/api/inventory")
async def get_inventory():
    """Obtiene todo el inventario para el panel de administración."""
    conn = await get_db_conn()
    if not conn: 
        return []
    
    try:
        rows = await conn.fetch("""
            SELECT id, item, sku, quantity, unit, status, location, 
                   TO_CHAR(last_updated, 'YYYY-MM-DD HH24:MI:SS') as last_updated
            FROM inventory 
            ORDER BY id
        """)
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Inventory fetch error: {e}")
        return []
    finally: 
        await conn.close()
@app.post("/api/inventory")
async def create_inventory_item(item_data: InventoryCreate):
    """Crea un nuevo ítem en el inventario."""
    conn = await get_db_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        # Verificar si el SKU ya existe
        existing = await conn.fetchrow(
            "SELECT id FROM inventory WHERE sku = $1", 
            item_data.sku
        )
        
        if existing:
            raise HTTPException(status_code=400, detail="SKU already exists")
        
        # Insertar nuevo ítem
        result = await conn.fetchrow("""
            INSERT INTO inventory (item, sku, quantity, unit, status, location, last_updated)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            RETURNING id, item, sku, quantity, unit, status, location, last_updated
        """, 
            item_data.item, 
            item_data.sku, 
            item_data.quantity, 
            item_data.unit, 
            item_data.status, 
            item_data.location
        )
        
        return dict(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Inventory create error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()
@app.put("/api/inventory/{item_id}")
async def update_inventory_item(item_id: int, item_data: InventoryUpdate):
    """Actualiza un ítem del inventario."""
    conn = await get_db_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        # Construir la consulta de actualización dinámicamente
        update_fields = []
        values = []
        param_count = 1
        
        if item_data.item is not None:
            update_fields.append(f"item = ${param_count}")
            values.append(item_data.item)
            param_count += 1
        
        if item_data.sku is not None:
            update_fields.append(f"sku = ${param_count}")
            values.append(item_data.sku)
            param_count += 1
        
        if item_data.quantity is not None:
            update_fields.append(f"quantity = ${param_count}")
            values.append(item_data.quantity)
            param_count += 1
        
        if item_data.unit is not None:
            update_fields.append(f"unit = ${param_count}")
            values.append(item_data.unit)
            param_count += 1
        
        if item_data.status is not None:
            update_fields.append(f"status = ${param_count}")
            values.append(item_data.status)
            param_count += 1
        
        if item_data.location is not None:
            update_fields.append(f"location = ${param_count}")
            values.append(item_data.location)
            param_count += 1
        
        # Si no hay campos para actualizar, lanzar error
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Agregar actualización de timestamp
        update_fields.append("last_updated = NOW()")
        
        # Agregar el ID al final de los valores
        values.append(item_id)
        
        query = f"""
            UPDATE inventory 
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, item, sku, quantity, unit, status, location, last_updated
        """
        
        updated = await conn.fetchrow(query, *values)
        if updated is None:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return dict(updated)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Inventory update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()
@app.delete("/api/inventory/{item_id}")
async def delete_inventory_item(item_id: int):
    """Elimina un ítem del inventario."""
    conn = await get_db_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        # Verificar si el ítem existe
        existing = await conn.fetchrow(
            "SELECT id FROM inventory WHERE id = $1", 
            item_id
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Eliminar el ítem
        await conn.execute("DELETE FROM inventory WHERE id = $1", item_id)
        
        return {"status": "success", "message": f"Item {item_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Inventory delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()
@app.get("/api/inventory/{item_id}")
async def get_inventory_item(item_id: int):
    """Obtiene un ítem específico del inventario."""
    conn = await get_db_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        row = await conn.fetchrow("""
            SELECT id, item, sku, quantity, unit, status, location, 
                   TO_CHAR(last_updated, 'YYYY-MM-DD HH24:MI:SS') as last_updated
            FROM inventory 
            WHERE id = $1
        """, item_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()
# ==============================================================================
# 10. ENDPOINTS: ASSETS & SENSORS
# ==============================================================================

@app.get("/api/assets/overview", response_model=List[EquipmentResponse])
@app.get("/api/assets/overview", response_model=List[EquipmentResponse])
async def get_assets_overview():
    """Endpoint masivo: Equipos + Unidades + Sensores + Valores."""
    conn = await get_db_conn()
    if not conn: 
        return []
    
    try:
        query = """
            SELECT 
                e.equipment_id, 
                e.equipment_name, 
                e.equipment_type, 
                e.status, 
                e.unit_id, 
                pu.name as unit_name,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'tag_name', pt.tag_name, 
                            'value', pd.value, 
                            'units', pt.engineering_units
                        ) 
                    ) FILTER (WHERE pt.tag_id IS NOT NULL), 
                    '[]'
                ) as sensors
            FROM equipment e
            LEFT JOIN process_units pu ON e.unit_id = pu.unit_id
            LEFT JOIN process_tags pt ON pt.unit_id = e.unit_id 
            LEFT JOIN LATERAL (
                SELECT value 
                FROM process_data 
                WHERE tag_id = pt.tag_id 
                ORDER BY timestamp DESC 
                LIMIT 1
            ) pd ON true
            GROUP BY e.equipment_id, e.equipment_name, e.equipment_type, e.status, e.unit_id, pu.name
            ORDER BY e.unit_id, e.equipment_name
        """
        rows = await conn.fetch(query)
        results = []
        for row in rows:
            data = dict(row)
            if isinstance(data.get('sensors'), str):
                try:
                    data['sensors'] = json.loads(data['sensors'])
                except:
                    data['sensors'] = []
            elif data.get('sensors') is None:
                data['sensors'] = []
            results.append(data)
        return results
    except Exception as e:
        logger.error(f"Error assets: {e}")
        return []
    finally: 
        await conn.close()

# ==============================================================================
# 11. ENDPOINTS: ALERTS & MAINTENANCE
# ==============================================================================

@app.get("/api/alerts", response_model=List[AlertItem])
async def get_alerts(acknowledged: bool = False):
    conn = await get_db_conn()
    if not conn: 
        return get_mock_alerts()
    
    try:
        rows = await conn.fetch("""
            SELECT a.*, pu.name as unit_name FROM alerts a
            LEFT JOIN process_units pu ON a.unit_id = pu.unit_id
            WHERE acknowledged = $1 ORDER BY timestamp DESC LIMIT 20
        """, acknowledged)
        
        if not rows and not acknowledged: 
            return get_mock_alerts()
        
        return [{
            "id": r['id'], 
            "time": r['timestamp'].isoformat(),
            "unit_id": r['unit_id'], 
            "unit_name": r.get('unit_name', r['unit_id']) or "N/A",
            "message": r['message'], 
            "severity": r['severity'], 
            "acknowledged": r['acknowledged']
        } for r in rows]
    except Exception as e:
        logger.error(f"Alerts Fetch Error: {e}")
        return get_mock_alerts()
    finally: 
        await conn.close()

@app.get("/api/alerts/history")
async def get_alerts_history():
    conn = await get_db_conn()
    if not conn: 
        return []
    
    try:
        rows = await conn.fetch("""
            SELECT a.*, pu.name as unit_name, pt.tag_name FROM alerts a
            LEFT JOIN process_units pu ON a.unit_id = pu.unit_id
            LEFT JOIN process_tags pt ON a.tag_id = pt.tag_id
            ORDER BY timestamp DESC LIMIT 50
        """)
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Alerts History Error: {e}")
        return []
    finally: 
        await conn.close()

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    conn = await get_db_conn()
    if not conn: 
        raise HTTPException(500, "DB Error")
    
    try:
        await conn.execute("UPDATE alerts SET acknowledged = TRUE WHERE id = $1", alert_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(500, f"Error acknowledging alert: {e}")
    finally: 
        await conn.close()

@app.get("/api/maintenance/predictions")
async def get_maintenance_predictions():
    conn = await get_db_conn()
    
    try:
        if conn:
            rows = await conn.fetch("""
                SELECT mp.*, e.equipment_name FROM maintenance_predictions mp
                LEFT JOIN equipment e ON mp.equipment_id = e.equipment_id
                ORDER BY timestamp DESC LIMIT 10
            """)
            await conn.close()
            if rows: 
                return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Maintenance Predictions Error: {e}")
    
    # --- AI Core: predicciones en tiempo real ---
    if AI_CORE_AVAILABLE and ai_engine is not None:
        try:
            if not ai_engine._initialized:
                await ai_engine.initialize()
            
            default_equipment = [
                {"equipment_id": "PUMP-101", "equipment_type": "PUMP"},
                {"equipment_id": "PUMP-102", "equipment_type": "PUMP"},
                {"equipment_id": "COMP-201", "equipment_type": "COMPRESSOR"},
                {"equipment_id": "COMP-202", "equipment_type": "COMPRESSOR"},
                {"equipment_id": "VALVE-301", "equipment_type": "VALVE"},
                {"equipment_id": "HX-401", "equipment_type": "EXCHANGER"},
            ]
            
            results = await ai_engine.predict_batch(default_equipment)
            
            # Formatear para el frontend existente
            formatted = []
            eq_names = {
                "PUMP-101": "Bomba Centrífuga P-101",
                "PUMP-102": "Bomba de Alimentación P-102", 
                "COMP-201": "Compresor Gas C-201",
                "COMP-202": "Compresor Reciclo C-202",
                "VALVE-301": "Válvula Control V-301",
                "HX-401": "Intercambiador Calor E-401",
            }
            
            for r in results:
                rul = r.get("rul_hours")
                fp = r.get("failure_probability", 5.0) or 5.0
                
                if rul is not None and rul < 48:
                    prediction = "FALLO INMINENTE"
                elif rul is not None and rul < 168:
                    prediction = "MANTENIMIENTO REQUERIDO"
                elif r.get("is_anomaly"):
                    prediction = "ANOMALÍA DETECTADA"
                else:
                    prediction = "OPERACIÓN NORMAL"
                
                formatted.append({
                    "equipment_id": r["equipment_id"],
                    "equipment_name": eq_names.get(r["equipment_id"], r["equipment_id"]),
                    "equipment_type": r["equipment_type"],
                    "failure_probability": round(fp, 1),
                    "rul_hours": rul,
                    "anomaly_score": r.get("anomaly_score"),
                    "is_anomaly": r.get("is_anomaly", False),
                    "recommendation": r.get("recommendation", ""),
                    "narrative": r.get("narrative"),
                    "confidence": r.get("confidence", 75.0) or 75.0,
                    "prediction": prediction,
                    "model_source": r.get("model_source", "ai_core_v2"),
                    "shap_explanation": r.get("shap_explanation"),
                    "timestamp": r.get("timestamp"),
                })
            
            return formatted
        except Exception as e:
            logger.error(f"AI Core prediction error: {e}")
    
    return await pm_system.get_recent_predictions(None)

@app.get("/api/energy/analysis")
async def get_energy_analysis():
    conn = await get_db_conn()
    
    try:
        if conn:
            rows = await conn.fetch("""
                SELECT ea.*, pu.name as unit_name FROM energy_analysis ea
                LEFT JOIN process_units pu ON ea.unit_id = pu.unit_id
                ORDER BY analysis_date DESC LIMIT 5
            """)
            await conn.close()
            if rows: 
                return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Energy Analysis Error: {e}")
    
    return await energy_system.get_recent_analysis(None)
# ==============================================================================
# ==============================================================================
# ==============================================================================
# ==============================================================================
# ==============================================================================
# ==============================================================================

# ==============================================================================
@app.post("/api/fix-inventory-table")
async def fix_inventory_table():
    """Endpoint temporal para arreglar la tabla inventory si falta la columna 'item'."""
    conn = await get_db_conn()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        # Agregar columna 'item' si no existe
        await conn.execute("""
            ALTER TABLE inventory 
            ADD COLUMN IF NOT EXISTS item TEXT;
        """)
        
        # Si hay registros sin 'item', actualízalos con un valor por defecto
        await conn.execute("""
            UPDATE inventory 
            SET item = 'Ítem sin nombre' 
            WHERE item IS NULL OR item = '';
        """)
        
        return {"status": "success", "message": "Inventory table fixed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()
# ==============================================================================
# 12. ENDPOINTS: NORMALIZACIÓN Y DB VIEWER
# ==============================================================================

@app.get("/api/normalized/tags")
async def get_norm_tags():
    conn = await get_db_conn()
    if not conn: 
        return []
    
    try:
        rows = await conn.fetch("""
            SELECT pt.*, pu.name as unit_name FROM process_tags pt 
            LEFT JOIN process_units pu ON pt.unit_id = pu.unit_id ORDER BY pt.tag_id
        """)
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Norm Tags Error: {e}")
        return []
    finally: 
        await conn.close()

@app.get("/api/normalized/stats", response_model=DBStatsResponse)
async def get_normalized_stats():
    conn = await get_db_conn()
    empty = {
        "total_process_records": 0, 
        "total_alerts": 0, 
        "total_units": 0, 
        "total_equipment": 0, 
        "total_tags": 0, 
        "database_normalized": False, 
        "last_updated": datetime.now().isoformat()
    }
    
    if not conn: 
        return empty
    
    try:
        return {
            "total_process_records": await conn.fetchval("SELECT COUNT(*) FROM kpis") or 0,
            "total_alerts": await conn.fetchval("SELECT COUNT(*) FROM alerts WHERE acknowledged = FALSE") or 0,
            "total_units": await conn.fetchval("SELECT COUNT(*) FROM process_units") or 0,
            "total_equipment": await conn.fetchval("SELECT COUNT(*) FROM equipment") or 0,
            "total_tags": await conn.fetchval("SELECT COUNT(*) FROM process_tags") or 0,
            "database_normalized": True,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Norm Stats Error: {e}")
        return empty
    finally: 
        await conn.close()

@app.get("/api/normalized/process-data/enriched")
async def get_norm_data_enriched(limit: int = 50):
    conn = await get_db_conn()
    if not conn: 
        return []
    
    try:
        rows = await conn.fetch("""
            SELECT pd.timestamp, pd.value, pd.quality, 
                   pd.unit_id, pd.tag_id,
                   pu.name as unit_name, 
                   pt.tag_name, 
                   pt.engineering_units
            FROM process_data pd
            JOIN process_tags pt ON pd.tag_id = pt.tag_id
            JOIN process_units pu ON pd.unit_id = pu.unit_id
            ORDER BY pd.timestamp DESC LIMIT $1
        """, limit)
        
        return [{
            "timestamp": r['timestamp'].isoformat(),
            "value": r['value'],
            "quality": r['quality'],
            "unit_id": r['unit_id'],
            "tag_id": r['tag_id'],
            "unit_name": r['unit_name'],
            "tag_name": r['tag_name'],
            "engineering_units": r['engineering_units']
        } for r in rows]
    except Exception as e:
        logger.error(f"Norm Data Enriched Error: {e}")
        return []
    finally: 
        await conn.close()

@app.get("/api/normalized/units")
async def get_norm_units():
    conn = await get_db_conn()
    if not conn: 
        return []
    
    try:
        rows = await conn.fetch("SELECT * FROM process_units ORDER BY unit_id")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Norm Units Error: {e}")
        return []
    finally: 
        await conn.close()

@app.get("/api/normalized/equipment")
async def get_norm_equipment():
    conn = await get_db_conn()
    if not conn: 
        return []
    
    try:
        rows = await conn.fetch("SELECT * FROM equipment ORDER BY unit_id")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Norm Equipment Error: {e}")
        return []
    finally: 
        await conn.close()

@app.post("/api/optimization/run")
async def run_process_optimization(request: OptimizationRequest):
    """
    Ejecuta la optimización utilizando el modelo entrenado con datos reales.
    """
    if not ML_OPTIMIZER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Motor ML no disponible")
    
    try:
        # Mapeamos los inputs a un diccionario simple
        current_vals = {
            'temperature': request.current_temperature,
            'pressure': request.current_pressure,
            'flow_rate': request.current_flow
        }
        
        # Llamada asíncrona al optimizador
        result = await optimizer.find_optimal_parameters(request.unit_id, current_vals)
        return result

    except Exception as e:
        logger.error(f"Error optimización: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/optimization/test")
async def test_process_optimization_browser(unit_id: str = "CDU-101"):
    """
    Prueba rápida desde navegador. Simula valores típicos de la unidad CDU-101.
    """
    if not ML_OPTIMIZER_AVAILABLE:
        return {"error": "ML no disponible"}

    # Valores típicos simulados para CDU-101 (basados en auto_generator)
    mock_vals = {
        'temperature': 350.5, # Típico entre 340-360
        'pressure': 20.0,     # Típico entre 15-25
        'flow_rate': 10050.0  # Típico ~10,000 bpd
    }
    
    try:
        result = await optimizer.find_optimal_parameters(unit_id, mock_vals)
        return {
            "status": "OK",
            "mode": "BROWSER_TEST",
            "input_simulado": mock_vals,
            "resultado_ia": result
        }
    except Exception as e:
        return {"error": str(e)}
@app.post("/api/optimization/train/{unit_id}")
async def force_train_model(unit_id: str):
    """Fuerza el re-entrenamiento del modelo manualmente"""
    if not ML_OPTIMIZER_AVAILABLE:
        raise HTTPException(503, "ML no disponible")
    return await optimizer.train_optimization_model(unit_id)
# ==============================================================================
# 13. GENERADOR DE REPORTES (PDF/HTML MEJORADO)
# ==============================================================================

@app.get("/api/reports/daily", response_class=HTMLResponse)
async def generate_daily_report():
    """
    Genera un reporte operativo diario con formato ejecutivo A4.
    Personalizado para Planta Maturín, Venezuela.
    """
    try:
        conn = await get_db_conn()
        
        # Consultas de datos
        if conn:
            kpis = await conn.fetch("SELECT * FROM kpis ORDER BY timestamp DESC LIMIT 15")
            alerts = await conn.fetch("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 8")
            tanks = await conn.fetch("SELECT * FROM tanks ORDER BY name")
            
            # Cálculo de promedios para el resumen
            avg_eff = await conn.fetchval("SELECT AVG(energy_efficiency) FROM kpis WHERE timestamp > NOW() - INTERVAL '24h'") or 0
            total_prod = await conn.fetchval("SELECT SUM(throughput) FROM kpis WHERE timestamp > NOW() - INTERVAL '24h'") or 0
            
            await conn.close()
        else:
            # Datos de respaldo si falla la DB
            kpis, alerts, tanks = [], [], []
            avg_eff, total_prod = 0, 0

        # Ajuste de Hora para Venezuela (UTC-4)
        # Los servidores suelen estar en UTC, restamos 4 horas manualmente
        ve_time = datetime.now(timezone.utc) - timedelta(hours=4)
        date_str = ve_time.strftime("%d/%m/%Y %H:%M")
        date_short = ve_time.strftime("%d/%m/%Y")

        # Generación de filas HTML
        rows_kpi = ""
        for r in kpis:
            # Ajustar hora de cada registro también
            row_time = r['timestamp']
            if row_time.tzinfo is None: # Si es naive, asumir UTC
                row_time = row_time.replace(tzinfo=timezone.utc)
            local_row_time = row_time - timedelta(hours=4)
            
            status_color = "#16a34a" if r['energy_efficiency'] > 90 else "#ca8a04" if r['energy_efficiency'] > 80 else "#dc2626"
            
            rows_kpi += f"""
            <tr>
                <td>{local_row_time.strftime('%H:%M')}</td>
                <td>{r['unit_id']}</td>
                <td style="font-weight:bold; color:{status_color}">{r['energy_efficiency']:.1f}%</td>
                <td>{r['throughput']:.0f} bbl</td>
                <td>{r['quality_score']:.1f}%</td>
            </tr>"""

        rows_tanks = ""
        for t in tanks:
            percent = (t['current_level'] / t['capacity']) * 100
            bar_color = "#3b82f6" if percent > 20 else "#dc2626"
            rows_tanks += f"""
            <tr>
                <td><strong>{t['name']}</strong></td>
                <td>{t['product']}</td>
                <td>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <div style="flex:1; background:#e2e8f0; height:8px; border-radius:4px; overflow:hidden;">
                            <div style="width:{percent}%; background:{bar_color}; height:100%;"></div>
                        </div>
                        <span style="font-size:0.85em">{t['current_level']:.0f} L</span>
                    </div>
                </td>
                <td><span class="badge">{t['status']}</span></td>
            </tr>"""

        rows_alert = ""
        if not alerts:
            rows_alert = "<tr><td colspan='4' style='text-align:center; color:#16a34a'>Sin incidentes reportados</td></tr>"
        else:
            for a in alerts:
                sev_style = "background:#fee2e2; color:#dc2626;" if a['severity'] == 'HIGH' else "background:#fef3c7; color:#d97706;"
                rows_alert += f"""
                <tr>
                    <td>{a['timestamp'].strftime('%H:%M')}</td>
                    <td>{a['unit_id']}</td>
                    <td><span style="padding:2px 6px; border-radius:4px; font-size:0.8em; font-weight:bold; {sev_style}">{a['severity']}</span></td>
                    <td>{a['message']}</td>
                </tr>"""

        # Plantilla HTML Completa
        html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Reporte Diario - RefineryIQ</title>
            <style>
                @page {{ size: A4; margin: 1.5cm; }}
                body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.5; font-size: 11px; }}
                .container {{ max-width: 100%; margin: 0 auto; }}
                
                /* Header */
                .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0f172a; padding-bottom: 15px; margin-bottom: 20px; }}
                .brand h1 {{ margin: 0; color: #0f172a; font-size: 24px; letter-spacing: -0.5px; }}
                .brand p {{ margin: 2px 0 0; color: #64748b; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }}
                .meta {{ text-align: right; }}
                .meta div {{ margin-bottom: 2px; }}
                
                /* Summary Cards */
                .summary {{ display: flex; gap: 15px; margin-bottom: 25px; }}
                .card {{ flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; padding: 10px 15px; border-radius: 6px; }}
                .card-label {{ font-size: 9px; color: #64748b; text-transform: uppercase; font-weight: bold; }}
                .card-value {{ font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 5px; }}
                
                /* Sections */
                h2 {{ background: #f1f5f9; padding: 8px 12px; border-left: 4px solid #3b82f6; margin: 20px 0 10px; font-size: 14px; color: #334155; }}
                
                /* Tables */
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
                th {{ background: #f8fafc; text-align: left; padding: 8px; border-bottom: 1px solid #cbd5e1; color: #475569; font-weight: 600; font-size: 10px; text-transform: uppercase; }}
                td {{ padding: 8px; border-bottom: 1px solid #e2e8f0; vertical-align: middle; }}
                tr:last-child td {{ border-bottom: none; }}
                
                .badge {{ background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 600; color: #475569; }}
                
                /* Footer / Signatures */
                .signatures {{ margin-top: 60px; display: flex; justify-content: space-between; page-break-inside: avoid; }}
                .sig-block {{ width: 40%; text-align: center; }}
                .sig-line {{ border-top: 1px solid #94a3b8; margin-bottom: 8px; }}
                .sig-name {{ font-weight: bold; font-size: 12px; }}
                .sig-title {{ color: #64748b; font-size: 10px; }}
                
                .footer {{ margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 10px; text-align: center; color: #94a3b8; font-size: 9px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="brand">
                        <h1>REFINERY IQ</h1>
                        <p>Planta Maturín, Estado Monagas - Venezuela</p>
                    </div>
                    <div class="meta">
                        <div style="font-weight:bold; font-size:14px;">REPORTE OPERATIVO</div>
                        <div>Fecha: {date_str}</div>
                        <div>ID: RPT-{int(time.time())}</div>
                    </div>
                </div>

                <div class="summary">
                    <div class="card">
                        <div class="card-label">Eficiencia Promedio (24h)</div>
                        <div class="card-value" style="color: {'#16a34a' if avg_eff > 90 else '#d97706'}">{avg_eff:.1f}%</div>
                    </div>
                    <div class="card">
                        <div class="card-label">Producción Total (24h)</div>
                        <div class="card-value">{total_prod:,.0f} bbl</div>
                    </div>
                    <div class="card">
                        <div class="card-label">Estado del Sistema</div>
                        <div class="card-value" style="color:#16a34a">OPERATIVO</div>
                    </div>
                </div>

                <h2>1. RENDIMIENTO DE PROCESO (Últimos Registros)</h2>
                <table>
                    <thead><tr><th width="15%">Hora</th><th width="25%">Unidad</th><th>Eficiencia</th><th>Throughput</th><th>Calidad</th></tr></thead>
                    <tbody>{rows_kpi}</tbody>
                </table>
                
                <h2>2. GESTIÓN DE INVENTARIOS Y TANQUES</h2>
                <table>
                    <thead><tr><th width="20%">Tanque</th><th width="30%">Producto</th><th width="30%">Nivel / Capacidad</th><th width="20%">Estado</th></tr></thead>
                    <tbody>{rows_tanks}</tbody>
                </table>

                <h2>3. INCIDENCIAS Y ALERTAS CRÍTICAS</h2>
                <table>
                    <thead><tr><th width="15%">Hora</th><th width="20%">Unidad</th><th width="15%">Severidad</th><th>Mensaje del Sistema</th></tr></thead>
                    <tbody>{rows_alert}</tbody>
                </table>
                
                <div class="signatures">
                    <div class="sig-block">
                        <div class="sig-line"></div>
                        <div class="sig-name">Carlos Gómez</div>
                        <div class="sig-title">GERENTE DE PLANTA</div>
                    </div>
                    <div class="sig-block">
                        <div class="sig-line"></div>
                        <div class="sig-name">Supervisión de Turno</div>
                        <div class="sig-title">OPERACIONES</div>
                    </div>
                </div>

                <div class="footer">
                    Documento generado automáticamente por RefineryIQ System v12.0 Enterprise | Confidencial<br>
                    Ubicación del Servidor: Maturín, VE | Zona Horaria: America/Caracas (UTC-4)
                </div>
            </div>
            
            <script>
                // Auto-imprimir al cargar
                window.onload = function() {{ setTimeout(function() {{ window.print(); }}, 500); }}
            </script>
        </body>
        </html>
        """
        return html
    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
        return HTMLResponse(f"Error interno generando el reporte: {str(e)}", status_code=500)

# ==============================================================================
# 14. HEALTH CHECK
# ==============================================================================

@app.get("/")
async def root():
    return {
        "message": "RefineryIQ API v12.0",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Render."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ==============================================================================
# 15. ARRANQUE LOCAL
# ==============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("\n" + "="*60)
    print(f"🚀 REFINERYIQ BACKEND V12 - PORT {port}")
    print("="*60)
    print(f"Docs: http://0.0.0.0:{port}/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)