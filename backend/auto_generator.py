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
# 2. DEFINICIÓN DE CATÁLOGOS MAESTROS (DATA FACTORY) - ACTUALIZADO
# ==============================================================================

# Unidades de Proceso (La estructura base de la refinería)
UNITS_CONFIG = [
    {"id": "CDU-101", "name": "Destilación Atmosférica", "type": "DISTILLATION", "desc": "Separación primaria de crudo en fracciones.", "capacity": 150000, "status": "ACTIVE"},
    {"id": "FCC-201", "name": "Craqueo Catalítico Fluidizado", "type": "CRACKING", "desc": "Conversión de hidrocarburos pesados en gasolina.", "capacity": 120000, "status": "ACTIVE"},
    {"id": "HT-305", "name": "Hidrotratamiento Diesel", "type": "TREATING", "desc": "Eliminación de azufre y contaminantes.", "capacity": 80000, "status": "ACTIVE"},
    {"id": "ALK-400", "name": "Unidad de Alquilación", "type": "ALKYLATION", "desc": "Producción de componentes de alto octanaje.", "capacity": 50000, "status": "ACTIVE"}
]

# Equipos Industriales (Activos físicos) - CON FABRICANTES
EQUIPMENT_CONFIG = [
    {"id": "PUMP-101", "name": "Bomba Alim. Crudo", "type": "PUMP", "unit": "CDU-101", "manufacturer": "Flowserve"},
    {"id": "FURNACE-100", "name": "Horno de Precalentamiento", "type": "FURNACE", "unit": "CDU-101", "manufacturer": "Thermax"},
    {"id": "TOWER-101", "name": "Torre Fraccionadora", "type": "TOWER", "unit": "CDU-101", "manufacturer": "UOP"},
    {"id": "COMP-201", "name": "Compresor Gas Húmedo", "type": "COMPRESSOR", "unit": "FCC-201", "manufacturer": "Atlas Copco"},
    {"id": "REACT-202", "name": "Reactor Riser", "type": "REACTOR", "unit": "FCC-201", "manufacturer": "UOP"},
    {"id": "REGEN-203", "name": "Regenerador Catalizador", "type": "VESSEL", "unit": "FCC-201", "manufacturer": "FLSmidth"},
    {"id": "PUMP-305", "name": "Bomba Carga Diesel", "type": "PUMP", "unit": "HT-305", "manufacturer": "Sulzer"},
    {"id": "EXCH-306", "name": "Intercambiador Calor", "type": "EXCHANGER", "unit": "HT-305", "manufacturer": "Alfa Laval"},
    {"id": "VALVE-401", "name": "Válvula Control Ácido", "type": "VALVE", "unit": "ALK-400", "manufacturer": "Emerson"}
]

# Tags / Sensores (Variables de proceso) - INCLUYE CORRIENTE MOTOR
TAGS_CONFIG = [
    {"id": "TI-101", "name": "Temp. Salida Horno", "unit": "CDU-101", "uom": "°C", "min_val": 340, "max_val": 360, "tag_type": "TEMPERATURE"},
    {"id": "FI-102", "name": "Flujo Carga Crudo", "unit": "CDU-101", "uom": "bpd", "min_val": 9800, "max_val": 10200, "tag_type": "FLOW"},
    {"id": "PI-103", "name": "Presión Torre", "unit": "CDU-101", "uom": "psig", "min_val": 15, "max_val": 25, "tag_type": "PRESSURE"},
    {"id": "II-999", "name": "Corriente Motor", "unit": "CDU-101", "uom": "A", "min_val": 45, "max_val": 55, "tag_type": "CURRENT"},
    {"id": "PI-201", "name": "Presión Reactor", "unit": "FCC-201", "uom": "psig", "min_val": 28, "max_val": 32, "tag_type": "PRESSURE"},
    {"id": "TI-203", "name": "Temp. Regenerador", "unit": "FCC-201", "uom": "°C", "min_val": 680, "max_val": 720, "tag_type": "TEMPERATURE"},
    {"id": "LI-305", "name": "Nivel Separador", "unit": "HT-305", "uom": "%", "min_val": 45, "max_val": 55, "tag_type": "LEVEL"},
    {"id": "TI-306", "name": "Temp. Reacción HDS", "unit": "HT-305", "uom": "°C", "min_val": 320, "max_val": 350, "tag_type": "TEMPERATURE"},
    {"id": "AI-400", "name": "Concentración Ácido", "unit": "ALK-400", "uom": "%", "min_val": 88, "max_val": 92, "tag_type": "ANALYTICAL"},
    {"id": "FI-402", "name": "Flujo Isobutano", "unit": "ALK-400", "uom": "bpd", "min_val": 4000, "max_val": 4500, "tag_type": "FLOW"}
]

