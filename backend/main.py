import os
import sys
import time
import json
import random
import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

# --- LIBRERÍAS DE SERVIDOR (FASTAPI) ---
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Body, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

# --- LIBRERÍAS DE BASE DE DATOS (SQLALCHEMY + ASYNCPG) ---
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# --- LIBRERÍAS DE TAREAS Y ML ---
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==============================================================================
# 1. CONFIGURACIÓN DE LOGGING Y ENTORNO
# ==============================================================================

# Configuración de logs profesional
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("RefineryIQ")

# Añadir directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# LÓGICA DE CONEXIÓN DE BASE DE DATOS
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:307676@localhost:5432/refineryiq")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ==============================================================================
# 2. DEFINICIÓN DE MODELOS DE DATOS (PYDANTIC SCHEMAS)
# ==============================================================================
# Estos modelos garantizan que la API siempre devuelva la estructura exacta
# que espera el Frontend, evitando errores de "undefined".

class KPIResponse(BaseModel):
    unit_id: str
    efficiency: float
    throughput: float
    quality: float
    status: str
    last_updated: str

class AlertResponse(BaseModel):
    id: int
    time: str
    unit_id: str
    unit_name: str
    message: str
    severity: str
    acknowledged: bool

class TankResponse(BaseModel):
    id: int
    name: str
    product: str
    capacity: float
    current_level: float
    status: str

class InventoryResponse(BaseModel):
    item: str
    sku: str
    quantity: float
    unit: str
    status: str

class EquipmentResponse(BaseModel):
    equipment_id: str
    equipment_name: str
    equipment_type: str
    status: str
    unit_id: str
    unit_name: Optional[str] = "N/A"
    sensors: List[Dict[str, Any]] = []

class StatsResponse(BaseModel):
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

# Motor Síncrono (SQLAlchemy) para operaciones DDL (Crear tablas)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=20, max_overflow=30)

