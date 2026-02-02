import os
import random
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, OperationalError

# ==============================================================================
# CONFIGURACIÓN DEL SISTEMA DE SIMULACIÓN
# ==============================================================================

# Detectar URL de Base de Datos
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:307676@localhost:5432/refineryiq")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Motor de conexión
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# --- DATOS MAESTROS (CATÁLOGOS) ---
UNITS_CONFIG = [
    {"id": "CDU-101", "name": "Destilación Atmosférica", "type": "DISTILLATION"},
    {"id": "FCC-201", "name": "Craqueo Catalítico", "type": "CRACKING"},
    {"id": "HT-305", "name": "Hidrotratamiento Diesel", "type": "TREATING"},
    {"id": "ALK-400", "name": "Unidad de Alquilación", "type": "ALKYLATION"}
]

TANK_PRODUCTS = {
    "TK-101": {"prod": "Crudo Pesado", "cap": 50000},
    "TK-102": {"prod": "Gasolina 95", "cap": 25000},
    "TK-201": {"prod": "Diesel UBA", "cap": 30000},
    "TK-305": {"prod": "Agua Proceso", "cap": 10000}
}

# ==============================================================================
# 1. SISTEMA DE REPARACIÓN DE ESQUEMA (AUTO-HEALING)
# ==============================================================================

