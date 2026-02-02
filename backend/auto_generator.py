import os
import random
import time
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, OperationalError

# ==============================================================================
# 1. CONFIGURACIÓN DEL SISTEMA DE SIMULACIÓN Y LOGGING
# ==============================================================================

# Configuración de Logs para depuración profunda
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SIMULATOR] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("RefineryIQ_Generator")

# Detectar URL de Base de Datos (Compatible con Render y Local)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:307676@localhost:5432/refineryiq")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Motor de conexión síncrono (Vital para operaciones DDL)
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
except Exception as e:
    logger.critical(f"No se pudo crear el motor de base de datos: {e}")
    exit(1)

# ==============================================================================
# 2. DEFINICIÓN DE CATÁLOGOS MAESTROS (DATA FACTORY)
# ==============================================================================

# Unidades de Proceso (La estructura base de la refinería)
UNITS_CONFIG = [
    {"id": "CDU-101", "name": "Destilación Atmosférica", "type": "DISTILLATION", "desc": "Separación primaria de crudo en fracciones."},
    {"id": "FCC-201", "name": "Craqueo Catalítico Fluidizado", "type": "CRACKING", "desc": "Conversión de hidrocarburos pesados en gasolina."},
    {"id": "HT-305", "name": "Hidrotratamiento Diesel", "type": "TREATING", "desc": "Eliminación de azufre y contaminantes."},
    {"id": "ALK-400", "name": "Unidad de Alquilación", "type": "ALKYLATION", "desc": "Producción de componentes de alto octanaje."}
]

# Equipos Industriales (Activos físicos)
EQUIPMENT_CONFIG = [
    {"id": "PUMP-101", "name": "Bomba Alim. Crudo", "type": "PUMP", "unit": "CDU-101"},
    {"id": "FURNACE-100", "name": "Horno de Precalentamiento", "type": "FURNACE", "unit": "CDU-101"},
    {"id": "TOWER-101", "name": "Torre Fraccionadora", "type": "TOWER", "unit": "CDU-101"},
    {"id": "COMP-201", "name": "Compresor Gas Húmedo", "type": "COMPRESSOR", "unit": "FCC-201"},
    {"id": "REACT-202", "name": "Reactor Riser", "type": "REACTOR", "unit": "FCC-201"},
    {"id": "REGEN-203", "name": "Regenerador Catalizador", "type": "VESSEL", "unit": "FCC-201"},
    {"id": "PUMP-305", "name": "Bomba Carga Diesel", "type": "PUMP", "unit": "HT-305"},
    {"id": "EXCH-306", "name": "Intercambiador Calor", "type": "EXCHANGER", "unit": "HT-305"},
    {"id": "VALVE-401", "name": "Válvula Control Ácido", "type": "VALVE", "unit": "ALK-400"}
]

# Tags / Sensores (Variables de proceso) - CORREGIDO: usamos min_val y max_val
TAGS_CONFIG = [
    {"id": "TI-101", "name": "Temp. Salida Horno", "unit": "CDU-101", "uom": "°C", "min_val": 340, "max_val": 360},
    {"id": "FI-102", "name": "Flujo Carga Crudo", "unit": "CDU-101", "uom": "bpd", "min_val": 9800, "max_val": 10200},
    {"id": "PI-103", "name": "Presión Torre", "unit": "CDU-101", "uom": "psig", "min_val": 15, "max_val": 25},
    {"id": "PI-201", "name": "Presión Reactor", "unit": "FCC-201", "uom": "psig", "min_val": 28, "max_val": 32},
    {"id": "TI-203", "name": "Temp. Regenerador", "unit": "FCC-201", "uom": "°C", "min_val": 680, "max_val": 720},
    {"id": "LI-305", "name": "Nivel Separador", "unit": "HT-305", "uom": "%", "min_val": 45, "max_val": 55},
    {"id": "TI-306", "name": "Temp. Reacción HDS", "unit": "HT-305", "uom": "°C", "min_val": 320, "max_val": 350},
    {"id": "AI-400", "name": "Concentración Ácido", "unit": "ALK-400", "uom": "%", "min_val": 88, "max_val": 92},
    {"id": "FI-402", "name": "Flujo Isobutano", "unit": "ALK-400", "uom": "bpd", "min_val": 4000, "max_val": 4500}
]