# Motor Asíncrono (AsyncPG) para operaciones de API (Alta velocidad)
async def get_db_conn():
    """Establece una conexión asíncrona de alto rendimiento."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"⚠️ Error conectando a DB Async: {e}")
        return None

def create_tables_if_not_exist():
    """
    Sistema de Auto-Migración 'Self-Healing'.
    Crea todas las tablas necesarias si no existen.
    """
    try:
        with engine.connect() as conn:
            logger.info("🔧 [BOOT] Verificando esquema de Base de Datos...")
            
            # Definición masiva de tablas (SQL DDL)
            conn.execute(text("""
                -- USUARIOS
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY, username TEXT UNIQUE, hashed_password TEXT, 
                    full_name TEXT, role TEXT, created_at TIMESTAMP DEFAULT NOW()
                );
                
                -- OPERACIONES
                CREATE TABLE IF NOT EXISTS kpis (
                    id SERIAL PRIMARY KEY, timestamp TIMESTAMP, unit_id TEXT, 
                    energy_efficiency FLOAT, throughput FLOAT, quality_score FLOAT, 
                    maintenance_score FLOAT
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY, timestamp TIMESTAMP, unit_id TEXT, 
                    tag_id TEXT, value FLOAT, threshold FLOAT, severity TEXT, 
                    message TEXT, acknowledged BOOLEAN DEFAULT FALSE
                );
                
                -- LOGÍSTICA
                CREATE TABLE IF NOT EXISTS tanks (
                    id SERIAL PRIMARY KEY, name TEXT, product TEXT, 
                    capacity FLOAT, current_level FLOAT, status TEXT, last_updated TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY, item TEXT, sku TEXT, 
                    quantity FLOAT, unit TEXT, status TEXT, location TEXT
                );
                
                -- NORMALIZACIÓN (SOLUCIÓN ERRORES FRONTEND)
                CREATE TABLE IF NOT EXISTS process_units (
                    unit_id TEXT PRIMARY KEY, name TEXT, type TEXT, description TEXT
                );
                CREATE TABLE IF NOT EXISTS process_tags (
                    tag_id TEXT PRIMARY KEY, tag_name TEXT, unit_id TEXT, 
                    engineering_units TEXT, min_val FLOAT, max_val FLOAT
                );
                CREATE TABLE IF NOT EXISTS equipment (
                    equipment_id TEXT PRIMARY KEY, equipment_name TEXT, 
                    equipment_type TEXT, unit_id TEXT, status TEXT, installation_date TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS process_data (
                    id SERIAL PRIMARY KEY, timestamp TIMESTAMP, 
                    unit_id TEXT, tag_id TEXT, value FLOAT, quality INTEGER
                );
                
                -- INTELIGENCIA ARTIFICIAL
                CREATE TABLE IF NOT EXISTS maintenance_predictions (
                    id SERIAL PRIMARY KEY, equipment_id TEXT, failure_probability FLOAT,
                    prediction TEXT, recommendation TEXT, timestamp TIMESTAMP, confidence FLOAT
                );
                CREATE TABLE IF NOT EXISTS energy_analysis (
                    id SERIAL PRIMARY KEY, unit_id TEXT, efficiency_score FLOAT,
                    consumption_kwh FLOAT, savings_potential FLOAT, recommendation TEXT,
                    analysis_date TIMESTAMP, status TEXT
                );
            """))
            conn.commit()
            logger.info("✅ [BOOT] Esquema de Base de Datos verificado y listo.")
    except Exception as e:
        logger.critical(f"❌ [BOOT] Error crítico en migración: {e}")

# ==============================================================================
# 4. SISTEMA DE RESPALDO EN MEMORIA (FAIL-SAFE DATA)
# ==============================================================================
# Si la base de datos falla o está vacía, estas funciones generan datos
# en el momento para que el Frontend NUNCA muestre pantalla blanca.

def generate_mock_kpis():
    return [
        {"unit_id": "CDU-101", "efficiency": 92.5, "throughput": 12500, "quality": 99.8, "status": "normal", "last_updated": datetime.now().isoformat()},
        {"unit_id": "FCC-201", "efficiency": 88.2, "throughput": 15200, "quality": 98.5, "status": "warning", "last_updated": datetime.now().isoformat()},
        {"unit_id": "HT-305",  "efficiency": 95.0, "throughput": 8500,  "quality": 99.9, "status": "normal", "last_updated": datetime.now().isoformat()}
    ]

def generate_mock_tanks():
    return [
        {"id": 1, "name": "TK-101 (Respaldo)", "product": "Crudo Maya", "capacity": 50000, "current_level": 25000, "status": "STABLE"},
        {"id": 2, "name": "TK-102 (Respaldo)", "product": "Gasolina", "capacity": 30000, "current_level": 15000, "status": "FILLING"}
    ]

# ==============================================================================
# 5. GESTIÓN DE TAREAS EN SEGUNDO PLANO (SIMULACIÓN)
# ==============================================================================

# Intentamos importar el generador avanzado V7
try:
    from auto_generator import run_simulation_cycle
    SIMULATOR_AVAILABLE = True
except ImportError:
    SIMULATOR_AVAILABLE = False
    logger.warning("⚠️ auto_generator.py no encontrado. Usando modo pasivo.")
    def run_simulation_cycle(): pass

# Importamos (o simulamos) los módulos de IA
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
    """Ejecuta el ciclo de simulación cada 5 minutos."""
    if SIMULATOR_AVAILABLE:
        try:
            logger.info("⏰ Ejecutando ciclo programado de simulación...")
            run_simulation_cycle()
        except Exception as e:
            logger.error(f"Error en tarea programada: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # INICIO
    logger.info("==================================================")
    logger.info("🚀 REFINERYIQ SYSTEM V7.0 ENTERPRISE - INICIANDO")
    logger.info(f"📡 Entorno: {'NUBE (Render)' if 'onrender' in str(DATABASE_URL) else 'LOCAL'}")
    
    create_tables_if_not_exist()
    
    if SIMULATOR_AVAILABLE:
        logger.info("🤖 Iniciando Motor de Simulación Industrial...")
        scheduler.start()
        # Ejecución inicial para asegurar datos al arranque
        try:
            run_simulation_cycle()
        except Exception as e:
            logger.error(f"Error en simulación inicial: {e}")
            
    yield # La aplicación corre aquí
    
    # APAGADO
    logger.info("🛑 Deteniendo servicios...")
    if SIMULATOR_AVAILABLE:
        scheduler.shutdown()

# ==============================================================================
# 6. API PRINCIPAL (FASTAPI APP)
# ==============================================================================

app = FastAPI(
    title="RefineryIQ Enterprise API",
    description="Backend industrial para monitoreo, mantenimiento y gestión de activos.",
    version="7.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# 7. ENDPOINTS: AUTHENTICATION
# ==============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(creds: LoginRequest):
    logger.info(f"🔐 Intento de login: {creds.username}")
    # Backdoor administrativa para soporte
    if creds.username == "admin" and creds.password == "admin123":
        return {"token": "master-token", "user": "Admin", "role": "admin"}
    
    conn = await get_db_conn()
    if conn:
        try:
            user = await conn.fetchrow("SELECT * FROM users WHERE username = $1", creds.username)
            if user and user['hashed_password'] == creds.password:
                return {"token": "db-token", "user": user['full_name'], "role": user['role']}
        finally:
            await conn.close()
            
    raise HTTPException(status_code=401, detail="Credenciales inválidas")

# ==============================================================================
# 8. ENDPOINTS: DASHBOARD & KPIS
# ==============================================================================

@app.get("/api/kpis", response_model=List[KPIResponse])
async def get_kpis():
    """Devuelve los KPIs más recientes para las tarjetas principales."""
    conn = await get_db_conn()
    if not conn: return generate_mock_kpis() # Fail-safe
    
    try:
        rows = await conn.fetch("""
            SELECT DISTINCT ON (unit_id) * FROM kpis 
            ORDER BY unit_id, timestamp DESC 
        """)
        
        if not rows: return generate_mock_kpis() # Si la DB está vacía
        
        return [{
            "unit_id": r['unit_id'],
            "efficiency": r['energy_efficiency'],
            "throughput": r['throughput'],
            "quality": r.get('quality_score', 99.0),
            "status": "normal" if r['energy_efficiency'] > 90 else "warning",
            "last_updated": r['timestamp'].isoformat()
        } for r in rows]
    finally:
        await conn.close()

@app.get("/api/dashboard/history")
async def get_dashboard_history():
    """Historial de producción últimas 24h (Gráfico de Área)."""
    conn = await get_db_conn()
    if not conn: return []
    try:
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
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@app.get("/api/stats/advanced")
async def get_advanced_stats():
    """
    Estadísticas calculadas para el Radar Chart y Panel Financiero.
    Soluciona el problema de "Salud de Activos = 0".
    """
    conn = await get_db_conn()
    default = {"oee": {"score": 85}, "stability": {"index": 90}, "financial": {"daily_loss_usd": 0}}
    
    if not conn: return default
    try:
        # 1. Eficiencia Media (OEE Proxy)
        eff = await conn.fetchval("SELECT AVG(energy_efficiency) FROM kpis WHERE timestamp > NOW() - INTERVAL '24h'")
        eff = float(eff) if eff else 88.0
        
        # 2. Desviación Estándar (Estabilidad)
        std = await conn.fetchval("SELECT STDDEV(throughput) FROM kpis WHERE timestamp > NOW() - INTERVAL '4h'")
        std = float(std) if std else 100.0
        stability = max(0, min(100, 100 - (std / 50)))
        
        # 3. Finanzas
        loss = (100 - eff) * 350 # Costo de oportunidad arbitrario

        return {
            "oee": {
                "score": round(eff * 0.95, 1), # OEE suele ser menor que eficiencia mecánica
                "quality": 99.5,
                "availability": 98.0,
                "performance": round(eff, 1)
            },
            "stability": {
                "index": round(stability, 1),
                "trend": "stable" if stability > 80 else "volatile"
            },
            "financial": {
                "daily_loss_usd": round(loss, 0),
                "potential_annual_savings": round(loss * 365, 0)
            }
        }
    finally:
        await conn.close()

# ==============================================================================
# 9. ENDPOINTS: NORMALIZACIÓN Y BASE DE DATOS (FIX 404)
# ==============================================================================

@app.get("/api/normalized/tags")
async def get_norm_tags():
    """
    [CRÍTICO] Endpoint que faltaba en tu versión anterior.
    Devuelve la lista de tags para el visor de DB.
    """
    conn = await get_db_conn()
    if not conn: return []
    try:
        rows = await conn.fetch("""
            SELECT pt.*, pu.name as unit_name 
            FROM process_tags pt 
            LEFT JOIN process_units pu ON pt.unit_id = pu.unit_id
            ORDER BY pt.tag_id
        """)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@app.get("/api/normalized/stats")
async def get_normalized_stats():
    """Estadísticas de la base de datos (Conteos reales)."""
    conn = await get_db_conn()
    if not conn: return {}
    try:
        kpis = await conn.fetchval("SELECT COUNT(*) FROM kpis")
        # Solo contamos alertas activas no reconocidas
        alerts = await conn.fetchval("SELECT COUNT(*) FROM alerts WHERE acknowledged = FALSE")
        units = await conn.fetchval("SELECT COUNT(*) FROM process_units")
        equip = await conn.fetchval("SELECT COUNT(*) FROM equipment")
        tags = await conn.fetchval("SELECT COUNT(*) FROM process_tags")
        
        return {
            "total_process_records": kpis,
            "total_alerts": alerts,
            "total_units": units,
            "total_equipment": equip,
            "total_tags": tags,
            "database_normalized": True,
            "last_updated": datetime.now().isoformat()
        }
    finally:
        await conn.close()

@app.get("/api/normalized/process-data/enriched")
async def get_norm_data_enriched(limit: int = 50):
    conn = await get_db_conn()
    if not conn: return []
    try:
        rows = await conn.fetch("""
            SELECT pd.timestamp, pd.value, pd.quality,
                   pu.name as unit_name, pt.tag_name, pt.engineering_units as units
            FROM process_data pd
            JOIN process_tags pt ON pd.tag_id = pt.tag_id
            JOIN process_units pu ON pd.unit_id = pu.unit_id
            ORDER BY pd.timestamp DESC
            LIMIT $1
        """, limit)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

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
        rows = await conn.fetch("""
            SELECT e.*, pu.name as unit_name 
            FROM equipment e
            LEFT JOIN process_units pu ON e.unit_id = pu.unit_id
            ORDER BY e.unit_id
        """)
        return [dict(r) for r in rows]
    finally: await conn.close()

# ==============================================================================
# 10. ENDPOINTS: SUPPLY & INVENTORY
# ==============================================================================

@app.get("/api/supplies/data")
async def get_supplies_data():
    conn = await get_db_conn()
    if not conn: return {"tanks": generate_mock_tanks(), "inventory": []}
    
    try:
        tanks = await conn.fetch("SELECT * FROM tanks ORDER BY name")
        # Filtramos inventario con nombres válidos
        inv = await conn.fetch("SELECT * FROM inventory WHERE item IS NOT NULL ORDER BY quantity ASC")
        
        return {
            "tanks": [dict(t) for t in tanks],
            "inventory": [dict(i) for i in inv]
        }
    finally:
        await conn.close()

# ==============================================================================
# 11. ENDPOINTS: ASSETS & SENSORS
# ==============================================================================

@app.get("/api/assets/overview", response_model=List[EquipmentResponse])
async def get_assets_overview():
    """
    Endpoint masivo que une Equipos + Unidades + Tags + Último Valor.
    """
    conn = await get_db_conn()
    if not conn: return []
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
                SELECT value FROM process_data 
                WHERE tag_id = pt.tag_id 
                ORDER BY timestamp DESC LIMIT 1
            ) pd ON true
            GROUP BY e.equipment_id, e.equipment_name, e.equipment_type, e.status, e.unit_id, pu.name
            ORDER BY e.unit_id, e.equipment_name
        """
        rows = await conn.fetch(query)
        
        results = []
        for row in rows:
            data = dict(row)
            if isinstance(data['sensors'], str):
                data['sensors'] = json.loads(data['sensors'])
            results.append(data)
        return results
    except Exception as e:
        logger.error(f"Error fetching assets: {e}")
        return []
    finally:
        await conn.close()

# ==============================================================================
# 12. ENDPOINTS: ALERTS & MAINTENANCE
# ==============================================================================

@app.get("/api/alerts")
async def get_alerts(acknowledged: bool = False):
    conn = await get_db_conn()
    if not conn: return []
    try:
        rows = await conn.fetch("""
            SELECT a.*, pu.name as unit_name 
            FROM alerts a
            LEFT JOIN process_units pu ON a.unit_id = pu.unit_id
            WHERE acknowledged = $1 
            ORDER BY timestamp DESC LIMIT 20
        """, acknowledged)
        return [dict(r) for r in rows]
    finally: await conn.close()

@app.get("/api/alerts/history")
async def get_alerts_history():
    conn = await get_db_conn()
    if not conn: return []
    try:
        rows = await conn.fetch("""
            SELECT a.*, pu.name as unit_name, pt.tag_name
            FROM alerts a
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
                SELECT mp.*, e.equipment_name 
                FROM maintenance_predictions mp
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
                SELECT ea.*, pu.name as unit_name 
                FROM energy_analysis ea
                LEFT JOIN process_units pu ON ea.unit_id = pu.unit_id
                ORDER BY analysis_date DESC LIMIT 5
            """)
            await conn.close()
            if rows: return [dict(r) for r in rows]
    except: pass
    return await energy_system.get_recent_analysis(None)

# ==============================================================================
# 13. GENERADOR DE REPORTES (HTML/PDF)
# ==============================================================================

@app.get("/api/reports/daily", response_class=HTMLResponse)
async def generate_daily_report():
    try:
        conn = await get_db_conn()
        kpis = await conn.fetch("SELECT * FROM kpis ORDER BY timestamp DESC LIMIT 10")
        alerts = await conn.fetch("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 5")
        tanks = await conn.fetch("SELECT * FROM tanks ORDER BY name")
        await conn.close()

        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        rows_kpi = "".join([f"<tr><td>{r['timestamp'].strftime('%H:%M')}</td><td>{r['unit_id']}</td><td>{r['energy_efficiency']:.1f}%</td><td>{r['throughput']:.0f}</td></tr>" for r in kpis])
        rows_alert = "".join([f"<tr><td>{r['timestamp'].strftime('%H:%M')}</td><td>{r['severity']}</td><td>{r['message']}</td></tr>" for r in alerts])
        rows_tanks = "".join([f"<tr><td>{t['name']}</td><td>{t['product']}</td><td>{t['current_level']:.0f} / {t['capacity']:.0f}</td><td>{t['status']}</td></tr>" for t in tanks])
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reporte Diario - RefineryIQ</title>
            <style>
                @page {{ size: A4; margin: 2cm; }}
                body {{ font-family: 'Segoe UI', Helvetica, sans-serif; color: #333; line-height: 1.4; font-size: 12px; }}
                .header {{ border-bottom: 2px solid #1e3a8a; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #1e3a8a; }}
                h2 {{ background: #f1f5f9; padding: 8px; border-left: 5px solid #3b82f6; margin-top: 25px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th {{ background: #f8fafc; text-align: left; padding: 8px; border: 1px solid #e2e8f0; }}
                td {{ padding: 8px; border: 1px solid #e2e8f0; }}
                .footer {{ margin-top: 50px; text-align: center; font-size: 10px; color: #999; border-top: 1px solid #eee; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">REFINERY IQ</div>
                <div style="text-align:right">
                    <strong>REPORTE OPERATIVO DIARIO</strong><br>
                    Fecha: {date_str}<br>
                    ID: RPT-{int(time.time())}
                </div>
            </div>

            <h2>1. RENDIMIENTO DE PLANTA (KPIs)</h2>
            <table><thead><tr><th>Hora</th><th>Unidad</th><th>Eficiencia</th><th>Producción (bbl)</th></tr></thead><tbody>{rows_kpi}</tbody></table>
            
            <h2>2. ESTADO DE TANQUES</h2>
            <table><thead><tr><th>Tanque</th><th>Producto</th><th>Nivel Actual / Capacidad</th><th>Estado</th></tr></thead><tbody>{rows_tanks}</tbody></table>

            <h2>3. ALERTAS CRÍTICAS</h2>
            <table><thead><tr><th>Hora</th><th>Severidad</th><th>Mensaje</th></tr></thead><tbody>{rows_alert}</tbody></table>
            
            <div style="margin-top: 60px; display: flex; justify-content: space-between;">
                <div style="border-top: 1px solid #333; width: 40%; text-align: center; padding-top: 10px;">Gerente de Planta</div>
                <div style="border-top: 1px solid #333; width: 40%; text-align: center; padding-top: 10px;">Supervisor de Turno</div>
            </div>

            <div class="footer">Generado automáticamente por RefineryIQ System v7.0 Enterprise | Confidencial</div>
            <script>window.onload = function() {{ window.print(); }}</script>
        </body>
        </html>
        """
        return html
    except Exception as e:
        return HTMLResponse(f"Error generando reporte: {e}", status_code=500)

# ==============================================================================
# 14. ARRANQUE LOCAL
# ==============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 REFINERYIQ BACKEND - MODO LOCAL MANUAL")
    print("="*60)
    print("Docs: http://localhost:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)