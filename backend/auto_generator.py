import os
import random
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, OperationalError

# ==============================================================================
# CONFIGURACIÓN DEL GENERADOR DE DATOS (INDUSTRIAL SIMULATION)
# ==============================================================================

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:307676@localhost:5432/refineryiq")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# --- CATÁLOGOS MAESTROS (NORMALIZACIÓN) ---

# 1. Unidades de Proceso
UNITS_CONFIG = [
    {"id": "CDU-101", "name": "Destilación Atmosférica", "type": "DISTILLATION"},
    {"id": "FCC-201", "name": "Craqueo Catalítico", "type": "CRACKING"},
    {"id": "HT-305", "name": "Hidrotratamiento Diesel", "type": "TREATING"},
    {"id": "ALK-400", "name": "Unidad de Alquilación", "type": "ALKYLATION"}
]

# 2. Equipos por Unidad (Activos)
EQUIPMENT_CONFIG = [
    {"id": "PUMP-101", "name": "Bomba de Alimentación", "type": "PUMP", "unit": "CDU-101"},
    {"id": "HE-200", "name": "Intercambiador Crudo", "type": "EXCHANGER", "unit": "CDU-101"},
    {"id": "COMP-201", "name": "Compresor de Gas Húmedo", "type": "COMPRESSOR", "unit": "FCC-201"},
    {"id": "REACT-202", "name": "Reactor Riser", "type": "REACTOR", "unit": "FCC-201"},
    {"id": "PUMP-305", "name": "Bomba de Carga Diesel", "type": "PUMP", "unit": "HT-305"},
    {"id": "VALVE-401", "name": "Válvula Control Flujo", "type": "VALVE", "unit": "ALK-400"}
]

# 3. Tags (Sensores) por Unidad
TAGS_CONFIG = [
    {"id": "TI-101", "name": "Temp. Salida Horno", "unit": "CDU-101", "uom": "°C", "min": 340, "max": 360},
    {"id": "FI-102", "name": "Flujo de Carga", "unit": "CDU-101", "uom": "bpd", "min": 9800, "max": 10200},
    {"id": "PI-201", "name": "Presión Reactor", "unit": "FCC-201", "uom": "psi", "min": 28, "max": 32},
    {"id": "TI-203", "name": "Temp. Regenerador", "unit": "FCC-201", "uom": "°C", "min": 680, "max": 720},
    {"id": "LI-305", "name": "Nivel Separador", "unit": "HT-305", "uom": "%", "min": 45, "max": 55},
    {"id": "AI-400", "name": "Concentración Ácido", "unit": "ALK-400", "uom": "%", "min": 88, "max": 92}
]

# 4. Tanques y Productos
TANK_PRODUCTS = {
    "TK-101": {"prod": "Crudo Pesado", "cap": 50000},
    "TK-102": {"prod": "Gasolina 95", "cap": 25000},
    "TK-201": {"prod": "Diesel UBA", "cap": 30000},
    "TK-305": {"prod": "Agua Proceso", "cap": 10000}
}

# ==============================================================================
# 1. GESTIÓN DE ESQUEMA (AUTO-REPARACIÓN AVANZADA)
# ==============================================================================