# Tanques y Productos (Logística)
TANK_PRODUCTS = {
    "TK-101": {"prod": "Crudo Pesado Maya", "cap": 80000},
    "TK-102": {"prod": "Gasolina Magna 87", "cap": 45000},
    "TK-201": {"prod": "Diesel UBA", "cap": 50000},
    "TK-305": {"prod": "Agua de Proceso", "cap": 20000},
    "TK-400": {"prod": "Alquilado", "cap": 15000}
}

# Inventario (Almacén)
INVENTORY_ITEMS = [
    {"item": "Catalizador FCC-ZSM5", "sku": "CAT-ZSM5", "quantity": 1500, "unit": "kg", "status": "OK"},
    {"item": "Inhibidor de Corrosión", "sku": "CHEM-CORR-01", "quantity": 800, "unit": "L", "status": "OK"},
    {"item": "Sosa Cáustica 50%", "sku": "CHEM-NAOH", "quantity": 2000, "unit": "L", "status": "LOW"},
    {"item": "Aceite Lubricante ISO-68", "sku": "LUB-ISO68", "quantity": 45, "unit": "tambor", "status": "OK"},
    {"item": "Empaques Espirales 4\"", "sku": "GSK-SP-04", "quantity": 120, "unit": "pza", "status": "OK"},
    {"item": "Válvula de Seguridad 2\"", "sku": "PSV-02-CS", "quantity": 5, "unit": "pza", "status": "CRITICAL"}
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
            # --- 1. REPARACIÓN: INVENTORY ---
            try:
                conn.execute(text("SELECT item FROM inventory LIMIT 1"))
            except (ProgrammingError, OperationalError) as e:
                logger.warning(f"⚠️ Tabla 'inventory' corrupta. Reconstruyendo... Error: {e}")
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

            # --- 2. REPARACIÓN: PROCESS_TAGS ---
            try:
                conn.execute(text("SELECT min_val FROM process_tags LIMIT 1"))
                # Agregar columnas faltantes
                try:
                    conn.execute(text("ALTER TABLE process_tags ADD COLUMN IF NOT EXISTS tag_type TEXT DEFAULT 'GENERAL'"))
                    conn.execute(text("ALTER TABLE process_tags ADD COLUMN IF NOT EXISTS is_critical BOOLEAN DEFAULT FALSE"))
                except:
                    pass
            except (ProgrammingError, OperationalError) as e:
                logger.warning(f"⚠️ Tabla 'process_tags' corrupta. Reconstruyendo... Error: {e}")
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
                        description TEXT,
                        tag_type TEXT DEFAULT 'GENERAL',
                        is_critical BOOLEAN DEFAULT FALSE
                    )
                """))
                logger.info("✅ Tabla 'process_tags' reconstruida exitosamente.")

            # --- 3. REPARACIÓN: PROCESS_UNITS ---
            try:
                conn.execute(text("SELECT name FROM process_units LIMIT 1"))
                # Agregar columnas faltantes
                try:
                    conn.execute(text("ALTER TABLE process_units ADD COLUMN IF NOT EXISTS capacity FLOAT"))
                    conn.execute(text("ALTER TABLE process_units ADD COLUMN IF NOT EXISTS unit_status TEXT DEFAULT 'ACTIVE'"))
                except:
                    pass
            except (ProgrammingError, OperationalError) as e:
                logger.warning(f"⚠️ Tabla 'process_units' obsoleta. Migrando... Error: {e}")
                transaction.rollback()
                transaction = conn.begin()
                conn.execute(text("DROP TABLE IF EXISTS process_units CASCADE"))
                conn.execute(text("""
                    CREATE TABLE process_units (
                        unit_id TEXT PRIMARY KEY,
                        name TEXT,
                        type TEXT,
                        description TEXT,
                        capacity FLOAT,
                        unit_status TEXT DEFAULT 'ACTIVE'
                    )
                """))
                logger.info("✅ Tabla 'process_units' migrada.")

            # --- 4. REPARACIÓN: EQUIPMENT ---
            try:
                conn.execute(text("SELECT manufacturer FROM equipment LIMIT 1"))
            except (ProgrammingError, OperationalError) as e:
                logger.warning(f"⚠️ Tabla 'equipment' sin columna 'manufacturer'. Migrando... Error: {e}")
                transaction.rollback()
                transaction = conn.begin()
                conn.execute(text("ALTER TABLE equipment ADD COLUMN IF NOT EXISTS manufacturer TEXT"))
                logger.info("✅ Tabla 'equipment' migrada.")

            # --- 5. REPARACIÓN: TANKS ---
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
                        name TEXT UNIQUE,
                        product TEXT,
                        capacity FLOAT,
                        current_level FLOAT,
                        status TEXT,
                        last_updated TIMESTAMP DEFAULT NOW()
                    )
                """))
                logger.info("✅ Tabla 'tanks' reconstruida exitosamente.")
            
            transaction.commit()
            logger.info("✅ Esquema de base de datos validado y reparado.")
            
        except Exception as e:
            logger.error(f"❌ Error crítico durante la reparación del esquema: {e}")
            transaction.rollback()
            raise e

