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

# Módulos IA Dummy
class DummyML:
    async def get_recent_predictions(self, *args, **kwargs): 
        return []
    async def get_recent_analysis(self, *args, **kwargs): 
        return []

pm_system = DummyML()
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- INICIO DEL SERVIDOR ---
    logger.info("==================================================")
    logger.info("🚀 REFINERYIQ SYSTEM V12.0 FINAL - INICIANDO")
    logger.info("==================================================")
    
    # 1. Crear tablas (Operación rápida)
    create_tables_if_not_exist()
    
    # 2. Iniciar Scheduler
    if SIMULATOR_AVAILABLE:
        logger.info("🤖 Scheduler activado.")
        scheduler.start()
        
        # 3. ANTI-FREEZE + SAFE BOOT:
        # Ejecutamos la simulación inicial en un hilo separado con un delay de 15s.
        # Esto permite que la API arranque instantáneamente y responda 'Live' a Render.
        # Además, da tiempo a que la DB esté lista.
        def delayed_start():
            time.sleep(15) 
            logger.info("⏰ Ejecutando simulación inicial (Delayed)...")
            try:
                run_simulation_cycle()
            except Exception as e:
                logger.error(f"Error en simulación inicial: {e}")

        threading.Thread(target=delayed_start, daemon=True).start()
            
    yield # Servidor corre aquí
    
    # --- APAGADO DEL SERVIDOR ---
    logger.info("🛑 Deteniendo servicios del sistema...")
    if SIMULATOR_AVAILABLE:
        scheduler.shutdown()

# ==============================================================================
# 6. API PRINCIPAL (FASTAPI APP)
# ==============================================================================

app = FastAPI(
    title="RefineryIQ Enterprise API",
    description="Backend industrial Full-Stack V12.0. Gestión integral de refinería.",
    version="12.0.0",
    lifespan=lifespan
)