# Tanques y Productos (Logística)
TANK_PRODUCTS = {
    "TK-101": {"prod": "Crudo Pesado Maya", "cap": 80000},
    "TK-102": {"prod": "Gasolina Magna 87", "cap": 45000},
    "TK-201": {"prod": "Diesel UBA", "cap": 50000},
    "TK-305": {"prod": "Agua de Proceso", "cap": 20000},
    "TK-400": {"prod": "Alquilado", "cap": 15000}
}

# Inventario (Almacén) - CORREGIDO: usamos 'quantity' en lugar de 'qty'
INVENTORY_ITEMS = [
    {"item": "Catalizador FCC-ZSM5", "sku": "CAT-ZSM5", "quantity": 1500, "unit": "kg"},
    {"item": "Inhibidor de Corrosión", "sku": "CHEM-CORR-01", "quantity": 800, "unit": "L"},
    {"item": "Sosa Cáustica 50%", "sku": "CHEM-NAOH", "quantity": 2000, "unit": "L"},
    {"item": "Aceite Lubricante ISO-68", "sku": "LUB-ISO68", "quantity": 45, "unit": "tambor"},
    {"item": "Empaques Espirales 4\"", "sku": "GSK-SP-04", "quantity": 120, "unit": "pza"},
    {"item": "Válvula de Seguridad 2\"", "sku": "PSV-02-CS", "quantity": 5, "unit": "pza"}
]

# ==============================================================================
# 3. MOTOR DE RECONSTRUCCIÓN DE BASE DE DATOS (AUTO-HEALING V8.0)
# ==============================================================================

def validate_and_repair_schema():
    """
    Función Nuclear: Verifica tabla por tabla. Si falta una columna crítica,
    DESTRUYE la tabla y la vuelve a crear. Esto garantiza que el esquema
    sea 100% compatible con el código actual.
    """
    logger.info("🔧 Iniciando validación profunda del esquema de base de datos...")
    
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            # --- 1. REPARACIÓN: INVENTORY (Error: column "item" does not exist) ---
            try:
                # Intentamos leer la columna conflictiva
                conn.execute(text("SELECT item FROM inventory LIMIT 1"))
            except (ProgrammingError, OperationalError) as e:
                logger.warning(f"⚠️ Tabla 'inventory' corrupta (Falta columna 'item'). Reconstruyendo... Error: {e}")
                transaction.rollback()
                transaction = conn.begin()
                conn.execute(text("DROP TABLE IF EXISTS inventory CASCADE"))
                conn.execute(text("""
                    CREATE TABLE inventory (
                        id SERIAL PRIMARY KEY,
                        item TEXT NOT NULL,
                        sku TEXT,
                        quantity FLOAT,
                        unit TEXT,
                        status TEXT,
                        location TEXT DEFAULT 'Almacén Central',
                        last_updated TIMESTAMP DEFAULT NOW()
                    )
                """))
                logger.info("✅ Tabla 'inventory' reconstruida exitosamente.")

            # --- 2. REPARACIÓN: PROCESS_TAGS (Error: column "min_val" does not exist) ---
            try:
                conn.execute(text("SELECT min_val FROM process_tags LIMIT 1"))
            except (ProgrammingError, OperationalError) as e:
                logger.warning(f"⚠️ Tabla 'process_tags' corrupta (Faltan límites). Reconstruyendo... Error: {e}")
                transaction.rollback()
                transaction = conn.begin()
                conn.execute(text("DROP TABLE IF EXISTS process_tags CASCADE"))
                conn.execute(text("""
                    CREATE TABLE process_tags (
                        tag_id TEXT PRIMARY KEY,
                        tag_name TEXT,
                        unit_id TEXT,
                        engineering_units TEXT,
                        min_val FLOAT,
                        max_val FLOAT,
                        description TEXT
                    )
                """))
                logger.info("✅ Tabla 'process_tags' reconstruida exitosamente.")

            # --- 3. REPARACIÓN: PROCESS_UNITS (Error: column "description" does not exist) ---
            try:
                conn.execute(text("SELECT description FROM process_units LIMIT 1"))
            except (ProgrammingError, OperationalError) as e:
                logger.warning(f"⚠️ Tabla 'process_units' obsoleta. Migrando... Error: {e}")
                transaction.rollback()
                transaction = conn.begin()
                # Aquí podemos usar ALTER TABLE en lugar de DROP
                conn.execute(text("ALTER TABLE process_units ADD COLUMN IF NOT EXISTS description TEXT"))
                logger.info("✅ Tabla 'process_units' migrada.")

            # --- 4. REPARACIÓN: ENERGY_ANALYSIS (Error: column "consumption_kwh" missing) ---
            try:
                conn.execute(text("SELECT consumption_kwh FROM energy_analysis LIMIT 1"))
            except (ProgrammingError, OperationalError) as e:
                logger.warning(f"⚠️ Tabla 'energy_analysis' obsoleta. Reconstruyendo... Error: {e}")
                transaction.rollback()
                transaction = conn.begin()
                conn.execute(text("DROP TABLE IF EXISTS energy_analysis CASCADE"))
                conn.execute(text("""
                    CREATE TABLE energy_analysis (
                        id SERIAL PRIMARY KEY,
                        unit_id TEXT,
                        efficiency_score FLOAT,
                        consumption_kwh FLOAT,
                        savings_potential FLOAT,
                        recommendation TEXT,
                        analysis_date TIMESTAMP DEFAULT NOW(),
                        status TEXT
                    )
                """))
                logger.info("✅ Tabla 'energy_analysis' reconstruida.")

            # --- 5. REPARACIÓN: TANKS (Error: column "last_updated" does not exist) ---
            try:
                conn.execute(text("SELECT last_updated FROM tanks LIMIT 1"))
            except (ProgrammingError, OperationalError) as e:
                logger.warning(f"⚠️ Tabla 'tanks' corrupta. Reconstruyendo... Error: {e}")
                transaction.rollback()
                transaction = conn.begin()
                conn.execute(text("DROP TABLE IF EXISTS tanks CASCADE"))
                conn.execute(text("""
                    CREATE TABLE tanks (
                        id SERIAL PRIMARY KEY,
                        name TEXT,
                        product TEXT,
                        capacity FLOAT,
                        current_level FLOAT,
                        status TEXT,
                        last_updated TIMESTAMP DEFAULT NOW()
                    )
                """))
                logger.info("✅ Tabla 'tanks' reconstruida exitosamente.")
            
            # Confirmar cambios de estructura
            transaction.commit()
            logger.info("✅ Esquema de base de datos validado y reparado.")
            
        except Exception as e:
            logger.error(f"❌ Error crítico durante la reparación del esquema: {e}")
            transaction.rollback()
            raise e

