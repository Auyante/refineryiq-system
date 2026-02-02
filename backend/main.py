from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import asyncpg
import uvicorn
from pydantic import BaseModel
from typing import List, Optional
import json
import random
import time
import sys
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(...)

# LISTA DE INVITADOS PERMITIDOS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "https://refineryiq.dev",            # <--- TU DOMINIO
    "https://www.refineryiq.dev",        # <--- TU DOMINIO CON WWW
    "https://refineryiq-system.onrender.com" # <--- EL BACKEND MISMO
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # TRUCO TEMPORAL: Permitir a todos para probar
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Agregar el directorio actual al path para que Python encuentre los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar los sistemas ML que creamos (ahora desde el mismo directorio)
try:
    from ml_predictive_maintenance import pm_system
    from energy_optimization import energy_system
    print("✅ Módulos ML importados correctamente")
except ImportError as e:
    print(f"⚠️ Error al importar módulos ML: {e}")
    # Si falla, usamos versiones simuladas para que al menos funcione
    class DummySystem:
        async def train_models(self, db_conn):
            return {"status": "simulated", "message": "Modelos simulados"}
        async def analyze_all_equipment(self, db_conn):
            return []
        async def get_recent_predictions(self, db_conn, limit=5):
            return []
        async def analyze_unit_energy(self, db_conn, unit_id, hours=24):
            return {
                "unit_id": unit_id,
                "avg_energy_consumption": 40.0,
                "benchmark": 45.0,
                "target": 42.0,
                "efficiency_score": 90.0,
                "status": "GOOD",
                "inefficiencies": [],
                "recommendations": [],
                "estimated_savings": 0.0
            }
        async def get_recent_analysis(self, db_conn, unit_id=None, limit=5):
            return []
    
    pm_system = DummySystem()
    energy_system = DummySystem()