# Configuración CORS EXTREMADAMENTE PERMISIVA para Render
# Configuración CORS para dominio personalizado
# Configuración CORS para todos los dominios
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
    
    # Para permitir desde cualquier origen en desarrollo
    "*"  # Solo para desarrollo, en producción es mejor especificar
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
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
        rows = await conn.fetch("""
            SELECT to_char(date_trunc('hour', timestamp), 'HH24:00') as time_label,
            ROUND(AVG(energy_efficiency)::numeric, 1) as efficiency,
            ROUND(AVG(throughput)::numeric, 0) as production
            FROM kpis WHERE timestamp >= NOW() - INTERVAL '24 HOURS'
            GROUP BY 1 ORDER BY 1 ASC
        """)
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
    check_query = "SELECT COUNT(*) as count FROM kpis WHERE timestamp > NOW() - INTERVAL '24 hours'"
    
    try:
        if conn:
            count_result = await conn.fetchrow(check_query)
            record_count = int(count_result['count'] or 0) if count_result else 0
            
            # Si no hay datos, generar algunos automáticamente
            if record_count < 5:
                logger.info("📊 Generando datos de KPIs iniciales para estadísticas...")
                await generate_initial_kpis(conn)
    except Exception as e:
        logger.error(f"Error verificando datos: {e}")
    
    # Valores por defecto más realistas
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
            "daily_loss_usd": 4350  # Valor fijo por defecto
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
                COUNT(*) as record_count
            FROM kpis 
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """
        
        kpis_result = await conn.fetchrow(kpis_query)
        
        if kpis_result and kpis_result['record_count'] > 0:
            avg_efficiency = float(kpis_result['avg_efficiency'] or 88.0)
            avg_throughput = float(kpis_result['avg_throughput'] or 12000)
            record_count = int(kpis_result['record_count'] or 1)
        else:
            # Si no hay datos, usar valores simulados
            avg_efficiency = 88.0
            avg_throughput = 12000
            record_count = 1
            
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
        performance = avg_efficiency  # Usamos la eficiencia como rendimiento
        quality = 99.2  # Valor fijo de calidad (podría venir de quality_score)
        
        oee_score = round((availability/100) * (performance/100) * (quality/100) * 100, 1)
        
        # 4. Calcular estabilidad
        # Menos alertas = más estabilidad
        stability_score = max(0, min(100, 100 - (active_alerts * 3)))
        
        # 5. Calcular impacto financiero
        # Pérdida = (100 - eficiencia) × factor de costo
        efficiency_factor = max(0, 100 - avg_efficiency)
        
        # Base de pérdida: $50 por cada 1% de ineficiencia
        base_loss = efficiency_factor * 50
        
        # Penalización por alertas: $100 por cada alerta activa
        alerts_penalty = active_alerts * 100
        
        # Penalización por baja producción: si throughput < 11500
        throughput_penalty = 0
        if avg_throughput < 11500:
            throughput_penalty = (11500 - avg_throughput) * 0.1
            
        daily_loss = round(base_loss + alerts_penalty + throughput_penalty, 0)
        
        # 6. Determinar tendencia
        trend = "improving"
        if active_alerts > 5:
            trend = "deteriorating"
        elif active_alerts > 2:
            trend = "stable"
            
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

# ==============================================================================
# 13. GENERADOR DE REPORTES (PDF)
# ==============================================================================

@app.get("/api/reports/daily", response_class=HTMLResponse)
async def generate_daily_report():
    try:
        conn = await get_db_conn()
        
        # Obtener todos los datos necesarios
        kpis = await conn.fetch("""
            SELECT k.*, pu.name as unit_name 
            FROM kpis k
            LEFT JOIN process_units pu ON k.unit_id = pu.unit_id
            WHERE k.timestamp > NOW() - INTERVAL '24 hours'
            ORDER BY k.timestamp DESC
            LIMIT 30
        """)
        
        alerts = await conn.fetch("""
            SELECT a.*, pu.name as unit_name 
            FROM alerts a
            LEFT JOIN process_units pu ON a.unit_id = pu.unit_id
            WHERE a.acknowledged = FALSE 
            AND a.timestamp > NOW() - INTERVAL '24 hours'
            ORDER BY a.timestamp DESC
            LIMIT 15
        """)
        
        tanks = await conn.fetch("SELECT * FROM tanks ORDER BY name")
        inventory = await conn.fetch("SELECT * FROM inventory WHERE status IN ('LOW', 'CRITICAL') ORDER BY quantity ASC LIMIT 10")
        
        await conn.close()
        
        date_str = datetime.now().strftime("%d/%m/%Y")
        time_str = datetime.now().strftime("%H:%M")
        
        # Calcular estadísticas
        total_production = sum([k['throughput'] for k in kpis]) if kpis else 0
        avg_efficiency = sum([k['energy_efficiency'] for k in kpis])/len(kpis) if kpis else 0
        critical_alerts = len([a for a in alerts if a['severity'] == 'HIGH'])
        
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reporte Diario RefineryIQ</title>
            <style>
                @page {{
                    size: A4;
                    margin: 2cm;
                }}
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background: white;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 3px solid #1e40af;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #1e40af;
                    margin-bottom: 5px;
                    font-size: 28px;
                }}
                .header .subtitle {{
                    color: #64748b;
                    font-size: 16px;
                }}
                .company-info {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 30px;
                    padding: 15px;
                    background: #f8fafc;
                    border-radius: 8px;
                }}
                .summary-cards {{
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    margin-bottom: 30px;
                }}
                .card {{
                    background: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 15px;
                    text-align: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}
                .card .value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #1e40af;
                    margin: 10px 0;
                }}
                .card .label {{
                    font-size: 12px;
                    color: #64748b;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .section {{
                    margin-bottom: 30px;
                    page-break-inside: avoid;
                }}
                .section-title {{
                    background: #1e40af;
                    color: white;
                    padding: 10px 15px;
                    border-radius: 6px;
                    font-size: 18px;
                    margin-bottom: 15px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                    font-size: 12px;
                }}
                th {{
                    background: #f1f5f9;
                    padding: 10px;
                    text-align: left;
                    border-bottom: 2px solid #e2e8f0;
                    font-weight: 600;
                    color: #475569;
                }}
                td {{
                    padding: 10px;
                    border-bottom: 1px solid #e2e8f0;
                }}
                tr:hover {{
                    background: #f8fafc;
                }}
                .signature-section {{
                    margin-top: 50px;
                    padding-top: 20px;
                    border-top: 2px solid #e2e8f0;
                }}
                .signature-line {{
                    width: 300px;
                    margin: 40px 0 10px;
                    border-top: 1px solid #333;
                    text-align: center;
                    padding-top: 10px;
                }}
                .footer {{
                    margin-top: 50px;
                    text-align: center;
                    font-size: 11px;
                    color: #94a3b8;
                    border-top: 1px solid #e2e8f0;
                    padding-top: 20px;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                .status-ok {{ background: #d1fae5; color: #065f46; }}
                .status-warning {{ background: #fef3c7; color: #92400e; }}
                .status-critical {{ background: #fee2e2; color: #991b1b; }}
                .watermark {{
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%) rotate(-45deg);
                    font-size: 100px;
                    color: rgba(30, 64, 175, 0.1);
                    font-weight: bold;
                    z-index: -1;
                    pointer-events: none;
                }}
            </style>
        </head>
        <body>
            <div class="watermark">CONFIDENCIAL</div>
            
            <div class="header">
                <h1>REPORTE DIARIO DE OPERACIONES</h1>
                <div class="subtitle">RefineryIQ System v12.0 - {date_str}</div>
            </div>
            
            <div class="company-info">
                <div>
                    <strong>Refinería Industrial Mexicana S.A. de C.V.</strong><br>
                    Carretera Industrial km 8.5<br>
                    Zona Industrial Norte, Monterrey, N.L.
                </div>
                <div>
                    <strong>Fecha de Generación:</strong> {date_str}<br>
                    <strong>Hora:</strong> {time_str}<br>
                    <strong>ID Reporte:</strong> RI-{datetime.now().strftime('%Y%m%d')}
                </div>
            </div>
            
            <div class="summary-cards">
                <div class="card">
                    <div class="value">{avg_efficiency:.1f}%</div>
                    <div class="label">Eficiencia Global</div>
                </div>
                <div class="card">
                    <div class="value">{total_production:,.0f}</div>
                    <div class="label">Producción Total (bbl)</div>
                </div>
                <div class="card">
                    <div class="value">{critical_alerts}</div>
                    <div class="label">Alertas Críticas</div>
                </div>
                <div class="card">
                    <div class="value">{len(inventory)}</div>
                    <div class="label">Items Bajo Stock</div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">📊 KPIs POR UNIDAD (Últimas 24h)</div>
                <table>
                    <thead>
                        <tr>
                            <th>Hora</th>
                            <th>Unidad</th>
                            <th>Eficiencia</th>
                            <th>Producción</th>
                            <th>Calidad</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''
                        <tr>
                            <td>{k['timestamp'].strftime('%H:%M')}</td>
                            <td><strong>{k['unit_name'] or k['unit_id']}</strong></td>
                            <td>{k['energy_efficiency']:.1f}%</td>
                            <td>{k['throughput']:,.0f}</td>
                            <td>{k['quality_score']:.1f}%</td>
                            <td>
                                <span class="status-badge {'status-ok' if k['energy_efficiency'] > 90 else 'status-warning'}">
                                    {"ÓPTIMO" if k['energy_efficiency'] > 90 else "REVISAR"}
                                </span>
                            </td>
                        </tr>
                        ''' for k in kpis])}
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <div class="section-title">⚠️ ALERTAS ACTIVAS</div>
                <table>
                    <thead>
                        <tr>
                            <th>Hora</th>
                            <th>Unidad</th>
                            <th>Severidad</th>
                            <th>Descripción</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''
                        <tr>
                            <td>{a['timestamp'].strftime('%H:%M')}</td>
                            <td>{a['unit_name'] or a['unit_id']}</td>
                            <td>
                                <span class="status-badge {'status-critical' if a['severity'] == 'HIGH' else 'status-warning'}">
                                    {a['severity']}
                                </span>
                            </td>
                            <td>{a['message']}</td>
                            <td>{"PENDIENTE" if not a['acknowledged'] else "ATENDIDA"}</td>
                        </tr>
                        ''' for a in alerts]) if alerts else '<tr><td colspan="5" style="text-align:center;color:#94a3b8">No hay alertas activas</td></tr>'}
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <div class="section-title">🛢️ INVENTARIO DE TANQUES</div>
                <table>
                    <thead>
                        <tr>
                            <th>Tanque</th>
                            <th>Producto</th>
                            <th>Capacidad</th>
                            <th>Nivel Actual</th>
                            <th>% Lleno</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''
                        <tr>
                            <td><strong>{t['name']}</strong></td>
                            <td>{t['product']}</td>
                            <td>{t['capacity']:,.0f} L</td>
                            <td>{t['current_level']:,.0f} L</td>
                            <td>{(t['current_level']/t['capacity']*100):.1f}%</td>
                            <td>
                                <span class="status-badge {'status-ok' if t['status'] == 'STABLE' else 'status-warning'}">
                                    {t['status']}
                                </span>
                            </td>
                        </tr>
                        ''' for t in tanks])}
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <div class="section-title">📦 INVENTARIO CRÍTICO</div>
                <table>
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th>SKU</th>
                            <th>Cantidad</th>
                            <th>Unidad</th>
                            <th>Estado</th>
                            <th>Recomendación</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''
                        <tr>
                            <td>{i['item']}</td>
                            <td><code>{i['sku']}</code></td>
                            <td>{i['quantity']}</td>
                            <td>{i['unit']}</td>
                            <td>
                                <span class="status-badge {'status-critical' if i['status'] == 'CRITICAL' else 'status-warning'}">
                                    {i['status']}
                                </span>
                            </td>
                            <td>{"REORDENAR URGENTE" if i['status'] == 'CRITICAL' else "REVISAR STOCK"}</td>
                        </tr>
                        ''' for i in inventory]) if inventory else '<tr><td colspan="6" style="text-align:center;color:#94a3b8">Todos los inventarios en niveles normales</td></tr>'}
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <div class="section-title">📋 RECOMENDACIONES OPERATIVAS</div>
                <div style="background: #f0f9ff; padding: 15px; border-radius: 6px; border-left: 4px solid #0ea5e9;">
                    <ol style="margin: 0; padding-left: 20px;">
                        <li>Mantener monitoreo continuo en unidad CDU-101 (temperaturas en límite superior)</li>
                        <li>Programar mantenimiento preventivo para bomba PUMP-305 en próximos 7 días</li>
                        <li>Revisar niveles de catalizador FCC-ZSM5 (estado: CRÍTICO)</li>
                        <li>Optimizar intercambiadores de calor en HT-305 para mejorar eficiencia energética</li>
                        <li>Verificar calibración de sensores de presión en FCC-201</li>
                    </ol>
                </div>
            </div>
            
            <div class="signature-section">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <div class="signature-line"></div>
                        <div style="text-align: center; margin-top: 5px;">
                            <strong>Ing. Carlos Martínez</strong><br>
                            Supervisor de Operaciones
                        </div>
                    </div>
                    <div>
                        <div class="signature-line"></div>
                        <div style="text-align: center; margin-top: 5px;">
                            <strong>Lic. Ana Rodríguez</strong><br>
                            Gerente de Planta
                        </div>
                    </div>
                </div>
                
                <div style="margin-top: 30px; text-align: center; font-size: 12px; color: #64748b;">
                    <strong>Este documento es propiedad de Refinería Industrial Mexicana S.A. de C.V.</strong><br>
                    Su distribución está restringida a personal autorizado.
                </div>
            </div>
            
            <div class="footer">
                <p>Reporte generado automáticamente por Sistema RefineryIQ v12.0</p>
                <p>Documento: RI-{datetime.now().strftime('%Y%m%d-%H%M')} | Página 1 de 1</p>
            </div>
            
            <script>
                // Auto-impresión después de 1 segundo
                setTimeout(() => {{
                    window.print();
                }}, 1000);
            </script>
        </body>
        </html>
        """
    except Exception as e: 
        return HTMLResponse(f"""
        <html>
        <body style="font-family: sans-serif; padding: 40px; color: #991b1b;">
            <h2>❌ Error generando reporte</h2>
            <p>{str(e)}</p>
            <p><small>Verifique la conexión a la base de datos y vuelva a intentar.</small></p>
        </body>
        </html>
        """, 500)

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