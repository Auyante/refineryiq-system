import os
import sys  # <--- FALTABA ESTO
import asyncio
import asyncpg
import random
import json
from datetime import datetime, timedelta, timezone

def update_main_logic():
    print("🧠 ACTUALIZANDO LÓGICA DE BACKEND...")
    file_path = 'main.py'
    
    # 1. Código del nuevo endpoint de Activos + Corrección de Estabilidad
    new_logic = """
# ==========================================
# 🛠️ GESTIÓN DE ACTIVOS & ESTABILIDAD V2
# ==========================================

@app.get("/api/assets/overview")
async def get_assets_overview():
    \"\"\"Obtiene estado completo de equipos con sus últimas lecturas\"\"\"
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
            sensors_raw = row['sensors']
            # Postgres devuelve string JSON a veces, o lista directa dependiendo del driver
            if isinstance(sensors_raw, str):
                sensors_parsed = json.loads(sensors_raw)
            else:
                sensors_parsed = sensors_raw
                
            sensors = [s for s in sensors_parsed if s['value'] is not None]
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
"""
    
    # Inyectamos el endpoint al final antes del if __name__
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "/api/assets/overview" not in content:
            if "if __name__" in content:
                content = content.replace("if __name__", new_logic + "\n\nif __name__")
            else:
                content += new_logic
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ main.py actualizado con endpoint de Activos.")
        else:
            print("ℹ️ Endpoint de activos ya existe en main.py.")
    else:
        print("❌ No se encontró main.py")

async def generate_dense_data():
    print("\n🚀 GENERANDO DATOS DE ALTA DENSIDAD (Gráficos Suaves)...")
    db_url = "postgresql://postgres:307676@localhost:5432/refineryiq"
    
    try:
        conn = await asyncpg.connect(db_url)
        tags = await conn.fetch("SELECT tag_id, unit_id FROM process_tags")
        
        # Borrar datos de las últimas 24h para reescribirlos bien
        print("   🧹 Limpiando últimas 24h defectuosas...")
        await conn.execute("DELETE FROM process_data WHERE timestamp >= NOW() - INTERVAL '24 HOURS'")
        await conn.execute("DELETE FROM kpis WHERE timestamp >= NOW() - INTERVAL '24 HOURS'")
        
        print("   ✍️ Insertando datos cada 15 minutos...")
        # Generar puntos cada 15 minutos para las últimas 24 horas
        start_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        total_points = 0
        # 24 horas * 4 puntos/hora = 96 puntos por tag
        for i in range(96):
            current_time = start_time + timedelta(minutes=15 * i)
            
            # 1. Datos de Sensores
            for tag in tags:
                # Valores muy estables para que la estabilidad suba a ~95/100
                if 'TEMP' in tag['tag_id']: base = 450
                elif 'FLOW' in tag['tag_id']: base = 10000
                else: base = 50
                
                # Variación muy pequeña (0.5%)
                val = base * random.uniform(0.995, 1.005)
                
                await conn.execute("""
                    INSERT INTO process_data (timestamp, unit_id, tag_id, value, quality)
                    VALUES ($1, $2, $3, $4, 1)
                """, current_time, tag['unit_id'], tag['tag_id'], val)
            
            # 2. Datos de KPIs (Para el gráfico del dashboard)
            # Generamos una curva bonita (senoidal) para que el gráfico se vea pro
            import math
            curve = math.sin(i / 10) * 5 # Oscilación
            eff = 90 + curve + random.uniform(-1, 1)
            prod = 10000 + (curve * 100) + random.uniform(-200, 200)
            
            # Insertar para las 3 unidades
            for uid in ['CDU-101', 'FCC-201', 'HT-301']:
                await conn.execute("""
                    INSERT INTO kpis (timestamp, unit_id, energy_efficiency, throughput, quality_score, maintenance_score)
                    VALUES ($1, $2, $3, $4, 95, 98)
                """, current_time, uid, eff, prod)
            
            total_points += 1
            
        print(f"   ✅ Insertados {total_points} intervalos de tiempo (aprox {total_points * len(tags)} lecturas).")
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error BD: {e}")

if __name__ == "__main__":
    # 1. Actualizar API
    update_main_logic()
    
    # 2. Generar Datos
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(generate_dense_data())