def initialize_schema():
    """Crea y llena las tablas maestras si están vacías o corruptas."""
    print("🔧 [SISTEMA] Verificando integridad de tablas maestras...")
    
    with engine.begin() as conn:
        # A. Tabla Equipment (Equipos)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS equipment (
                equipment_id TEXT PRIMARY KEY, equipment_name TEXT, 
                equipment_type TEXT, unit_id TEXT, status TEXT, 
                installation_date TIMESTAMP DEFAULT NOW()
            )
        """))
        
        # B. Tabla Process Tags (Sensores)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS process_tags (
                tag_id TEXT PRIMARY KEY, tag_name TEXT, unit_id TEXT, 
                engineering_units TEXT, min_val FLOAT, max_val FLOAT
            )
        """))

        # C. Tabla Inventory (Suministros)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY, item TEXT, sku TEXT, 
                quantity FLOAT, unit TEXT, status TEXT
            )
        """))

        # --- POBLADO DE DATOS MAESTROS ---
        
        # 1. Unidades
        for u in UNITS_CONFIG:
            conn.execute(text("""
                INSERT INTO process_units (unit_id, name, type) 
                VALUES (:uid, :name, :type) ON CONFLICT (unit_id) DO NOTHING
            """), {"uid": u["id"], "name": u["name"], "type": u["type"]})

        # 2. Equipos
        for eq in EQUIPMENT_CONFIG:
            conn.execute(text("""
                INSERT INTO equipment (equipment_id, equipment_name, equipment_type, unit_id, status)
                VALUES (:id, :name, :type, :unit, 'OPERATIONAL') ON CONFLICT (equipment_id) DO NOTHING
            """), eq)

        # 3. Tags (Sensores)
        for tag in TAGS_CONFIG:
            conn.execute(text("""
                INSERT INTO process_tags (tag_id, tag_name, unit_id, engineering_units, min_val, max_val)
                VALUES (:id, :name, :unit, :uom, :min, :max) ON CONFLICT (tag_id) DO NOTHING
            """), tag)

        print("✅ [SISTEMA] Tablas maestras sincronizadas (Unidades, Equipos, Tags).")

# ==============================================================================
# 2. GENERADORES DE DATOS (SIMULACIÓN FÍSICA)
# ==============================================================================

def simulate_process_data(conn):
    """Genera lecturas de sensores para 'Assets' y 'Enriched Data'"""
    print("   ↳ 📡 Generando lecturas de sensores...")
    
    for tag in TAGS_CONFIG:
        # Generar valor con fluctuación natural alrededor del rango normal
        base_val = (tag["min"] + tag["max"]) / 2
        fluctuation = (tag["max"] - tag["min"]) * 0.1 # 10% de variación
        current_val = random.gauss(base_val, fluctuation)
        
        conn.execute(text("""
            INSERT INTO process_data (timestamp, unit_id, tag_id, value, quality)
            VALUES (:ts, :uid, :tid, :val, 192)
        """), {
            "ts": datetime.now(),
            "uid": tag["unit"],
            "tid": tag["id"],
            "val": round(current_val, 2)
        })

def simulate_kpis(conn):
    """Genera puntos para el Dashboard Principal (Tendencias)"""
    print("   ↳ 📈 Generando KPIs de producción...")
    
    for u in UNITS_CONFIG:
        # Simulación de tendencia suave (Random Walk)
        prev_kpi = conn.execute(text(
            "SELECT energy_efficiency FROM kpis WHERE unit_id=:uid ORDER BY timestamp DESC LIMIT 1"
        ), {"uid": u["id"]}).scalar()
        
        last_eff = prev_kpi if prev_kpi else 88.0
        new_eff = last_eff + random.uniform(-1.5, 1.5) # Cambio suave
        new_eff = max(60, min(99.9, new_eff)) # Límites
        
        throughput = (new_eff / 100) * 15000 * random.uniform(0.95, 1.05)
        
        conn.execute(text("""
            INSERT INTO kpis (timestamp, unit_id, energy_efficiency, throughput, quality_score, maintenance_score)
            VALUES (:ts, :uid, :eff, :th, 99.5, 95.0)
        """), {
            "ts": datetime.now(), "uid": u["id"], 
            "eff": round(new_eff, 2), "th": round(throughput, 0)
        })

def simulate_tanks(conn):
    """Simula llenado/vaciado progresivo (No saltos locos)"""
    print("   ↳ 🛢️ Actualizando tanques (Física Real)...")
    
    tanks = conn.execute(text("SELECT id, name, current_level, capacity, status FROM tanks")).fetchall()
    
    if not tanks:
        # Crear tanques si no existen
        for name, info in TANK_PRODUCTS.items():
            conn.execute(text("""
                INSERT INTO tanks (name, product, capacity, current_level, status)
                VALUES (:name, :prod, :cap, :curr, 'STABLE')
            """), {"name": name, "prod": info['prod'], "cap": info['cap'], "curr": info['cap'] * 0.5})
        return

    for t in tanks:
        tid, name, level, cap, status = t
        
        # Cambio realista: 0.5% a 2% de la capacidad cada 5 min
        delta = cap * random.uniform(0.005, 0.02) 
        
        new_level = level
        new_status = status

        if status == 'FILLING':
            new_level += delta
            if new_level >= cap * 0.98: new_status = 'DRAINING' # Lleno -> Vaciar
        elif status == 'DRAINING':
            new_level -= delta
            if new_level <= cap * 0.05: new_status = 'FILLING' # Vacío -> Llenar
        else: # STABLE
            if random.random() > 0.8: # A veces cambia de estado
                new_status = random.choice(['FILLING', 'DRAINING'])
        
        # Limitar a capacidad física
        new_level = max(0, min(new_level, cap))
        
        conn.execute(text("UPDATE tanks SET current_level = :lvl, status = :st WHERE id = :id"), 
                     {"lvl": new_level, "st": new_status, "id": tid})

def simulate_inventory(conn):
    """Asegura que haya datos en 'Supply' y los consume lentamente"""
    print("   ↳ 📦 Verificando inventario...")
    
    # 1. Asegurar existencias (Evita 'Producto Desconocido')
    items = [
        ("Catalizador FCC-A", "CAT-001", "kg"),
        ("Aditivo Anticorrosivo", "ADD-X5", "L"),
        ("Reactivo de pH", "REA-PH2", "L"),
        ("Lubricante Industrial", "LUB-V8", "bidon"),
        ("Válvulas de Repuesto", "VAL-2X", "pza")
    ]
    
    for item in items:
        exists = conn.execute(text("SELECT 1 FROM inventory WHERE sku = :sku"), {"sku": item[1]}).scalar()
        if not exists:
            conn.execute(text("""
                INSERT INTO inventory (item, sku, quantity, unit, status)
                VALUES (:i, :s, :q, :u, 'OK')
            """), {"i":item[0], "s":item[1], "q":random.randint(50, 500), "u":item[2]})
            
    # 2. Consumo lento
    conn.execute(text("""
        UPDATE inventory 
        SET quantity = GREATEST(0, quantity - (random() * 2)),
            status = CASE 
                WHEN quantity < 20 THEN 'CRITICAL' 
                WHEN quantity < 100 THEN 'LOW' 
                ELSE 'OK' 
            END
    """))

def simulate_maintenance(conn):
    """Actualiza predicciones de IA para que no se vean estáticas"""
    print("   ↳ 🧠 Actualizando predicciones de Mantenimiento...")
    
    # Limpiar predicciones viejas
    conn.execute(text("DELETE FROM maintenance_predictions"))
    
    for eq in EQUIPMENT_CONFIG:
        # Probabilidad aleatoria pero ponderada (la mayoría sanos)
        prob = random.choice([random.uniform(0, 10), random.uniform(0, 10), random.uniform(40, 60), random.uniform(80, 95)])
        
        status = "NORMAL"
        rec = "Operación normal"
        if prob > 80: 
            status = "CRITICAL"
            rec = "Programar parada urgente"
        elif prob > 40: 
            status = "WARNING"
            rec = "Inspección visual requerida"
            
        conn.execute(text("""
            INSERT INTO maintenance_predictions (equipment_id, failure_probability, prediction, recommendation, timestamp, confidence)
            VALUES (:eid, :prob, :stat, :rec, NOW(), :conf)
        """), {
            "eid": eq["id"], "prob": prob, "stat": status, "rec": rec, "conf": random.uniform(85, 99)
        })

# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

def run_simulation_cycle():
    print(f"\n🔄 [SIMULACIÓN] Ciclo: {datetime.now().strftime('%H:%M:%S')}")
    try:
        initialize_schema() # Siempre verifica que las tablas maestras existan
        
        with engine.begin() as conn:
            simulate_process_data(conn) # Genera datos para Assets
            simulate_kpis(conn)         # Genera datos para Dashboard
            simulate_tanks(conn)        # Genera datos para Supply
            simulate_inventory(conn)    # Genera datos para Supply
            simulate_maintenance(conn)  # Genera datos para Mantenimiento
            
            # Limpieza: Mantener tabla Process Data ligera (últimos 1000 registros)
            conn.execute(text("DELETE FROM process_data WHERE id NOT IN (SELECT id FROM process_data ORDER BY timestamp DESC LIMIT 1000)"))
            
        print("✅ [SIMULACIÓN] Datos inyectados correctamente.")
    except Exception as e:
        print(f"❌ [SIMULACIÓN] Error: {e}")

if __name__ == "__main__":
    print("🚀 Ejecutando generador industrial...")
    # Llenar historial de 24 horas si es necesario
    run_simulation_cycle()