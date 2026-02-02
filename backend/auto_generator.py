import os
import random
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, OperationalError

# ==============================================================================
# CONFIGURACIÓN DEL GENERADOR DE DATOS (INDUSTRIAL SIMULATION V7.0)
# ==============================================================================

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:307676@localhost:5432/refineryiq")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# --- CATÁLOGOS MAESTROS COMPLETO ---

UNITS_CONFIG = [
    {"id": "CDU-101", "name": "Destilación Atmosférica", "type": "DISTILLATION", "desc": "Separación primaria de crudo"},
    {"id": "FCC-201", "name": "Craqueo Catalítico", "type": "CRACKING", "desc": "Conversión de fracciones pesadas"},
    {"id": "HT-305", "name": "Hidrotratamiento Diesel", "type": "TREATING", "desc": "Eliminación de azufre"},
    {"id": "ALK-400", "name": "Unidad de Alquilación", "type": "ALKYLATION", "desc": "Producción de alto octanaje"}
]

EQUIPMENT_CONFIG = [
    {"id": "PUMP-101", "name": "Bomba de Alimentación", "type": "PUMP", "unit": "CDU-101"},
    {"id": "HE-200", "name": "Intercambiador Crudo", "type": "EXCHANGER", "unit": "CDU-101"},
    {"id": "COMP-201", "name": "Compresor de Gas Húmedo", "type": "COMPRESSOR", "unit": "FCC-201"},
    {"id": "REACT-202", "name": "Reactor Riser", "type": "REACTOR", "unit": "FCC-201"},
    {"id": "PUMP-305", "name": "Bomba de Carga Diesel", "type": "PUMP", "unit": "HT-305"},
    {"id": "VALVE-401", "name": "Válvula Control Flujo", "type": "VALVE", "unit": "ALK-400"}
]

TAGS_CONFIG = [
    {"id": "TI-101", "name": "Temp. Salida Horno", "unit": "CDU-101", "uom": "°C", "min": 340, "max": 360},
    {"id": "FI-102", "name": "Flujo de Carga", "unit": "CDU-101", "uom": "bpd", "min": 9800, "max": 10200},
    {"id": "PI-201", "name": "Presión Reactor", "unit": "FCC-201", "uom": "psi", "min": 28, "max": 32},
    {"id": "TI-203", "name": "Temp. Regenerador", "unit": "FCC-201", "uom": "°C", "min": 680, "max": 720},
    {"id": "LI-305", "name": "Nivel Separador", "unit": "HT-305", "uom": "%", "min": 45, "max": 55},
    {"id": "AI-400", "name": "Concentración Ácido", "unit": "ALK-400", "uom": "%", "min": 88, "max": 92},
    {"id": "II-999", "name": "Corriente Motor", "unit": "CDU-101", "uom": "A", "min": 40, "max": 60}
]

TANK_PRODUCTS = {
    "TK-101": {"prod": "Crudo Pesado", "cap": 50000},
    "TK-102": {"prod": "Gasolina 95", "cap": 25000},
    "TK-201": {"prod": "Diesel UBA", "cap": 30000},
    "TK-305": {"prod": "Agua Proceso", "cap": 10000}
}

INVENTORY_ITEMS = [
    ("Catalizador FCC-A", "CAT-001", "kg"),
    ("Aditivo Anticorrosivo", "ADD-X5", "L"),
    ("Reactivo de pH", "REA-PH2", "L"),
    ("Lubricante Industrial", "LUB-V8", "bidon"),
    ("Válvulas de Repuesto", "VAL-2X", "pza")
]

# ==============================================================================
# 1. GESTIÓN DE ESQUEMA (AUTO-REPARACIÓN DE BASE DE DATOS)
# ==============================================================================