# ==============================================================================
# 4. POBLADO DE DATOS MAESTROS (MASTER DATA)
# ==============================================================================

def seed_master_data(conn):
    """Inserta los datos estáticos (Unidades, Equipos, Tags, Inventario Base)"""
    logger.info("🌱 Sembrando datos maestros...")
    
    # 1. Unidades
    for u in UNITS_CONFIG:
        conn.execute(text("""
            INSERT INTO process_units (unit_id, name, type, description)
            VALUES (:uid, :name, :type, :desc)
            ON CONFLICT (unit_id) DO UPDATE SET 
                name = EXCLUDED.name, 
                description = EXCLUDED.description
        """), {"uid": u["id"], "name": u["name"], "type": u["type"], "desc": u["desc"]})

    # 2. Equipos
    for eq in EQUIPMENT_CONFIG:
        conn.execute(text("""
            INSERT INTO equipment (equipment_id, equipment_name, equipment_type, unit_id, status)
            VALUES (:id, :name, :type, :unit, 'OPERATIONAL')
            ON CONFLICT (equipment_id) DO UPDATE SET 
                equipment_name = EXCLUDED.equipment_name,
                unit_id = EXCLUDED.unit_id
        """), eq)

    # 3. Tags (Sensores) - CORREGIDO: usamos min_val y max_val
    for tag in TAGS_CONFIG:
        conn.execute(text("""
            INSERT INTO process_tags (tag_id, tag_name, unit_id, engineering_units, min_val, max_val)
            VALUES (:id, :name, :unit, :uom, :min_val, :max_val)
            ON CONFLICT (tag_id) DO UPDATE SET 
                min_val = EXCLUDED.min_val,
                max_val = EXCLUDED.max_val
        """), {
            "id": tag["id"], 
            "name": tag["name"], 
            "unit": tag["unit"], 
            "uom": tag["uom"], 
            "min_val": tag["min_val"], 
            "max_val": tag["max_val"]
        })

    # 4. Inventario (Fix para "Producto Desconocido")
    for inv in INVENTORY_ITEMS:
        # Verificamos si existe por SKU
        exists = conn.execute(text("SELECT id FROM inventory WHERE sku = :sku"), {"sku": inv["sku"]}).scalar()
        if not exists:
            conn.execute(text("""
                INSERT INTO inventory (item, sku, quantity, unit, status)
                VALUES (:item, :sku, :quantity, :unit, 'OK')
            """), {
                "item": inv["item"], 
                "sku": inv["sku"], 
                "quantity": inv["quantity"], 
                "unit": inv["unit"]
            })