# ==============================================================================
# 4. POBLADO DE DATOS MAESTROS (MASTER DATA) - ACTUALIZADO
# ==============================================================================

def seed_master_data(conn):
    """Inserta los datos estáticos (Unidades, Equipos, Tags, Inventario Base)"""
    logger.info("🌱 Sembrando datos maestros...")
    
    # 1. Unidades (CON NOMBRES Y CAPACIDADES)
    for u in UNITS_CONFIG:
        conn.execute(text("""
            INSERT INTO process_units (unit_id, name, type, description, capacity, unit_status)
            VALUES (:uid, :name, :type, :desc, :cap, :status)
            ON CONFLICT (unit_id) DO UPDATE SET 
                name = EXCLUDED.name, 
                description = EXCLUDED.description,
                capacity = EXCLUDED.capacity,
                unit_status = EXCLUDED.unit_status
        """), {
            "uid": u["id"], 
            "name": u["name"], 
            "type": u["type"], 
            "desc": u["desc"],
            "cap": u.get("capacity", 0),
            "status": u.get("status", "ACTIVE")
        })

    # 2. Equipos (CON FABRICANTES)
    for eq in EQUIPMENT_CONFIG:
        conn.execute(text("""
            INSERT INTO equipment (equipment_id, equipment_name, equipment_type, unit_id, status, manufacturer)
            VALUES (:id, :name, :type, :unit, 'OPERATIONAL', :manufacturer)
            ON CONFLICT (equipment_id) DO UPDATE SET 
                equipment_name = EXCLUDED.equipment_name,
                unit_id = EXCLUDED.unit_id,
                manufacturer = EXCLUDED.manufacturer
        """), {
            "id": eq["id"],
            "name": eq["name"],
            "type": eq["type"],
            "unit": eq["unit"],
            "manufacturer": eq.get("manufacturer", "Desconocido")
        })

    # 3. Tags (Sensores) - INCLUYE CORRIENTE MOTOR
    for tag in TAGS_CONFIG:
        conn.execute(text("""
            INSERT INTO process_tags (tag_id, tag_name, unit_id, engineering_units, min_val, max_val, tag_type)
            VALUES (:id, :name, :unit, :uom, :min_val, :max_val, :tag_type)
            ON CONFLICT (tag_id) DO UPDATE SET 
                tag_name = EXCLUDED.tag_name,
                tag_type = EXCLUDED.tag_type
        """), {
            "id": tag["id"], 
            "name": tag["name"], 
            "unit": tag["unit"], 
            "uom": tag["uom"], 
            "min_val": tag["min_val"], 
            "max_val": tag["max_val"],
            "tag_type": tag.get("tag_type", "GENERAL")
        })

    # 4. Inventario
    for inv in INVENTORY_ITEMS:
        # Verificamos si existe por SKU
        exists = conn.execute(text("SELECT id FROM inventory WHERE sku = :sku"), {"sku": inv["sku"]}).scalar()
        if not exists:
            conn.execute(text("""
                INSERT INTO inventory (item, sku, quantity, unit, status, location)
                VALUES (:item, :sku, :quantity, :unit, :status, 'Almacén Central')
            """), {
                "item": inv["item"], 
                "sku": inv["sku"], 
                "quantity": inv["quantity"], 
                "unit": inv["unit"],
                "status": inv["status"]
            })

