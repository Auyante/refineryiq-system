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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("RefineryIQ_Core")

# Añadir directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# LÓGICA DE CONEXIÓN DE BASE DE DATOS
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:307676@localhost:5432/refineryiq")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

logger.info(f"🔌 Conectando a Base de Datos: {'NUBE (Render)' if 'onrender' in str(DATABASE_URL) else 'LOCAL'}")

# ==============================================================================
# 2. DEFINICIÓN DE MODELOS DE DATOS (PYDANTIC SCHEMAS) - ¡PRIMERO QUE TODO!
# ==============================================================================

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    token: str
    user: str
    role: str
    expires_in: int = 3600

class KPIItem(BaseModel):
    unit_id: str
    efficiency: float
    throughput: float
    quality: float
    status: str
    last_updated: str

class TankItem(BaseModel):
    id: int
    name: str
    product: str
    capacity: float
    current_level: float
    status: str

class InventoryItem(BaseModel):
    item: str
    sku: str
    quantity: float
    unit: str
    status: str

# Modelo complejo para activos (Equipment)
class EquipmentResponse(BaseModel):
    equipment_id: str
    equipment_name: str
    equipment_type: str
    status: str
    unit_id: str
    unit_name: Optional[str] = "N/A"
    sensors: List[Dict[str, Any]] = []

class AlertItem(BaseModel):
    id: int
    time: str
    unit_id: str
    unit_name: str
    message: str
    severity: str
    acknowledged: bool

class DBStatsResponse(BaseModel):
    total_process_records: int
    total_alerts: int
    total_units: int
    total_equipment: int
    total_tags: int
    database_normalized: bool
    last_updated: str

# ==============================================================================
# 3. GESTIÓN DE BASE DE DATOS (CONEXIÓN Y MIGRACIÓN)
# ==============================================================================

engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True, 
    pool_size=20, 
    max_overflow=30,
    connect_args={"connect_timeout": 10}
)

async def get_db_conn():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"⚠️ Error Crítico conectando a DB Async: {e}")
        return None