# ==============================================================================
# 5. SIMULACIÓN FÍSICA Y TRANSACCIONAL (DYNAMIC DATA)
# ==============================================================================

def simulate_process_dynamics(conn):
    """Genera datos de sensores, KPIs y movimiento de tanques."""
    logger.info("⚡ Simulando dinámica de planta...")
    
    # A. Sensores (Process Data)
    for tag in TAGS_CONFIG:
        # Generar valor con ruido gaussiano
        center = (tag["min_val"] + tag["max_val"]) / 2
        sigma = (tag["max_val"] - tag["min_val"]) / 6
        val = random.gauss(center, sigma)
        
        conn.execute(text("""
            INSERT INTO process_data (timestamp, unit_id, tag_id, value, quality)
            VALUES (:ts, :uid, :tid, :val, 192)
        """), {
            "ts": datetime.now(), 
            "uid": tag["unit"], 
            "tid": tag["id"], 
            "val": round(val, 2)
        })

    # B. KPIs de Producción (Dashboard)
    for u in UNITS_CONFIG:
        # Eficiencia aleatoria pero alta
        eff = min(99.9, max(75.0, random.gauss(92, 3)))
        thru = (eff / 100) * 12000 * random.uniform(0.95, 1.05)
        
        conn.execute(text("""
            INSERT INTO kpis (timestamp, unit_id, energy_efficiency, throughput, quality_score, maintenance_score)
            VALUES (:ts, :uid, :eff, :th, 99.2, 96.5)
        """), {
            "ts": datetime.now(), 
            "uid": u["id"], 
            "eff": round(eff, 2), 
            "th": round(thru, 0)
        })

    # C. Dinámica de Tanques (Suben y bajan suavemente)
    # Primero verifica si hay tanques, si no, créalos
    tanks = conn.execute(text("SELECT id, name, capacity, current_level, status FROM tanks")).fetchall()
    if not tanks:
        # Inicializar si vacío
        for name, info in TANK_PRODUCTS.items():
            conn.execute(text("""
                INSERT INTO tanks (name, product, capacity, current_level, status, last_updated)
                VALUES (:n, :p, :c, :l, 'STABLE', NOW())
                ON CONFLICT (name) DO UPDATE SET
                    current_level = EXCLUDED.current_level,
                    status = EXCLUDED.status,
                    last_updated = EXCLUDED.last_updated
            """), {
                "n": name, 
                "p": info['prod'], 
                "c": info['cap'], 
                "l": info['cap']*0.6
            })
    else:
        for t in tanks:
            tid, tname, cap, level, status = t
            delta = cap * 0.015 # 1.5% de cambio
            
            new_lvl = level
            new_status = status
            
            if status == 'FILLING':
                new_lvl += delta
                if new_lvl >= cap * 0.95: 
                    new_status = 'DRAINING'
            elif status == 'DRAINING':
                new_lvl -= delta
                if new_lvl <= cap * 0.1: 
                    new_status = 'FILLING'
            else:
                if random.random() > 0.7: 
                    new_status = 'FILLING'
            
            new_lvl = max(0, min(new_lvl, cap))
            conn.execute(text("""
                UPDATE tanks SET current_level = :l, status = :s, last_updated = NOW() 
                WHERE id = :id
            """), {
                "l": new_lvl, 
                "s": new_status, 
                "id": tid
            })