def initialize_schema():
    """Garantiza que todas las tablas existan con la estructura correcta."""
    print("🔧 [SISTEMA] Verificando integridad de tablas maestras...")
    
    with engine.begin() as conn:
        # A. Tabla Equipment
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS equipment (
                equipment_id TEXT PRIMARY KEY, equipment_name TEXT, 
                equipment_type TEXT, unit_id TEXT, status TEXT, 
                installation_date TIMESTAMP DEFAULT NOW()
            )
        """))
        
        # B. Tabla Process Tags
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS process_tags (
                tag_id TEXT PRIMARY KEY, tag_name TEXT, unit_id TEXT, 
                engineering_units TEXT, min_val FLOAT, max_val FLOAT
            )
        """))

        # C. Tabla Inventory (Asegurando columnas)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY, item TEXT, sku TEXT, 
                quantity FLOAT, unit TEXT, status TEXT, location TEXT
            )
        """))
        
        # D. Tabla Process Units (Reparación si falta descripción)
        try:
            conn.execute(text("SELECT description FROM process_units LIMIT 1"))
        except:
            print("   ⚠️ Migrando tabla process_units...")
            conn.execute(text("ALTER TABLE process_units ADD COLUMN IF NOT EXISTS description TEXT"))

        # --- POBLADO DE DATOS MAESTROS ---
        
        # 1. Unidades
        for u in UNITS_CONFIG:
            conn.execute(text("""
                INSERT INTO process_units (unit_id, name, type, description) 
                VALUES (:uid, :name, :type, :desc) 
                ON CONFLICT (unit_id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
            """), {"uid": u["id"], "name": u["name"], "type": u["type"], "desc": u["desc"]})

        # 2. Equipos
        for eq in EQUIPMENT_CONFIG:
            conn.execute(text("""
                INSERT INTO equipment (equipment_id, equipment_name, equipment_type, unit_id, status)
                VALUES (:id, :name, :type, :unit, 'OPERATIONAL') 
                ON CONFLICT (equipment_id) DO UPDATE SET equipment_name = EXCLUDED.equipment_name
            """), eq)

        # 3. Tags
        for tag in TAGS_CONFIG:
            conn.execute(text("""
                INSERT INTO process_tags (tag_id, tag_name, unit_id, engineering_units, min_val, max_val)
                VALUES (:id, :name, :unit, :uom, :min, :max) 
                ON CONFLICT (tag_id) DO UPDATE SET tag_name = EXCLUDED.tag_name
            """), tag)

        print("✅ [SISTEMA] Tablas maestras sincronizadas y actualizadas.")

# ==============================================================================
# 2. VIAJE EN EL TIEMPO (BACKFILL HISTÓRICO)
# ==============================================================================

def backfill_history(conn):
    """
    Rellena huecos en los datos de las últimas 24 horas.
    Esto soluciona el problema de la gráfica "Tendencia Operativa" vacía.
    """
    print("   ↳ 🕰️ Verificando historial de 24 horas...")
    
    # Verificamos si hay datos recientes
    count = conn.execute(text("SELECT COUNT(*) FROM kpis WHERE timestamp > NOW() - INTERVAL '24 hours'")).scalar()
    
    if count < 10:
        print("   ⚠️ Historial vacío detectado. Generando datos retroactivos...")
        
        # Generar un punto de datos por cada hora hacia atrás
        current_time = datetime.now()
        for hour in range(24):
            past_time = current_time - timedelta(hours=hour)
            
            for u in UNITS_CONFIG:
                efficiency = random.uniform(82, 98)
                throughput = (efficiency / 100) * 15000 + random.uniform(-200, 200)
                
                conn.execute(text("""
                    INSERT INTO kpis (timestamp, unit_id, energy_efficiency, throughput, quality_score, maintenance_score)
                    VALUES (:ts, :uid, :eff, :th, 99.5, 96.0)
                """), {
                    "ts": past_time, "uid": u["id"], 
                    "eff": round(efficiency, 2), "th": round(throughput, 0)
                })
        print("   ✅ Historial de 24 horas reconstruido.")

# ==============================================================================
# 3. GENERADORES DE DATOS (SIMULACIÓN FÍSICA)
# ==============================================================================

def simulate_process_data(conn):
    """Genera lecturas de sensores"""
    print("   ↳ 📡 Generando lecturas de sensores...")
    for tag in TAGS_CONFIG:
        base_val = (tag["min"] + tag["max"]) / 2
        fluctuation = (tag["max"] - tag["min"]) * 0.15 
        current_val = random.gauss(base_val, fluctuation)
        
        conn.execute(text("""
            INSERT INTO process_data (timestamp, unit_id, tag_id, value, quality)
            VALUES (:ts, :uid, :tid, :val, 192)
        """), {
            "ts": datetime.now(), "uid": tag["unit"], "tid": tag["id"], "val": round(current_val, 2)
        })

def simulate_kpis(conn):
    """Genera puntos actuales para el Dashboard"""
    print("   ↳ 📈 Generando KPIs en tiempo real...")
    for u in UNITS_CONFIG:
        # Tendencia suave basada en el último valor
        prev = conn.execute(text("SELECT energy_efficiency FROM kpis WHERE unit_id=:uid ORDER BY timestamp DESC LIMIT 1"), {"uid": u["id"]}).scalar()
        last_eff = prev if prev else 88.0
        new_eff = max(65, min(99.9, last_eff + random.uniform(-1.0, 1.0)))
        throughput = (new_eff / 100) * 15000 * random.uniform(0.98, 1.02)
        
        conn.execute(text("""
            INSERT INTO kpis (timestamp, unit_id, energy_efficiency, throughput, quality_score, maintenance_score)
            VALUES (:ts, :uid, :eff, :th, 99.5, 95.0)
        """), {
            "ts": datetime.now(), "uid": u["id"], "eff": round(new_eff, 2), "th": round(throughput, 0)
        })

def simulate_tanks(conn):
    """Simula llenado/vaciado"""
    print("   ↳ 🛢️ Actualizando tanques...")
    tanks = conn.execute(text("SELECT id, name, current_level, capacity, status FROM tanks")).fetchall()
    
    if not tanks:
        for name, info in TANK_PRODUCTS.items():
            conn.execute(text("INSERT INTO tanks (name, product, capacity, current_level, status) VALUES (:n, :p, :c, :l, 'STABLE')"), 
                         {"n": name, "p": info['prod'], "c": info['cap'], "l": info['cap']*0.5})
        return

    for t in tanks:
        tid, name, level, cap, status = t
        delta = cap * random.uniform(0.005, 0.02)
        new_level = level + delta if status == 'FILLING' else level - delta if status == 'DRAINING' else level
        
        # Cambio de estado lógico
        new_status = status
        if new_level >= cap * 0.95: new_status = 'DRAINING'
        if new_level <= cap * 0.10: new_status = 'FILLING'
        if status == 'STABLE' and random.random() > 0.8: new_status = random.choice(['FILLING', 'DRAINING'])
        
        conn.execute(text("UPDATE tanks SET current_level = :lvl, status = :st WHERE id = :id"), 
                     {"lvl": max(0, min(new_level, cap)), "st": new_status, "id": tid})

def manage_alerts(conn):
    """
    Genera alertas nuevas Y limpia las viejas.
    Soluciona el problema de 'Salud de Activos = 0' limpiando alertas antiguas.
    """
    print("   ↳ ⚠️ Gestionando ciclo de vida de alertas...")
    
    # 1. Auto-reconocer alertas viejas (> 2 horas)
    conn.execute(text("UPDATE alerts SET acknowledged = TRUE WHERE timestamp < NOW() - INTERVAL '2 hours' AND acknowledged = FALSE"))
    
    # 2. Generar nuevas (Baja probabilidad para no saturar)
    active_count = conn.execute(text("SELECT COUNT(*) FROM alerts WHERE acknowledged = FALSE")).scalar()
    
    # Solo generar si hay pocas alertas activas (< 5)
    if active_count < 5 and random.random() > 0.7:
        unit = random.choice(UNITS_CONFIG)["id"]
        alert = random.choice([("HIGH", "Vibración excesiva"), ("MEDIUM", "Filtro saturado"), ("LOW", "Revisión programada")])
        conn.execute(text("INSERT INTO alerts (timestamp, unit_id, severity, message, acknowledged) VALUES (NOW(), :uid, :s, :m, FALSE)"), 
                     {"uid": unit, "s": alert[0], "m": alert[1]})

def fix_inventory_names(conn):
    """Arregla 'Producto Desconocido' forzando nombres correctos"""
    print("   ↳ 📦 Reparando catálogo de inventario...")
    for item in INVENTORY_ITEMS:
        # Insertar o Actualizar nombre si el SKU coincide
        conn.execute(text("""
            INSERT INTO inventory (item, sku, quantity, unit, status)
            VALUES (:i, :s, :q, :u, 'OK')
            ON CONFLICT (id) DO UPDATE SET item = :i
        """), {"i":item[0], "s":item[1], "q":random.randint(100,500), "u":item[2]})
    
    # Actualizar nulos
    conn.execute(text("UPDATE inventory SET item = 'Material Genérico' WHERE item IS NULL"))

def simulate_energy(conn):
    print("   ↳ ⚡ Simulando energía...")
    conn.execute(text("DELETE FROM energy_analysis WHERE analysis_date < NOW() - INTERVAL '1 day'"))
    for u in UNITS_CONFIG:
        score = random.uniform(85, 99) # Valores altos para que se vea verde
        conn.execute(text("""
            INSERT INTO energy_analysis (unit_id, efficiency_score, consumption_kwh, savings_potential, recommendation, analysis_date, status)
            VALUES (:uid, :score, :c, :s, 'Optimización OK', NOW(), 'OPTIMAL')
        """), {"uid": u["id"], "score": score, "c": random.uniform(3000, 6000), "s": (100-score)*100})

# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

def run_simulation_cycle():
    print(f"\n🔄 [SIMULACIÓN V7] Ciclo: {datetime.now().strftime('%H:%M:%S')}")
    try:
        initialize_schema()
        
        with engine.begin() as conn:
            backfill_history(conn)  # Rellena huecos históricos
            simulate_process_data(conn)
            simulate_kpis(conn)
            simulate_tanks(conn)
            manage_alerts(conn)     # Limpia alertas viejas
            fix_inventory_names(conn) # Arregla nombres desconocidos
            simulate_energy(conn)
            
            # Mantenimiento predictivo dinámico
            conn.execute(text("DELETE FROM maintenance_predictions"))
            for eq in EQUIPMENT_CONFIG:
                prob = random.uniform(0, 15) # Mayormente sano
                conn.execute(text("INSERT INTO maintenance_predictions (equipment_id, failure_probability, prediction, recommendation, timestamp, confidence) VALUES (:id, :p, 'NORMAL', 'Monitorizar', NOW(), 99.0)"),
                             {"id": eq["id"], "p": prob})
            
        print("✅ [SIMULACIÓN] Ciclo completado sin errores.")
    except Exception as e:
        print(f"❌ [SIMULACIÓN] Error: {e}")

if __name__ == "__main__":
    print("🚀 Ejecutando generador V7...")
    run_simulation_cycle()