app = FastAPI(title="RefineryIQ API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <--- IMPORTANTE: El asterisco permite TODAS las IPs (PC y Celular)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ==============================================================================
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ==============================================================================
# CONEXIÓN INTELIGENTE (Detecta Nube vs Casa)
# ==============================================================================

# 1. BUSCAR LA VARIABLE:
#    El código pregunta: "¿Existe una variable 'DATABASE_URL' en el sistema?"
#    - SI ESTAMOS EN RENDER: Sí existe, y tomará la URL externa automáticamente.
#    - SI ESTAMOS EN TU PC: No existe, así que usará la que está después de la coma (localhost).
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:307676@localhost:5432/refineryiq")

# 2. PARCHE PARA RENDER:
#    Render a veces entrega la URL como "postgres://", pero Python necesita "postgresql://"
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. CREAR EL MOTOR:
engine = create_engine(DATABASE_URL)

# 4. PREPARAR SESIÓN:
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
# ==============================================================================

# Modelos EXISTENTES
class ProcessData(BaseModel):
    timestamp: datetime
    unit_id: str
    tag_id: str
    value: float
    quality: int = 1

# Modelos NUEVOS para base de datos normalizada
class UnitInfo(BaseModel):
    unit_id: str
    unit_name: str
    unit_type: str
    description: Optional[str] = None
    capacity: Optional[float] = None
    status: str = "ACTIVE"

class TagInfo(BaseModel):
    tag_id: str
    tag_name: str
    unit_id: str
    tag_type: Optional[str] = None
    engineering_units: Optional[str] = None
    normal_range_min: Optional[float] = None
    normal_range_max: Optional[float] = None

class EquipmentInfo(BaseModel):
    equipment_id: str
    equipment_name: str
    equipment_type: str
    unit_id: str
    status: str = "OPERATIONAL"

# Conexión a DB
async def get_db():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        return None

# ========== ENDPOINTS EXISTENTES ==========

@app.get("/")
async def root():
    return {
        "status": "RefineryIQ API Running",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": ["kpis", "alerts", "maintenance", "energy", "demo", "normalized"]
    }

@app.get("/health")
async def health_check():
    try:
        conn = await get_db()
        if conn is None:
            return {"status": "unhealthy", "database": "disconnected"}
        await conn.execute("SELECT 1")
        await conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/api/data/ingest")
async def ingest_data(data: List[ProcessData]):
    """Endpoint para ingesta de datos de proceso"""
    conn = await get_db()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        inserted = 0
        async with conn.transaction():
            for record in data:
                await conn.execute('''
                    INSERT INTO process_data (timestamp, unit_id, tag_id, value, quality)
                    VALUES ($1, $2, $3, $4, $5)
                ''', record.timestamp, record.unit_id, record.tag_id, 
                   record.value, record.quality)
                inserted += 1
        
        return {"status": "success", "records_inserted": inserted}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        await conn.close()

@app.get("/api/kpis")
async def get_kpis():
    """Endpoint para KPIs dinámicos"""
    
    current_time = int(time.time())
    random.seed(current_time % 1000)
    
    # CDU-101: Variación suave
    cdu_efficiency = 85 + random.uniform(0, 5) + 2 * (random.random() - 0.5)
    
    # FCC-201: Más variable (simulando problemas)
    fcc_efficiency = 80 + random.uniform(0, 8)
    fcc_status = "warning" if fcc_efficiency < 83 else "normal"
    
    # HT-301: Muy estable
    ht_efficiency = 90 + random.uniform(0, 4)
    
    kpis = [
        {
            "unit_id": "CDU-101",
            "efficiency": round(cdu_efficiency, 1),
            "throughput": round(10000 + random.uniform(-500, 500)),
            "energy_consumption": round(45 + random.uniform(-2, 2), 1),
            "status": "normal",
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "unit_id": "FCC-201",
            "efficiency": round(fcc_efficiency, 1),
            "throughput": round(7500 + random.uniform(-300, 300)),
            "energy_consumption": round(65 + random.uniform(-5, 5), 1),
            "status": fcc_status,
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "unit_id": "HT-301",
            "efficiency": round(ht_efficiency, 1),
            "throughput": round(5200 + random.uniform(-200, 200)),
            "energy_consumption": round(32 + random.uniform(-1, 1), 1),
            "status": "normal",
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    ]
    return kpis
    
@app.get("/api/alerts")
async def get_alerts(acknowledged: bool = False):
    """Obtiene alertas del sistema"""
    try:
        conn = await get_db()
        if conn is None:
            # Si no hay conexión, devolver datos simulados
            raise Exception("No database connection")
        rows = await conn.fetch('''
            SELECT * FROM alerts 
            WHERE acknowledged = $1 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''', acknowledged)
        await conn.close()
        
        alerts = []
        for row in rows:
            alerts.append({
                "id": row['id'],
                "time": row['timestamp'].isoformat() if row['timestamp'] else None,
                "unit_id": row['unit_id'],
                "tag_id": row['tag_id'],
                "value": row['value'],
                "threshold": row['threshold'],
                "message": row['message'],
                "severity": row['severity'],
                "acknowledged": row['acknowledged']
            })
        
        return alerts
        
    except Exception as e:
        # En caso de error, devolver datos simulados
        print(f"Error obteniendo alertas: {e}")
        alerts = [
            {
                "id": 1,
                "time": datetime.now(timezone.utc).isoformat(),
                "unit_id": "FCC-201",
                "tag_id": "TEMP_REACTOR",
                "message": "Temperatura elevada en reactor",
                "severity": "high",
                "acknowledged": False
            },
            {
                "id": 2,
                "time": datetime.now(timezone.utc).isoformat(),
                "unit_id": "CDU-101",
                "tag_id": "PRESS_TOWER",
                "message": "Presión fuera de rango normal",
                "severity": "medium",
                "acknowledged": True
            }
        ]
        
        return [alert for alert in alerts if alert["acknowledged"] == acknowledged]

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    """Reconocer alerta"""
    try:
        conn = await get_db()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection failed")
        await conn.execute('''
            UPDATE alerts SET acknowledged = TRUE WHERE id = $1
        ''', alert_id)
        await conn.close()
        return {"status": "acknowledged", "alert_id": alert_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== NUEVOS ENDPOINTS: MANTENIMIENTO PREDICTIVO ==========

@app.post("/api/maintenance/train")
async def train_maintenance_models():
    """Entrena los modelos de mantenimiento predictivo"""
    try:
        conn = await get_db()
        if conn is None:
            return {
                "status": "error", 
                "message": "No database connection",
                "note": "Usando modelos simulados para demostración"
            }
        result = await pm_system.train_models(conn)
        await conn.close()
        return result
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e),
            "note": "Usando modelos simulados para demostración"
        }

@app.get("/api/maintenance/all")
async def get_all_equipment_health():
    """Obtiene estado de salud de todos los equipos"""
    try:
        conn = await get_db()
        if conn is None:
            raise Exception("No database connection")
        results = await pm_system.analyze_all_equipment(conn)
        await conn.close()
        return results
    except Exception as e:
        # Datos simulados en caso de error
        print(f"Error en mantenimiento predictivo: {e}")
        return [
            {
                "equipment_id": "PUMP-CDU-101",
                "equipment_type": "PUMP",
                "unit_id": "CDU-101",
                "failure_probability": round(random.uniform(5, 25), 1),
                "prediction": "OPERACIÓN NORMAL",
                "confidence": round(random.uniform(85, 97), 1),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recommendation": "PUMP OPERANDO NORMALMENTE - CONTINUAR MONITOREO"
            },
            {
                "equipment_id": "COMP-FCC-201",
                "equipment_type": "COMPRESSOR",
                "unit_id": "FCC-201",
                "failure_probability": round(random.uniform(60, 85), 1),
                "prediction": "FALLA INMINENTE",
                "confidence": round(random.uniform(75, 90), 1),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recommendation": "PROGRAMAR MANTENIMIENTO DE COMPRESSOR EN PRÓXIMAS 24H"
            },
            {
                "equipment_id": "VALVE-HT-301",
                "equipment_type": "VALVE",
                "unit_id": "HT-301",
                "failure_probability": round(random.uniform(20, 40), 1),
                "prediction": "OPERACIÓN NORMAL",
                "confidence": round(random.uniform(90, 98), 1),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recommendation": "VALVE OPERANDO NORMALMENTE - CONTINUAR MONITOREO"
            }
        ]

@app.get("/api/maintenance/recent")
async def get_recent_predictions(limit: int = 5):
    """Obtiene predicciones recientes"""
    try:
        conn = await get_db()
        if conn is None:
            raise Exception("No database connection")
        predictions = await pm_system.get_recent_predictions(conn, limit)
        await conn.close()
        return predictions
    except Exception as e:
        # Simular predicciones recientes
        all_data = await get_all_equipment_health()
        return all_data[:limit]

# ========== NUEVOS ENDPOINTS: OPTIMIZACIÓN ENERGÉTICA ==========

@app.get("/api/energy/analyze/{unit_id}")
async def analyze_energy(unit_id: str, hours: int = 24):
    """Analiza eficiencia energética de una unidad"""
    try:
        conn = await get_db()
        if conn is None:
            raise Exception("No database connection")
        analysis = await energy_system.analyze_unit_energy(conn, unit_id, hours)
        await conn.close()
        if analysis:
            return analysis
        else:
            return {"error": "No se pudo realizar el análisis"}
    except Exception as e:
        # Análisis simulado
        print(f"Error en análisis energético: {e}")
        benchmarks = {
            'CDU-101': {'energy_per_barrel': 45, 'target': 42},
            'FCC-201': {'energy_per_barrel': 65, 'target': 60},
            'HT-301': {'energy_per_barrel': 35, 'target': 32}
        }
        
        if unit_id not in benchmarks:
            return {"error": f"Unidad {unit_id} no encontrada"}
        
        benchmark = benchmarks[unit_id]['energy_per_barrel']
        target = benchmarks[unit_id]['target']
        avg_consumption = benchmark * (0.9 + random.random() * 0.2)
        
        return {
            'unit_id': unit_id,
            'analysis_date': datetime.now().date().isoformat(),
            'avg_energy_consumption': round(avg_consumption, 2),
            'benchmark': benchmark,
            'target': target,
            'efficiency_score': round((target / avg_consumption) * 100, 2),
            'status': 'NEEDS_IMPROVEMENT' if avg_consumption > benchmark else 'GOOD',
            'inefficiencies': [{
                'type': 'SIMULATED_DATA',
                'severity': 'LOW',
                'message': 'Usando datos simulados para demostración',
                'savings_potential': max(0, avg_consumption - target)
            }],
            'recommendations': [{
                'action': 'CONNECT_REAL_DATA',
                'priority': 'HIGH',
                'description': 'Conectar a fuentes de datos reales para análisis preciso',
                'expected_savings': '5-10%',
                'implementation_time': '2 semanas'
            }],
            'estimated_savings': round(max(0, avg_consumption - target), 2),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

@app.get("/api/energy/recent")
async def get_recent_energy_analysis(unit_id: str = None, limit: int = 3):
    """Obtiene análisis energéticos recientes"""
    try:
        conn = await get_db()
        if conn is None:
            raise Exception("No database connection")
        analyses = await energy_system.get_recent_analysis(conn, unit_id, limit)
        await conn.close()
        return analyses
    except Exception as e:
        # Simular análisis recientes
        units = ['CDU-101', 'FCC-201', 'HT-301'] if not unit_id else [unit_id]
        analyses = []
        for u in units:
            analysis = await analyze_energy(u, 24)
            analyses.append(analysis)
        return analyses[:limit]

# ========== NUEVOS ENDPOINTS: DEMOSTRACIÓN ==========

@app.post("/api/demo/generate-alert")
async def generate_demo_alert():
    """Genera una alerta de demostración"""
    try:
        conn = await get_db()
        if conn is None:
            return {
                "status": "simulated_alert",
                "alert": {
                    "id": 999,
                    "time": datetime.now(timezone.utc).isoformat(),
                    "unit_id": "FCC-201",
                    "tag_id": "TEMP_REACTOR",
                    "value": 525.5,
                    "threshold": 500.0,
                    "severity": "HIGH",
                    "message": "Temperatura crítica en reactor (simulada)",
                    "acknowledged": False
                }
            }
        
        units = ['CDU-101', 'FCC-201', 'HT-301']
        tags = ['TEMP_REACTOR', 'PRESS_TOWER', 'FLOW_FEED', 'LEVEL_TANK']
        messages = [
            "Temperatura crítica en reactor",
            "Presión fuera de rango operativo",
            "Flujo de alimentación bajo",
            "Nivel de tanque demasiado alto",
            "Vibración excesiva en bomba"
        ]
        
        alert = {
            "time": datetime.now(timezone.utc).isoformat(),
            "unit_id": random.choice(units),
            "tag_id": random.choice(tags),
            "value": round(random.uniform(50, 150), 1),
            "threshold": round(random.uniform(80, 120), 1),
            "severity": random.choice(['LOW', 'MEDIUM', 'HIGH']),
            "message": random.choice(messages),
            "acknowledged": False
        }
        
        await conn.execute('''
            INSERT INTO alerts (timestamp, unit_id, tag_id, value, threshold, severity, message, acknowledged)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ''', alert['time'], alert['unit_id'], alert['tag_id'], alert['value'], 
             alert['threshold'], alert['severity'], alert['message'], alert['acknowledged'])
        
        await conn.close()
        
        return {"status": "alert_generated", "alert": alert}
        
    except Exception as e:
        print(f"Error generando alerta demo: {e}")
        return {
            "status": "simulated_alert",
            "alert": {
                "id": 999,
                "time": datetime.now(timezone.utc).isoformat(),
                "unit_id": "FCC-201",
                "tag_id": "TEMP_REACTOR",
                "value": 525.5,
                "threshold": 500.0,
                "severity": "HIGH",
                "message": "Temperatura crítica en reactor (simulada)",
                "acknowledged": False
            }
        }

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Estadísticas para el dashboard"""
    return {
        "total_units": 3,
        "active_alerts": 2,
        "avg_efficiency": 86.7,
        "energy_savings_potential": 14500,
        "predictive_maintenance_active": True,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

# ========== NUEVOS ENDPOINTS: BASE DE DATOS NORMALIZADA ==========

@app.get("/api/normalized/units")
async def get_all_units():
    """Obtener todas las unidades de proceso"""
    try:
        conn = await get_db()
        rows = await conn.fetch('SELECT * FROM process_units ORDER BY unit_id')
        await conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/normalized/tags")
async def get_all_tags(unit_id: Optional[str] = None):
    """Obtener tags/variables"""
    try:
        conn = await get_db()
        if unit_id:
            rows = await conn.fetch('SELECT * FROM process_tags WHERE unit_id = $1 ORDER BY tag_id', unit_id)
        else:
            rows = await conn.fetch('SELECT * FROM process_tags ORDER BY unit_id, tag_id')
        await conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/normalized/equipment")
async def get_all_equipment(unit_id: Optional[str] = None):
    """Obtener equipos"""
    try:
        conn = await get_db()
        if unit_id:
            rows = await conn.fetch('SELECT * FROM equipment WHERE unit_id = $1 ORDER BY equipment_id', unit_id)
        else:
            rows = await conn.fetch('SELECT * FROM equipment ORDER BY unit_id, equipment_type')
        await conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/normalized/process-data/enriched")
async def get_enriched_process_data(
    unit_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    limit: int = 100,
    hours: Optional[int] = None
):
    """Obtener datos de proceso enriquecidos con nombres descriptivos"""
    try:
        conn = await get_db()
        query = "SELECT * FROM process_data_enriched WHERE 1=1"
        params = []
        param_count = 0
        
        if unit_id:
            param_count += 1
            query += f" AND unit_id = ${param_count}"
            params.append(unit_id)
        
        if tag_id:
            param_count += 1
            query += f" AND tag_id = ${param_count}"
            params.append(tag_id)
        
        if hours:
            param_count += 1
            query += f" AND timestamp > NOW() - INTERVAL '${param_count} hours'"
            params.append(hours)
        
        param_count += 1
        query += f" ORDER BY timestamp DESC LIMIT ${param_count}"
        params.append(limit)
        
        rows = await conn.fetch(query, *params)
        await conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/normalized/alerts/enriched")
async def get_enriched_alerts(acknowledged: bool = False, limit: int = 20):
    """Obtener alertas enriquecidas con información adicional"""
    try:
        conn = await get_db()
        rows = await conn.fetch('''
            SELECT * FROM alerts_enriched 
            WHERE acknowledged = $1
            ORDER BY timestamp DESC 
            LIMIT $2
        ''', acknowledged, limit)
        await conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/normalized/energy/enriched")
async def get_enriched_energy_analysis(unit_id: Optional[str] = None, limit: int = 10):
    """Obtener análisis de energía enriquecido"""
    try:
        conn = await get_db()
        if unit_id:
            rows = await conn.fetch('''
                SELECT * FROM energy_analysis_enriched 
                WHERE unit_id = $1
                ORDER BY analysis_date DESC 
                LIMIT $2
            ''', unit_id, limit)
        else:
            rows = await conn.fetch('''
                SELECT * FROM energy_analysis_enriched 
                ORDER BY analysis_date DESC, unit_id 
                LIMIT $1
            ''', limit)
        await conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/normalized/stats")
async def get_normalized_stats():
    """Estadísticas de la base de datos normalizada"""
    try:
        conn = await get_db()
        stats = {}
        
        stats['total_units'] = await conn.fetchval("SELECT COUNT(*) FROM process_units")
        stats['active_units'] = await conn.fetchval("SELECT COUNT(*) FROM process_units WHERE status = 'ACTIVE'")
        stats['total_tags'] = await conn.fetchval("SELECT COUNT(*) FROM process_tags")
        stats['total_equipment'] = await conn.fetchval("SELECT COUNT(*) FROM equipment")
        stats['operational_equipment'] = await conn.fetchval("SELECT COUNT(*) FROM equipment WHERE status = 'OPERATIONAL'")
        stats['total_process_records'] = await conn.fetchval("SELECT COUNT(*) FROM process_data")
        
        try:
            stats['process_records_today'] = await conn.fetchval("""
                SELECT COUNT(*) FROM process_data 
                WHERE timestamp > CURRENT_DATE
            """)
        except:
            stats['process_records_today'] = 0
        
        stats['total_alerts'] = await conn.fetchval("SELECT COUNT(*) FROM alerts")
        stats['active_alerts'] = await conn.fetchval("SELECT COUNT(*) FROM alerts WHERE acknowledged = FALSE")
        
        await conn.close()
        stats['last_updated'] = datetime.now(timezone.utc).isoformat()
        stats['database_normalized'] = True
        return stats
        
    except Exception as e:
        return {"error": str(e), "database_normalized": False}



# ==========================================
# 🚀 ENDPOINTS PROFESIONALES (CONECTADOS A BD)
# ==========================================

@app.get("/api/maintenance/predictions")
async def get_maintenance_predictions():
    """Obtiene predicciones reales de ML desde la BD"""
    try:
        conn = await get_db()
        # Usamos JOIN para traer nombres reales de equipos
        query = '''
            SELECT 
                mp.equipment_id,
                e.equipment_name,
                mp.failure_probability,
                mp.prediction,
                mp.recommendation,
                mp.timestamp
            FROM maintenance_predictions mp
            JOIN equipment e ON mp.equipment_id = e.equipment_id
            ORDER BY mp.timestamp DESC
            LIMIT 10
        '''
        rows = await conn.fetch(query)
        await conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error Maintenance: {e}")
        return []

@app.get("/api/energy/analysis")
async def get_energy_analysis():
    """Obtiene análisis energético desde la vista enriquecida"""
    try:
        conn = await get_db()
        # Consultamos la vista que arreglamos anteriormente
        query = '''
            SELECT * FROM energy_analysis_enriched
            ORDER BY analysis_date DESC, unit_id
            LIMIT 5
        '''
        rows = await conn.fetch(query)
        await conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error Energy: {e}")
        return []

@app.get("/api/alerts/history")
async def get_alerts_history():
    """Obtiene historial completo de alertas para la tabla"""
    try:
        conn = await get_db()
        query = '''
            SELECT * FROM alerts_enriched
            ORDER BY timestamp DESC
            LIMIT 50
        '''
        rows = await conn.fetch(query)
        await conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error Alerts: {e}")
        return []



# ==========================================
# 🧠 ANALÍTICA AVANZADA & HISTÓRICOS
# ==========================================

@app.get("/api/dashboard/history")
async def get_dashboard_history():
    """Obtiene tendencia histórica real de KPIs (últimas 24h)"""
    try:
        conn = await get_db()
        # Promedio horario de eficiencia y producción
        query = '''
            SELECT 
                to_char(date_trunc('hour', timestamp), 'HH24:00') as time_label,
                ROUND(AVG(energy_efficiency)::numeric, 1) as efficiency,
                ROUND(AVG(throughput)::numeric, 0) as production
            FROM kpis
            WHERE timestamp >= NOW() - INTERVAL '24 HOURS'
            GROUP BY 1
            ORDER BY 1 ASC
        '''
        rows = await conn.fetch(query)
        await conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error History: {e}")
        return []

@app.get("/api/stats/advanced")
async def get_advanced_stats():
    """Calcula métricas de ingeniería complejas (OEE, Estabilidad, Costos)"""
    try:
        conn = await get_db()
        
        # 1. Calcular OEE (Overall Equipment Effectiveness) Global
        # OEE = Disponibilidad * Rendimiento * Calidad
        # Simplificación: Usamos promedios de KPIs existentes
        oee_data = await conn.fetchrow('''
            SELECT 
                AVG(quality_score) as quality,
                AVG(maintenance_score) as availability,
                (AVG(throughput) / 12000.0 * 100) as performance -- Asumiendo capacidad max 12k
            FROM kpis
            WHERE timestamp >= NOW() - INTERVAL '24 HOURS'
        ''')
        
        quality = oee_data['quality'] or 0
        avail = oee_data['availability'] or 0
        perf = min(100, oee_data['performance'] or 0)
        oee_score = (quality * avail * perf) / 10000.0

        # 2. Calcular Estabilidad del Proceso (Basado en variabilidad de sensores)
        # Menor desviación estándar = Mayor estabilidad
        stability_data = await conn.fetchrow('''
            SELECT STDDEV(value) as variability
            FROM process_data
            WHERE timestamp >= NOW() - INTERVAL '4 HOURS'
        ''')
        variability = stability_data['variability'] or 100
        stability_index = max(0, min(100, 100 - (variability / 5))) # Normalización simple

        # 3. Costo de Ineficiencia Energética
        # Suma de (Consumo - Benchmark) * Costo Energía ($0.12/kWh por ejemplo)
        cost_data = await conn.fetchrow('''
            SELECT SUM(estimated_savings) as total_waste_kwh
            FROM energy_analysis
            WHERE analysis_date = CURRENT_DATE
        ''')
        waste_kwh = cost_data['total_waste_kwh'] or 0
        daily_loss = waste_kwh * 0.12 # Precio hipotético del kWh industrial

        await conn.close()
        
        return {
            "oee": {
                "score": round(oee_score, 1),
                "quality": round(quality, 1),
                "availability": round(avail, 1),
                "performance": round(perf, 1)
            },
            "stability": {
                "index": round(stability_index, 1),
                "trend": "stable" if stability_index > 80 else "unstable"
            },
            "financial": {
                "daily_loss_usd": round(daily_loss, 2),
                "potential_annual_savings": round(daily_loss * 365, 0)
            }
        }
        
    except Exception as e:
        print(f"Error Advanced Stats: {e}")
        return {"error": str(e)}



# ==========================================
# 🛠️ GESTIÓN DE ACTIVOS & ESTABILIDAD V2
# ==========================================

@app.get("/api/assets/overview")
async def get_assets_overview():
    """Obtiene estado completo de equipos con sus últimas lecturas"""
    try:
        conn = await get_db()
        # Query compleja para unir Equipos -> Tags -> Último Valor
        query = '''
            SELECT 
                e.equipment_id,
                e.equipment_name,
                e.equipment_type,
                e.status as equipment_status,
                e.unit_id,
                json_agg(json_build_object(
                    'tag_name', pt.tag_name, 
                    'value', pd.value, 
                    'units', pt.engineering_units
                )) as sensors
            FROM equipment e
            LEFT JOIN process_tags pt ON pt.unit_id = e.unit_id 
                -- Relación heurística simple: Tags de la misma unidad
            LEFT JOIN LATERAL (
                SELECT value FROM process_data 
                WHERE tag_id = pt.tag_id 
                ORDER BY timestamp DESC LIMIT 1
            ) pd ON true
            GROUP BY e.equipment_id, e.equipment_name, e.equipment_type, e.status, e.unit_id
            ORDER BY e.unit_id, e.equipment_name
        '''
        rows = await conn.fetch(query)
        
        # Procesar para que el JSON sea compatible
        results = []
        for row in rows:
            # Filtramos sensores nulos
            sensors = [s for s in json.loads(row['sensors']) if s['value'] is not None]
            # Seleccionamos solo 2-3 sensores relevantes para no saturar la vista
            results.append({
                **dict(row),
                'sensors': sensors[:3] 
            })
            
        await conn.close()
        return results
    except Exception as e:
        print(f"Error Assets: {e}")
        return []

# PATCH: Corrección de Estabilidad (Reemplaza la lógica anterior en /api/stats/advanced)
# Buscamos en el código si ya existe la función y la reemplazamos mentalmente
# (Nota: En este script simplificado, inyectamos una función auxiliar de cálculo)

async def calculate_stability_v2(conn):
    # Usamos Coeficiente de Variación (StdDev / Promedio) para normalizar escalas
    # Esto evita que un Flujo de 10,000 rompa la escala comparado con una Temp de 50
    data = await conn.fetch('''
        WITH Stats AS (
            SELECT 
                tag_id, 
                AVG(value) as avg_val, 
                STDDEV(value) as std_val
            FROM process_data
            WHERE timestamp >= NOW() - INTERVAL '4 HOURS'
            GROUP BY tag_id
        )
        SELECT AVG(CASE WHEN avg_val = 0 THEN 0 ELSE (std_val / avg_val) END) as cv
        FROM Stats
    ''')
    
    avg_cv = data[0]['cv'] or 0
    # Si la variación promedio es 0%, estabilidad 100. Si es 20%, estabilidad 0.
    stability_index = max(0, min(100, 100 - (avg_cv * 500))) 
    return round(stability_index, 1)



# ==========================================
# 📦 SUMINISTROS, REPORTES Y SEGURIDAD
# ==========================================

from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(creds: LoginRequest):
    """Simula autenticación segura"""
    # En producción esto iría contra una tabla de usuarios con hash
    if creds.username == "admin" and creds.password == "admin123":
        return {"token": "fake-jwt-token-123", "user": "Administrador", "role": "admin"}
    elif creds.username == "operador" and creds.password == "1234":
        return {"token": "fake-jwt-token-456", "user": "Operador Turno", "role": "operator"}
    else:
        # Retornar error 401
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

@app.get("/api/supplies/data")
async def get_supplies_data():
    """Obtiene estado de tanques e inventario"""
    try:
        conn = await get_db()
        tanks = await conn.fetch("SELECT * FROM tanks ORDER BY name")
        inv = await conn.fetch("SELECT * FROM inventory ORDER BY quantity ASC") # Prioridad a los bajos
        await conn.close()
        return {
            "tanks": [dict(t) for t in tanks],
            "inventory": [dict(i) for i in inv]
        }
    except Exception as e:
        print(f"Error Supplies: {e}")
        return {"tanks": [], "inventory": []}

from fastapi.responses import HTMLResponse
# --- BUSCA ESTA SECCIÓN EN main.py Y REEMPLÁZALA ---

from datetime import datetime

@app.get("/api/reports/daily", response_class=HTMLResponse)
async def generate_daily_report():
    """Genera un reporte PDF oficial con datos REALES de la BD"""
    try:
        conn = await get_db()
        
        # 1. Consultar Datos Reales
        # KPIs del día
        kpis = await conn.fetch("SELECT * FROM kpis ORDER BY timestamp DESC LIMIT 3")
        
        # Alertas recientes
        alerts = await conn.fetch("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 5")
        
        # Estado de Tanques
        tanks = await conn.fetch("SELECT * FROM tanks ORDER BY name")
        
        await conn.close()

        # 2. Calcular Resúmenes
        avg_efficiency = sum([k['energy_efficiency'] for k in kpis]) / len(kpis) if kpis else 0
        total_production = sum([k['throughput'] for k in kpis]) if kpis else 0
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")

        # 3. Construir HTML Profesional (Estilo Papel A4)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reporte Operativo - {date_str}</title>
            <style>
                @page {{ size: A4; margin: 2cm; }}
                body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #333; line-height: 1.4; font-size: 12px; }}
                
                /* Encabezado */
                .header {{ border-bottom: 2px solid #1e3a8a; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #1e3a8a; }}
                .meta {{ text-align: right; font-size: 10px; color: #666; }}
                
                /* Secciones */
                h2 {{ background: #f1f5f9; padding: 8px 12px; border-left: 5px solid #3b82f6; font-size: 14px; margin-top: 25px; color: #1e293b; }}
                
                /* Tablas */
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th {{ background-color: #f8fafc; text-align: left; padding: 8px; border: 1px solid #e2e8f0; font-size: 11px; }}
                td {{ padding: 8px; border: 1px solid #e2e8f0; font-size: 11px; }}
                
                /* Estados */
                .badge {{ padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px; }}
                .ok {{ background: #ecfdf5; color: #047857; }}
                .warn {{ background: #fffbeb; color: #b45309; }}
                .danger {{ background: #fef2f2; color: #b91c1c; }}

                /* Pie de página y Firmas */
                .signatures {{ margin-top: 60px; display: flex; justify-content: space-between; page-break-inside: avoid; }}
                .sig-box {{ width: 40%; border-top: 1px solid #333; padding-top: 10px; text-align: center; font-size: 11px; }}
                
                .footer {{ margin-top: 40px; text-align: center; font-size: 9px; color: #999; border-top: 1px solid #eee; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">REFINERY IQ</div>
                <div class="meta">
                    <strong>REPORTE DIARIO DE OPERACIONES</strong><br>
                    ID Documento: RPT-{int(datetime.now().timestamp())}<br>
                    Fecha de Emisión: {date_str}<br>
                    Planta: Complejo Maturín
                </div>
            </div>

            <div style="background: #eff6ff; padding: 15px; border-radius: 6px; border: 1px solid #dbeafe;">
                <strong>Resumen Ejecutivo:</strong><br>
                La planta opera con una eficiencia promedio del <strong>{avg_efficiency:.1f}%</strong>. 
                El volumen procesado en el último corte es de <strong>{total_production:,.0f} barriles</strong>.
                Se requiere atención en <strong>{len(alerts)} alertas recientes</strong>.
            </div>

            <h2>1. BALANCE DE PRODUCCIÓN (KPIs)</h2>
            <table>
                <thead>
                    <tr><th>Hora</th><th>Unidad</th><th>Eficiencia</th><th>Producción (bbl)</th><th>Calidad</th></tr>
                </thead>
                <tbody>
                    {''.join([f"<tr><td>{row['timestamp'].strftime('%H:%M')}</td><td>{row['unit_id']}</td><td>{row['energy_efficiency']:.1f}%</td><td>{row['throughput']:.0f}</td><td>{row['quality_score']:.1f}</td></tr>" for row in kpis])}
                </tbody>
            </table>

            <h2>2. NIVELES DE SUMINISTRO (TANQUES)</h2>
            <table>
                <thead>
                    <tr><th>Tanque</th><th>Producto</th><th>Nivel Actual</th><th>Capacidad</th><th>Estado</th></tr>
                </thead>
                <tbody>
                    {''.join([f"<tr><td>{t['name']}</td><td>{t['product']}</td><td>{t['current_level']:,.0f} L</td><td>{t['capacity']:,.0f} L</td><td><span class='badge {'ok' if t['status']=='STATIC' else 'warn'}'>{t['status']}</span></td></tr>" for t in tanks])}
                </tbody>
            </table>

            <h2>3. BITÁCORA DE ALERTAS RECIENTES</h2>
            <table>
                <thead>
                    <tr><th>Hora</th><th>Unidad</th><th>Severidad</th><th>Mensaje</th></tr>
                </thead>
                <tbody>
                    {''.join([f"<tr><td>{a['timestamp'].strftime('%H:%M:%S')}</td><td>{a['unit_id']}</td><td><span class='badge {'danger' if a['severity']=='HIGH' else 'warn'}'>{a['severity']}</span></td><td>{a['message']}</td></tr>" for a in alerts])}
                </tbody>
            </table>

            <div class="signatures">
                <div class="sig-box">
                    <strong>Ing. Carlos D.</strong><br>
                    Gerente de Planta
                </div>
                <div class="sig-box">
                    <strong>Supervisión de Turno</strong><br>
                    Firma y Sello
                </div>
            </div>

            <div class="footer">
                Generado automáticamente por el sistema RefineryIQ v3.0 | Confidencial<br>
                Este documento es un registro oficial de operaciones.
            </div>

            <script>
                window.onload = function() {{ window.print(); }}
            </script>
        </body>
        </html>
        """
        return html_content

    except Exception as e:
        return HTMLResponse(content=f"Error generando reporte: {str(e)}", status_code=500)

if __name__ == "__main__":
    # Imprimimos localhost para no confundir
    print("\n" + "="*60)
    print("🚀 REFINERYIQ BACKEND - INICIANDO MODO LOCAL")
    print("="*60)
    print("Docs: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)