# ==============================================================================
# 5. SIMULACIÓN FÍSICA Y TRANSACCIONAL (DYNAMIC DATA)
# ==============================================================================

def simulate_process_dynamics(conn):
    """Genera datos de sensores, KPIs y movimiento de tanques."""
    logger.info("⚡ Simulando dinámica de planta...")
    
    # A. Sensores (Process Data) - CON MEJOR CALIDAD
    for tag in TAGS_CONFIG:
        # Generar valor con ruido gaussiano
        center = (tag["min_val"] + tag["max_val"]) / 2
        sigma = (tag["max_val"] - tag["min_val"]) / 6
        val = random.gauss(center, sigma)
        
        # 80% de probabilidad de buena calidad, 20% dudosa
        quality = 192 if random.random() > 0.2 else 128
        
        conn.execute(text("""
            INSERT INTO process_data (timestamp, unit_id, tag_id, value, quality)
            VALUES (:ts, :uid, :tid, :val, :quality)
        """), {
            "ts": datetime.now(), 
            "uid": tag["unit"], 
            "tid": tag["id"], 
            "val": round(val, 2),
            "quality": quality
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

    # C. Dinámica de Tanques
    tanks = conn.execute(text("SELECT id, name, capacity, current_level, status FROM tanks")).fetchall()
    
    if not tanks:
        # Inicializar si vacío
        for name, info in TANK_PRODUCTS.items():
            conn.execute(text("""
                INSERT INTO tanks (name, product, capacity, current_level, status, last_updated)
                VALUES (:n, :p, :c, :l, 'STABLE', NOW())
            """), {
                "n": name, 
                "p": info['prod'], 
                "c": info['cap'], 
                "l": info['cap'] * 0.6
            })
    else:
        for t in tanks:
            tid, tname, cap, level, status = t
            delta = cap * 0.015
            
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
def simulate_inventory_changes(conn):
    """
    Simula el consumo y reposición de inventario de forma realista.
    Cada ciclo, algunos items se consumen y otros se reponen.
    """
    logger.info("📦 Simulando dinámica de inventario...")
    
    try:
        # Obtener todo el inventario actual
        inventory_items = conn.execute(text("SELECT * FROM inventory")).fetchall()
        
        for item in inventory_items:
            item_id, item_name, sku, quantity, unit, status, location, last_updated = item
            
            # Diferentes tasas de consumo según el tipo de item
            consumption_rate = 0
            
            if "Catalizador" in item_name:
                consumption_rate = random.uniform(0.5, 2.0)  # Se consume rápido
            elif "Inhibidor" in item_name or "Sosa" in item_name:
                consumption_rate = random.uniform(1.0, 3.0)  # Consumo medio
            elif "Aceite" in item_name:
                consumption_rate = random.uniform(0.1, 0.5)  # Consumo lento
            elif "Válvula" in item_name or "Empaque" in item_name:
                consumption_rate = random.uniform(0, 0.1)    # Consumo muy lento
            else:
                consumption_rate = random.uniform(0.5, 1.5)  # Consumo general
            
            # Nueva lógica con mayor variabilidad
            rand_choice = random.random()
            
            if rand_choice < 0.7:  # 70% de probabilidad de consumir
                # A veces consumo grande, a veces pequeño
                if random.random() < 0.2:  # 20% de probabilidad de consumo grande
                    consumption_multiplier = random.uniform(3, 10)
                else:
                    consumption_multiplier = random.uniform(0.5, 2)
                
                new_quantity = max(0, quantity - (consumption_rate * consumption_multiplier))
            elif rand_choice < 0.9:  # 20% de probabilidad de reposición (0.7 a 0.9)
                # Reposición
                new_quantity = quantity + random.uniform(10, 50)
            else:  # 10% de probabilidad de sin cambios (0.9 a 1.0)
                new_quantity = quantity
            
            # Actualizar estado según la cantidad
            new_status = "OK"
            if new_quantity <= 0:
                new_status = "CRITICAL"
                new_quantity = 0  # No permitir negativos
            elif new_quantity < 10:
                new_status = "LOW"
            elif new_quantity > 100:
                new_status = "OK"
            
            # Actualizar en la base de datos
            conn.execute(text("""
                UPDATE inventory 
                SET quantity = :qty, status = :status, last_updated = NOW() 
                WHERE id = :id
            """), {
                "qty": round(new_quantity, 2), 
                "status": new_status, 
                "id": item_id
            })
            
            # Registrar reposiciones automáticas si el stock está muy bajo
            if new_status == "CRITICAL" and random.random() < 0.3:
                reposicion = random.uniform(50, 100)
                conn.execute(text("""
                    UPDATE inventory 
                    SET quantity = :qty, status = 'LOW', last_updated = NOW() 
                    WHERE id = :id
                """), {
                    "qty": reposicion, 
                    "id": item_id
                })
                logger.info(f"   ↳ Reposición automática: {item_name} +{reposicion:.0f} {unit}")
    
    except Exception as e:
        logger.error(f"Error en simulación de inventario: {e}")
def generate_new_inventory_items(conn):
    """
    Genera nuevos items de inventario aleatoriamente ocasionalmente.
    Esto simula nuevas compras o adquisiciones.
    """
    # 15% de probabilidad de agregar un nuevo item en cada ciclo
    if random.random() > 0.15:
        return
    
    # Lista de posibles nuevos items
    possible_items = [
        {"item": "Filtro de Aire HEPA", "sku": "FILT-HEPA-01", "quantity": random.randint(5, 20), "unit": "pza", "status": "OK"},
        {"item": "Sensor de Presión 4-20mA", "sku": f"SENS-P-{random.randint(100, 999)}", "quantity": random.randint(2, 8), "unit": "pza", "status": "OK"},
        {"item": "Juego de Juntas Espirales", "sku": f"JGTA-{random.randint(10, 99)}", "quantity": random.randint(10, 30), "unit": "juego", "status": "OK"},
        {"item": "Aceite Hidráulico ISO-46", "sku": f"ACE-HID-{random.randint(1, 9)}", "quantity": random.randint(100, 300), "unit": "L", "status": "OK"},
        {"item": "Kit de Mantenimiento Bombas", "sku": f"KIT-PMP-{random.randint(1, 5)}", "quantity": random.randint(1, 5), "unit": "kit", "status": "LOW"},
        {"item": "Reactivo de Prueba pH", "sku": f"REACT-PH-{random.randint(1, 9)}", "quantity": random.randint(50, 150), "unit": "L", "status": "OK"},
    ]
    
    new_item = random.choice(possible_items)
    
    try:
        # Verificar si el SKU ya existe
        existing = conn.execute(text("SELECT id FROM inventory WHERE sku = :sku"), 
                               {"sku": new_item["sku"]}).fetchone()
        
        if not existing:
            conn.execute(text("""
                INSERT INTO inventory (item, sku, quantity, unit, status, location, last_updated)
                VALUES (:item, :sku, :qty, :unit, :status, 'Almacén Central', NOW())
            """), {
                "item": new_item["item"],
                "sku": new_item["sku"],
                "qty": new_item["quantity"],
                "unit": new_item["unit"],
                "status": new_item["status"]
            })
            logger.info(f"🆕 Nuevo item agregado: {new_item['item']} (SKU: {new_item['sku']})")
    except Exception as e:
        logger.error(f"Error agregando nuevo item: {e}")
def backfill_missing_history(conn):
    """
    Viaje en el tiempo: Si no hay datos de ayer, los crea.
    Esto arregla la gráfica de área vacía.
    """
    logger.info("🕰️ Verificando historial de 24h...")
    count = conn.execute(text("SELECT COUNT(*) FROM kpis WHERE timestamp > NOW() - INTERVAL '24 hours'")).scalar()
    
    if count < 20:
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
            simulate_inventory_changes(conn)  # <-- AÑADIR ESTA LÍNEA
            generate_new_inventory_items(conn)  # <-- AÑADIR ESTA LÍNEA
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