def fix_broken_schema():
    """
    Detecta si las tablas críticas tienen la estructura incorrecta (columnas faltantes)
    y las reconstruye automáticamente. Soluciona 'UndefinedColumn'.
    """
    print("🔧 [SISTEMA] Verificando integridad de tablas...")
    
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            # --- 1. REPARACIÓN: TABLA PROCESS_UNITS ---
            try:
                conn.execute(text("SELECT unit_id, name, type FROM process_units LIMIT 1"))
            except (ProgrammingError, OperationalError):
                print("   ⚠️ [REPARACIÓN] Tabla 'process_units' obsoleta. Reconstruyendo...")
                transaction.rollback()
                transaction = conn.begin()
                conn.execute(text("DROP TABLE IF EXISTS process_units CASCADE"))
                conn.execute(text("""
                    CREATE TABLE process_units (
                        unit_id TEXT PRIMARY KEY,
                        name TEXT,
                        type TEXT,
                        description TEXT
                    )
                """))
                print("   ✅ Tabla 'process_units' reparada.")

            # --- 2. REPARACIÓN: TABLA ENERGY_ANALYSIS (TU ERROR ACTUAL) ---
            try:
                # Intentamos leer la columna que fallaba
                conn.execute(text("SELECT consumption_kwh FROM energy_analysis LIMIT 1"))
            except (ProgrammingError, OperationalError):
                print("   ⚠️ [REPARACIÓN] Tabla 'energy_analysis' obsoleta. Reconstruyendo...")
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
                        analysis_date TIMESTAMP,
                        status TEXT
                    )
                """))
                print("   ✅ Tabla 'energy_analysis' reparada.")

            # --- 3. RESTAURACIÓN DE DATOS MAESTROS ---
            # Aseguramos que existan las unidades para evitar errores de FK
            for u in UNITS_CONFIG:
                exists = conn.execute(text("SELECT 1 FROM process_units WHERE unit_id = :uid"), {"uid": u["id"]}).scalar()
                if not exists:
                    print(f"   + Restaurando unidad maestra: {u['id']}")
                    conn.execute(text("""
                        INSERT INTO process_units (unit_id, name, type) 
                        VALUES (:uid, :name, :type)
                    """), {"uid": u["id"], "name": u["name"], "type": u["type"]})

            transaction.commit()
            print("✅ [SISTEMA] Integridad de datos verificada.")
            
        except Exception as e:
            print(f"❌ Error en reparación: {e}")
            transaction.rollback()

# ==============================================================================
# 2. LÓGICA DE SIMULACIÓN
# ==============================================================================

def generate_kpis(conn):
    """Genera datos de producción"""
    print("   ↳ 🏭 Generando KPIs de producción...")
    
    for u in UNITS_CONFIG:
        unit_id = u["id"]
        efficiency = min(100, max(60, random.gauss(88, 5)))
        throughput = (efficiency / 100) * 15000 + random.uniform(-500, 500)
        quality = min(99.9, max(90, random.gauss(98, 1)))
        maint_score = min(100, max(70, random.gauss(95, 3)))

        conn.execute(text("""
            INSERT INTO kpis (timestamp, unit_id, energy_efficiency, throughput, quality_score, maintenance_score)
            VALUES (:ts, :uid, :eff, :th, :qs, :ms)
        """), {
            "ts": datetime.now(), "uid": unit_id, "eff": round(efficiency, 2),
            "th": round(throughput, 0), "qs": round(quality, 2), "ms": round(maint_score, 1)
        })

def update_tanks(conn):
    """Simula movimiento de tanques"""
    print("   ↳ 🛢️ Actualizando tanques...")
    
    tanks = conn.execute(text("SELECT id, name, current_level, status FROM tanks")).fetchall()
    
    if not tanks:
        print("     (Inicializando tanques...)")
        for name, info in TANK_PRODUCTS.items():
            conn.execute(text("""
                INSERT INTO tanks (name, product, capacity, current_level, status)
                VALUES (:name, :prod, :cap, :curr, 'STABLE')
            """), {"name": name, "prod": info['prod'], "cap": info['cap'], "curr": info['cap'] * 0.5})
        return

    for t in tanks:
        tid, name, level, status = t
        capacity = TANK_PRODUCTS.get(name, {"cap": 50000})["cap"]
        change = random.uniform(500, 2000)
        
        new_level = level
        new_status = status

        if status == 'FILLING':
            new_level += change
            if new_level >= capacity * 0.95: new_status = 'DRAINING'
        elif status == 'DRAINING':
            new_level -= change
            if new_level <= capacity * 0.15: new_status = 'FILLING'
        else:
            new_status = random.choice(['FILLING', 'DRAINING', 'STABLE'])
        
        new_level = max(0, min(new_level, capacity))
        conn.execute(text("UPDATE tanks SET current_level = :lvl, status = :st WHERE id = :id"), 
                     {"lvl": new_level, "st": new_status, "id": tid})

def generate_alerts(conn):
    """Genera alertas aleatorias"""
    if random.random() > 0.6: return 

    print("   ↳ ⚠️ Generando alerta de sistema...")
    unit = random.choice(UNITS_CONFIG)["id"]
    alert = random.choice([
        ("HIGH", "Sobrecalentamiento en intercambiador"),
        ("MEDIUM", "Filtro de entrada obstruido"),
        ("LOW", "Advertencia: Nivel bajo de aceite")
    ])
    
    conn.execute(text("""
        INSERT INTO alerts (timestamp, unit_id, severity, message, acknowledged)
        VALUES (NOW(), :uid, :sev, :msg, FALSE)
    """), {"uid": unit, "sev": alert[0], "msg": alert[1]})

def update_inventory(conn):
    """Actualiza inventario"""
    print("   ↳ 📦 Gestionando inventario...")
    count = conn.execute(text("SELECT COUNT(*) FROM inventory")).scalar()
    if count == 0:
        items = [("Catalizador A", "CAT-01", 1000, "kg"), ("Aditivo B", "ADD-X", 500, "L")]
        for i in items:
            conn.execute(text("INSERT INTO inventory (item, sku, quantity, unit, status) VALUES (:i, :s, :q, :u, 'OK')"), 
                         {"i":i[0], "s":i[1], "q":i[2], "u":i[3]})
    
    conn.execute(text("UPDATE inventory SET quantity = quantity - (random() * 2) WHERE quantity > 10"))

def generate_energy_data(conn):
    """Datos de energía"""
    print("   ↳ ⚡ Calculando métricas energéticas...")
    # Limpiamos datos viejos para no saturar
    conn.execute(text("DELETE FROM energy_analysis WHERE analysis_date < NOW() - INTERVAL '1 day'"))
    
    for u in UNITS_CONFIG:
        score = random.uniform(80, 99)
        conn.execute(text("""
            INSERT INTO energy_analysis (unit_id, efficiency_score, consumption_kwh, savings_potential, recommendation, analysis_date, status)
            VALUES (:uid, :score, :cons, :sav, 'Optimización activa', NOW(), 'OK')
        """), {"uid": u["id"], "score": score, "cons": random.uniform(3000, 8000), "sav": (100-score)*50})

# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

def run_simulation_cycle():
    print(f"\n🔄 [SIMULACIÓN] Iniciando ciclo: {datetime.now().strftime('%H:%M:%S')}")
    try:
        # Paso 1: Reparación (Fuera de transacción principal)
        fix_broken_schema()
        
        # Paso 2: Simulación (Dentro de transacción)
        with engine.begin() as conn:
            generate_kpis(conn)
            update_tanks(conn)
            generate_alerts(conn)
            update_inventory(conn)
            generate_energy_data(conn)
            
        print("✅ [SIMULACIÓN] Datos inyectados correctamente.")
    except Exception as e:
        print(f"❌ [SIMULACIÓN] Error: {e}")

if __name__ == "__main__":
    print("🚀 Ejecutando generador auto-reparable...")
    for i in range(2):
        print(f"--- Ciclo de Carga {i+1} ---")
        run_simulation_cycle()
        time.sleep(1)