def manage_alerts_lifecycle(conn):
    """
    Ciclo de vida de alertas:
    1. Reconoce automáticamente alertas viejas (Self-Healing).
    2. Genera nuevas alertas ocasionalmente.
    Esto arregla que la 'Salud de Activos' se quede en 0.
    """
    logger.info("⚠️ Gestionando alertas...")
    
    # Limpiar alertas viejas (> 30 mins) para recuperar salud
    conn.execute(text("""
        UPDATE alerts SET acknowledged = TRUE 
        WHERE acknowledged = FALSE AND timestamp < NOW() - INTERVAL '30 minutes'
    """))
    
    # Generar nueva alerta (20% probabilidad)
    if random.random() > 0.8:
        unit = random.choice(UNITS_CONFIG)["id"]
        alert = random.choice([
            ("HIGH", "Vibración crítica en compresor"),
            ("MEDIUM", "Filtro de succión sucio"),
            ("LOW", "Desviación menor de temperatura")
        ])
        
        # Obtener un tag_id aleatorio para esta unidad
        tags_for_unit = [t for t in TAGS_CONFIG if t["unit"] == unit]
        tag_id = random.choice(tags_for_unit)["id"] if tags_for_unit else None
        
        conn.execute(text("""
            INSERT INTO alerts (timestamp, unit_id, tag_id, severity, message, acknowledged)
            VALUES (NOW(), :uid, :tid, :sev, :msg, FALSE)
        """), {
            "uid": unit, 
            "tid": tag_id, 
            "sev": alert[0], 
            "msg": alert[1]
        })

def backfill_missing_history(conn):
    """
    Viaje en el tiempo: Si no hay datos de ayer, los crea.
    Esto arregla la gráfica de área vacía.
    """
    logger.info("🕰️ Verificando historial de 24h...")
    count = conn.execute(text("SELECT COUNT(*) FROM kpis WHERE timestamp > NOW() - INTERVAL '24 hours'")).scalar()
    
    if count < 20: # Si hay muy pocos datos
        logger.info("   ↳ Generando historial retroactivo...")
        now = datetime.now()
        for i in range(24):
            ts = now - timedelta(hours=i)
            for u in UNITS_CONFIG:
                eff = random.uniform(85, 98)
                conn.execute(text("""
                    INSERT INTO kpis (timestamp, unit_id, energy_efficiency, throughput, quality_score, maintenance_score)
                    VALUES (:ts, :uid, :eff, 12000, 99.0, 95.0)
                """), {
                    "ts": ts, 
                    "uid": u["id"], 
                    "eff": eff
                })

def update_energy_and_maintenance(conn):
    """Calcula datos de eficiencia y predicciones"""
    logger.info("🧠 Actualizando IA...")
    
    # Energía
    conn.execute(text("DELETE FROM energy_analysis"))
    for u in UNITS_CONFIG:
        conn.execute(text("""
            INSERT INTO energy_analysis (unit_id, efficiency_score, consumption_kwh, savings_potential, recommendation, analysis_date, status)
            VALUES (:uid, :eff, :cons, :sav, 'Operación nominal', NOW(), 'OPTIMAL')
        """), {
            "uid": u["id"], 
            "eff": random.uniform(90, 98), 
            "cons": random.uniform(4000, 6000), 
            "sav": 0
        })
        
    # Mantenimiento
    conn.execute(text("DELETE FROM maintenance_predictions"))
    for eq in EQUIPMENT_CONFIG:
        conn.execute(text("""
            INSERT INTO maintenance_predictions (equipment_id, failure_probability, prediction, recommendation, timestamp, confidence)
            VALUES (:id, :prob, 'NORMAL', 'Monitoreo continuo recomendado', NOW(), 99.5)
        """), {
            "id": eq["id"], 
            "prob": random.uniform(0, 5)
        })

# ==============================================================================
# 6. ORQUESTADOR PRINCIPAL
# ==============================================================================

def run_simulation_cycle():
    """Ejecuta un ciclo completo de simulación y mantenimiento."""
    logger.info(f"--- INICIO CICLO: {datetime.now().strftime('%H:%M:%S')} ---")
    try:
        # 1. Validación de Esquema (Nuclear Fix)
        validate_and_repair_schema()
        
        # 2. Transacción de Datos
        with engine.begin() as conn:
            seed_master_data(conn)
            backfill_missing_history(conn)
            simulate_process_dynamics(conn)
            manage_alerts_lifecycle(conn)
            update_energy_and_maintenance(conn)
            
            # Limpieza de datos viejos para no llenar el disco
            conn.execute(text("DELETE FROM process_data WHERE timestamp < NOW() - INTERVAL '2 days'"))
            
        logger.info("✅ Ciclo completado exitosamente.")
        
    except Exception as e:
        logger.error(f"❌ Error crítico en ciclo de simulación: {e}")

if __name__ == "__main__":
    print("🚀 Ejecución manual del Generador V8.0...")
    run_simulation_cycle()