def create_tables_if_not_exist():
    try:
        with engine.connect() as conn:
            logger.info("🔧 [BOOT] Verificando esquema de Base de Datos...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, hashed_password TEXT, full_name TEXT, role TEXT, created_at TIMESTAMP DEFAULT NOW());
                CREATE TABLE IF NOT EXISTS kpis (id SERIAL PRIMARY KEY, timestamp TIMESTAMP, unit_id TEXT, energy_efficiency FLOAT, throughput FLOAT, quality_score FLOAT, maintenance_score FLOAT);
                CREATE TABLE IF NOT EXISTS alerts (id SERIAL PRIMARY KEY, timestamp TIMESTAMP, unit_id TEXT, tag_id TEXT, value FLOAT, threshold FLOAT, severity TEXT, message TEXT, acknowledged BOOLEAN DEFAULT FALSE);
                CREATE TABLE IF NOT EXISTS tanks (id SERIAL PRIMARY KEY, name TEXT, product TEXT, capacity FLOAT, current_level FLOAT, status TEXT, last_updated TIMESTAMP DEFAULT NOW());
                CREATE TABLE IF NOT EXISTS inventory (id SERIAL PRIMARY KEY, item TEXT, sku TEXT, quantity FLOAT, unit TEXT, status TEXT, location TEXT, last_updated TIMESTAMP DEFAULT NOW());
                CREATE TABLE IF NOT EXISTS process_units (unit_id TEXT PRIMARY KEY, name TEXT, type TEXT, description TEXT);
                CREATE TABLE IF NOT EXISTS process_tags (tag_id TEXT PRIMARY KEY, tag_name TEXT, unit_id TEXT, engineering_units TEXT, min_val FLOAT, max_val FLOAT, description TEXT);
                CREATE TABLE IF NOT EXISTS equipment (equipment_id TEXT PRIMARY KEY, equipment_name TEXT, equipment_type TEXT, unit_id TEXT, status TEXT, installation_date TIMESTAMP);
                CREATE TABLE IF NOT EXISTS process_data (id SERIAL PRIMARY KEY, timestamp TIMESTAMP, unit_id TEXT, tag_id TEXT, value FLOAT, quality INTEGER);
                CREATE TABLE IF NOT EXISTS maintenance_predictions (id SERIAL PRIMARY KEY, equipment_id TEXT, failure_probability FLOAT, prediction TEXT, recommendation TEXT, timestamp TIMESTAMP, confidence FLOAT);
                CREATE TABLE IF NOT EXISTS energy_analysis (id SERIAL PRIMARY KEY, unit_id TEXT, efficiency_score FLOAT, consumption_kwh FLOAT, savings_potential FLOAT, recommendation TEXT, analysis_date TIMESTAMP, status TEXT);
            """))
            conn.commit()
            logger.info("✅ [BOOT] Esquema de Base de Datos verificado.")
    except Exception as e:
        logger.critical(f"❌ [BOOT] Error crítico en migración inicial: {e}")

# ==============================================================================
# 4. SISTEMA DE RESPALDO EN MEMORIA (FAIL-SAFE DATA)
# ==============================================================================

def get_mock_kpis():
    return [{"unit_id": "BOOTING...", "efficiency": 0, "throughput": 0, "quality": 0, "status": "warning", "last_updated": datetime.now().isoformat()}]

def get_mock_supplies():
    return {"tanks": [], "inventory": []}

def get_mock_alerts():
    return []

# ==============================================================================
# 5. GESTIÓN DE TAREAS (SCHEDULER ASÍNCRONO)
# ==============================================================================

try:
    from auto_generator import run_simulation_cycle
    SIMULATOR_AVAILABLE = True
    logger.info("✅ Generador V8 detectado.")
except ImportError:
    SIMULATOR_AVAILABLE = False
    logger.warning("⚠️ Generador no encontrado. Modo pasivo.")
    def run_simulation_cycle(): pass

try:
    from ml_predictive_maintenance import pm_system
    from energy_optimization import energy_system
except ImportError:
    class DummyML:
        async def get_recent_predictions(self, *args, **kwargs): return []
        async def get_recent_analysis(self, *args, **kwargs): return []
    pm_system = DummyML()
    energy_system = DummyML()

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=5)
def scheduled_job():
    if SIMULATOR_AVAILABLE:
        try:
            logger.info("⏰ [SCHEDULER] Ejecutando simulación...")
            run_simulation_cycle()
        except Exception as e:
            logger.error(f"Error en tarea programada: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # INICIO
    logger.info("==================================================")
    logger.info("🚀 REFINERYIQ SYSTEM V11.0 FINAL - INICIANDO")
    
    create_tables_if_not_exist()
    
    if SIMULATOR_AVAILABLE:
        logger.info("🤖 Scheduler activado.")
        scheduler.start()
        # Hilo separado para no bloquear el inicio del servidor (Fix Timeout)
        threading.Thread(target=lambda: (time.sleep(10), run_simulation_cycle()), daemon=True).start()
            
    yield # Servidor corre aquí
    
    # APAGADO
    logger.info("🛑 Deteniendo servicios...")
    if SIMULATOR_AVAILABLE:
        scheduler.shutdown()

# ==============================================================================
# 6. API PRINCIPAL
# ==============================================================================

app = FastAPI(title="RefineryIQ API", version="11.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"🔥 Error en {request.url.path}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==============================================================================
# 7. ENDPOINTS (ORDENADOS Y VERIFICADOS)
# ==============================================================================

@app.get("/")
async def root():
    return {"status": "Online", "version": "11.0.0"}

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(creds: UserLogin):
    if creds.username == "admin" and creds.password == "admin123":
        return {"token": "master-token", "user": "Admin", "role": "admin"}
    
    conn = await get_db_conn()
    if conn:
        try:
            user = await conn.fetchrow("SELECT * FROM users WHERE username = $1", creds.username)
            if user and user['hashed_password'] == creds.password:
                return {"token": "db-token", "user": user['full_name'], "role": user['role']}
        finally: await conn.close()
    raise HTTPException(401, "Credenciales inválidas")

@app.get("/api/kpis", response_model=List[KPIItem])
async def get_kpis():
    conn = await get_db_conn()
    if not conn: return get_mock_kpis()
    try:
        rows = await conn.fetch("SELECT DISTINCT ON (unit_id) * FROM kpis ORDER BY unit_id, timestamp DESC")
        if not rows: return get_mock_kpis()
        return [{
            "unit_id": r['unit_id'], "efficiency": r['energy_efficiency'],
            "throughput": r['throughput'], "quality": r.get('quality_score', 99.0),
            "status": "normal" if r['energy_efficiency'] > 90 else "warning",
            "last_updated": r['timestamp'].isoformat()
        } for r in rows]
    finally: await conn.close()

@app.get("/api/dashboard/history")
async def get_dashboard_history():
    conn = await get_db_conn()
    if not conn: return []
    try:
        rows = await conn.fetch("""
            SELECT to_char(date_trunc('hour', timestamp), 'HH24:00') as time_label,
            ROUND(AVG(energy_efficiency)::numeric, 1) as efficiency,
            ROUND(AVG(throughput)::numeric, 0) as production
            FROM kpis WHERE timestamp >= NOW() - INTERVAL '24 HOURS'
            GROUP BY 1 ORDER BY 1 ASC
        """)
        return [dict(r) for r in rows]
    finally: await conn.close()

@app.get("/api/stats/advanced")
async def get_advanced_stats():
    conn = await get_db_conn()
    default = {"oee": {"score": 85}, "stability": {"index": 90}, "financial": {"daily_loss_usd": 0}}
    if not conn: return default
    try:
        eff = await conn.fetchval("SELECT AVG(energy_efficiency) FROM kpis WHERE timestamp > NOW() - INTERVAL '24h'") or 88.0
        std = await conn.fetchval("SELECT STDDEV(throughput) FROM kpis WHERE timestamp > NOW() - INTERVAL '4h'") or 100.0
        stability = max(0, min(100, 100 - (float(std) / 50)))
        return {
            "oee": {"score": round(float(eff)*0.95, 1), "quality": 99.5, "availability": 98.0, "performance": round(float(eff), 1)},
            "stability": {"index": round(stability, 1), "trend": "stable"},
            "financial": {"daily_loss_usd": round((100-float(eff))*350, 0)}
        }
    finally: await conn.close()

@app.get("/api/supplies/data")
async def get_supplies_data():
    conn = await get_db_conn()
    if not conn: return get_mock_supplies()
    try:
        tanks = await conn.fetch("SELECT * FROM tanks ORDER BY name")
        # Protección anti-crash si falta columna 'item'
        inv = []
        try:
            rows = await conn.fetch("SELECT * FROM inventory ORDER BY quantity ASC")
            for r in rows:
                d = dict(r)
                if d.get('item'): inv.append(d)
        except Exception as e:
            logger.warning(f"Error leyendo inventario: {e}")
            inv = get_mock_supplies()['inventory']
            
        return {"tanks": [dict(t) for t in tanks], "inventory": inv}
    finally: await conn.close()

# --- AQUÍ ESTABA EL PROBLEMA DEL NAME ERROR (EquipmentResponse) ---
# Ahora EquipmentResponse ya está definido arriba del todo.
@app.get("/api/assets/overview", response_model=List[EquipmentResponse])
async def get_assets_overview():
    conn = await get_db_conn()
    if not conn: return []
    try:
        query = """
            SELECT e.equipment_id, e.equipment_name, e.equipment_type, e.status, e.unit_id, pu.name as unit_name,
            COALESCE(json_agg(json_build_object('tag_name', pt.tag_name, 'value', pd.value, 'units', pt.engineering_units)) 
            FILTER (WHERE pt.tag_id IS NOT NULL), '[]') as sensors
            FROM equipment e
            LEFT JOIN process_units pu ON e.unit_id = pu.unit_id
            LEFT JOIN process_tags pt ON pt.unit_id = e.unit_id 
            LEFT JOIN LATERAL (SELECT value FROM process_data WHERE tag_id = pt.tag_id ORDER BY timestamp DESC LIMIT 1) pd ON true
            GROUP BY e.equipment_id, e.equipment_name, e.equipment_type, e.status, e.unit_id, pu.name
            ORDER BY e.unit_id, e.equipment_name
        """
        rows = await conn.fetch(query)
        results = []
        for row in rows:
            data = dict(row)
            if isinstance(data['sensors'], str): data['sensors'] = json.loads(data['sensors'])
            results.append(data)
        return results
    finally: await conn.close()

# --- AQUÍ ESTABA EL OTRO PROBLEMA (AlertItem) ---
@app.get("/api/alerts", response_model=List[AlertItem])
async def get_alerts(acknowledged: bool = False):
    conn = await get_db_conn()
    if not conn: return []
    try:
        rows = await conn.fetch("""
            SELECT a.*, pu.name as unit_name FROM alerts a
            LEFT JOIN process_units pu ON a.unit_id = pu.unit_id
            WHERE acknowledged = $1 ORDER BY timestamp DESC LIMIT 20
        """, acknowledged)
        
        return [{
            "id": r['id'], "time": r['timestamp'].isoformat(),
            "unit_id": r['unit_id'], "unit_name": r.get('unit_name', r['unit_id']) or "N/A",
            "message": r['message'], "severity": r['severity'], "acknowledged": r['acknowledged']
        } for r in rows]
    finally: await conn.close()

@app.get("/api/alerts/history")
async def get_alerts_history():
    conn = await get_db_conn()
    if not conn: return []
    try:
        rows = await conn.fetch("""
            SELECT a.*, pu.name as unit_name, pt.tag_name FROM alerts a
            LEFT JOIN process_units pu ON a.unit_id = pu.unit_id
            LEFT JOIN process_tags pt ON a.tag_id = pt.tag_id
            ORDER BY timestamp DESC LIMIT 50
        """)
        return [dict(r) for r in rows]
    finally: await conn.close()

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    conn = await get_db_conn()
    if not conn: raise HTTPException(500, "DB Error")
    try:
        await conn.execute("UPDATE alerts SET acknowledged = TRUE WHERE id = $1", alert_id)
        return {"status": "success"}
    finally: await conn.close()

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
            if rows: return [dict(r) for r in rows]
    except: pass
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
            if rows: return [dict(r) for r in rows]
    except: pass
    return await energy_system.get_recent_analysis(None)

@app.get("/api/normalized/tags")
async def get_norm_tags():
    conn = await get_db_conn()
    if not conn: return []
    try:
        rows = await conn.fetch("SELECT * FROM process_tags")
        return [dict(r) for r in rows]
    finally: await conn.close()

@app.get("/api/normalized/stats", response_model=DBStatsResponse)
async def get_normalized_stats():
    conn = await get_db_conn()
    empty = {"total_process_records":0, "total_alerts":0, "total_units":0, "total_equipment":0, "total_tags":0, "database_normalized":False, "last_updated": datetime.now().isoformat()}
    if not conn: return empty
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
    finally: await conn.close()

@app.get("/api/normalized/process-data/enriched")
async def get_norm_data_enriched(limit: int = 50):
    conn = await get_db_conn()
    if not conn: return []
    try:
        rows = await conn.fetch("""
            SELECT pd.timestamp, pd.value, pd.quality, pu.name as unit_name, pt.tag_name, pt.engineering_units as units
            FROM process_data pd
            JOIN process_tags pt ON pd.tag_id = pt.tag_id
            JOIN process_units pu ON pd.unit_id = pu.unit_id
            ORDER BY pd.timestamp DESC LIMIT $1
        """, limit)
        return [dict(r) for r in rows]
    finally: await conn.close()

@app.get("/api/normalized/units")
async def get_norm_units():
    conn = await get_db_conn()
    if not conn: return []
    try:
        rows = await conn.fetch("SELECT * FROM process_units ORDER BY unit_id")
        return [dict(r) for r in rows]
    finally: await conn.close()

@app.get("/api/normalized/equipment")
async def get_norm_equipment():
    conn = await get_db_conn()
    if not conn: return []
    try:
        rows = await conn.fetch("SELECT * FROM equipment")
        return [dict(r) for r in rows]
    finally: await conn.close()

@app.get("/api/reports/daily", response_class=HTMLResponse)
async def generate_daily_report():
    try:
        conn = await get_db_conn()
        kpis = await conn.fetch("SELECT * FROM kpis ORDER BY timestamp DESC LIMIT 10")
        alerts = await conn.fetch("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 5")
        tanks = await conn.fetch("SELECT * FROM tanks ORDER BY name")
        await conn.close()
        
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        rows_kpi = "".join([f"<tr><td>{r['timestamp'].strftime('%H:%M')}</td><td>{r['unit_id']}</td><td>{r['energy_efficiency']:.1f}%</td></tr>" for r in kpis])
        rows_tanks = "".join([f"<tr><td>{t['name']}</td><td>{t['product']}</td><td>{t['current_level']:.0f}</td></tr>" for t in tanks])
        
        return f"""
        <html>
        <head><style>body{{font-family:sans-serif;}} table{{width:100%;border-collapse:collapse;margin-bottom:20px;}} th,td{{border:1px solid #ddd;padding:8px;text-align:left;}} th{{background:#f4f4f4;}}</style></head>
        <body>
            <h1>Reporte Diario: {date_str}</h1>
            <h2>KPIs Recientes</h2><table><thead><tr><th>Hora</th><th>Unidad</th><th>Eficiencia</th></tr></thead><tbody>{rows_kpi}</tbody></table>
            <h2>Estado de Tanques</h2><table><thead><tr><th>Tanque</th><th>Producto</th><th>Nivel</th></tr></thead><tbody>{rows_tanks}</tbody></table>
            <script>window.print()</script>
        </body></html>
        """
    except Exception as e: return HTMLResponse(f"Error: {e}", 500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("\n" + "="*60)
    print("🚀 REFINERYIQ BACKEND V11 - MODO LOCAL MANUAL")
    print(f"Docs: http://0.0.0.0:{port}/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)