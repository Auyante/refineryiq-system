"""
Generador de datos inteligente y robusto para RefineryIQ
Correcciones:
1. Serialización JSON explícita para evitar errores de asyncpg.
2. Generación forzada de alertas para demostración.
3. Reparación de rangos nulos en process_tags.
"""
import asyncio
import random
import json
from datetime import datetime, timedelta, timezone
import asyncpg
import sys

class DataGenerator:
    def __init__(self):
        # Asegúrate de que la contraseña y puerto sean correctos
        self.db_url = "postgresql://postgres:307676@localhost:5432/refineryiq"
        
    async def run(self, hours=24):
        print(f"\n🚀 INICIANDO GENERADOR DE DATOS ({hours}h)...")
        
        try:
            conn = await asyncpg.connect(self.db_url)
            print("✅ Conectado a PostgreSQL")
        except Exception as e:
            print(f"❌ Error conectando a BD: {e}")
            return

        try:
            # --- PASO 0: REPARAR RANGOS EN TAGS ---
            # Si los tags no tienen límites definidos, las alertas no funcionan.
            print("🔧 Configurando rangos operativos en tags...")
            await conn.execute("""
                UPDATE process_tags SET normal_range_min = 300, normal_range_max = 600, critical_threshold = 650 
                WHERE tag_id LIKE '%TEMP%' AND normal_range_max IS NULL;
                
                UPDATE process_tags SET normal_range_min = 10, normal_range_max = 50, critical_threshold = 60 
                WHERE tag_id LIKE '%PRESS%' AND normal_range_max IS NULL;
                
                UPDATE process_tags SET normal_range_min = 8000, normal_range_max = 12000 
                WHERE tag_id LIKE '%FLOW%' AND normal_range_max IS NULL;
            """)

            # 1. OBTENER REFERENCIAS
            units = await conn.fetch("SELECT unit_id FROM process_units")
            tags = await conn.fetch("SELECT tag_id, unit_id, tag_type FROM process_tags")
            equipment = await conn.fetch("SELECT equipment_id, unit_id, equipment_type FROM equipment")
            
            if not units or not tags:
                print("⚠️ No hay unidades o tags. Ejecuta normalization_migration.py primero.")
                return

            # 2. GENERAR DATOS DE PROCESO
            print(f"📊 Generando lecturas de sensores ({hours} horas)...")
            records_count = 0
            start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Preparamos una lista masiva de inserciones para velocidad
            process_values = []
            
            for h in range(hours):
                current_time = start_time + timedelta(hours=h)
                for tag in tags:
                    # Generar valor con algo de "ruido"
                    if 'TEMP' in tag['tag_id']: 
                        base = 450
                        val = random.gauss(base, 20) # Normal dist
                    elif 'PRESS' in tag['tag_id']: 
                        base = 30
                        val = random.gauss(base, 2)
                    elif 'FLOW' in tag['tag_id']:
                        base = 10000
                        val = random.gauss(base, 500)
                    else:
                        val = random.uniform(50, 100)
                    
                    # Ocasionalmente generar un pico (anomalía)
                    if random.random() < 0.05:
                        val *= 1.3
                    
                    await conn.execute("""
                        INSERT INTO process_data (timestamp, unit_id, tag_id, value, quality)
                        VALUES ($1, $2, $3, $4, $5)
                    """, current_time, tag['unit_id'], tag['tag_id'], round(val, 2), 1)
                    records_count += 1
            
            print(f"   ✅ {records_count} registros insertados.")

            # 3. GENERAR ALERTAS (Forzadas y Reales)
            print("🚨 Generando historial de alertas...")
            alert_msgs = [
                ("Alta Temperatura en Torre", "HIGH"),
                ("Vibración en Bomba de Alimentación", "MEDIUM"),
                ("Presión Crítica en Reactor", "HIGH"),
                ("Nivel Bajo en Tanque de Retorno", "LOW"),
                ("Fuga detectada en brida", "HIGH")
            ]
            
            alerts_count = 0
            for _ in range(10): # Generar 10 alertas aleatorias
                t = random.choice(tags)
                msg, sev = random.choice(alert_msgs)
                alert_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, hours))
                
                await conn.execute("""
                    INSERT INTO alerts (timestamp, unit_id, tag_id, value, threshold, severity, message, acknowledged)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, alert_time, t['unit_id'], t['tag_id'], 
                   random.uniform(100, 200), 90.0, sev, msg, random.choice([True, False]))
                alerts_count += 1
            
            print(f"   ✅ {alerts_count} alertas generadas.")

            # 4. MANTENIMIENTO PREDICTIVO
            print("🔮 Actualizando modelos de mantenimiento...")
            mp_count = 0
            for eq in equipment:
                # Simular probabilidad de falla
                prob = random.uniform(10, 95)
                
                if prob > 80:
                    pred = "FALLA INMINENTE"
                    rec = "Programar parada técnica y reemplazo de sellos."
                elif prob > 40:
                    pred = "RIESGO MODERADO"
                    rec = "Aumentar frecuencia de monitoreo de vibración."
                else:
                    pred = "OPERACIÓN NORMAL"
                    rec = "Continuar plan de mantenimiento preventivo."
                
                # Features ficticios para el JSON
                features = {
                    "vibration": round(random.uniform(2, 8), 2),
                    "temperature": round(random.uniform(60, 90), 1),
                    "hours_run": random.randint(1000, 5000)
                }
                
                await conn.execute("""
                    INSERT INTO maintenance_predictions 
                    (equipment_id, equipment_type, unit_id, failure_probability, prediction, confidence, recommendation, timestamp, features)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8)
                """, eq['equipment_id'], eq['equipment_type'], eq['unit_id'], 
                   round(prob, 1), pred, 92.5, rec, json.dumps(features))
                mp_count += 1
            print(f"   ✅ {mp_count} predicciones generadas.")

            # 5. ANÁLISIS ENERGÉTICO (Donde estaba el error)
            print("⚡ Realizando auditoría energética...")
            ea_count = 0
            for u in units:
                benchmark = 45.0
                cons = random.uniform(42, 55) # Consumo un poco alto
                eff = (benchmark / cons) * 100
                target = benchmark * 0.95
                
                status = "EXCELLENT" if eff > 95 else "NEEDS_IMPROVEMENT" if eff > 80 else "POOR"
                
                # CORRECCIÓN JSON: Convertir listas a strings JSON explícitamente
                inefficiencies = []
                if cons > benchmark:
                    inefficiencies.append({
                        "type": "EXCESS_CONSUMPTION",
                        "severity": "MEDIUM",
                        "val": round(cons - benchmark, 2)
                    })
                
                recommendations = [
                    {"action": "Check Insulation", "priority": "HIGH"},
                    {"action": "Optimize Heater", "priority": "MEDIUM"}
                ]
                
                await conn.execute("""
                    INSERT INTO energy_analysis 
                    (unit_id, analysis_date, avg_energy_consumption, benchmark, 
                     target, efficiency_score, status, inefficiencies, 
                     recommendations, estimated_savings, timestamp)
                    VALUES ($1, CURRENT_DATE, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                """, u['unit_id'], round(cons, 2), benchmark, round(target, 2),
                   round(eff, 2), status, json.dumps(inefficiencies), json.dumps(recommendations),
                   round(max(0, cons - target), 2))
                ea_count += 1
            print(f"   ✅ {ea_count} análisis generados.")

            # 6. ACTUALIZAR KPIS
            print("📈 Recalculando KPIs globales...")
            await conn.execute("DELETE FROM kpis") # Limpiar viejos para no saturar
            for u in units:
                await conn.execute("""
                    INSERT INTO kpis (timestamp, unit_id, energy_efficiency, throughput, quality_score, maintenance_score)
                    VALUES (NOW(), $1, $2, $3, $4, $5)
                """, u['unit_id'], random.uniform(85, 98), random.uniform(9000, 11000), 
                   random.uniform(90, 99), random.uniform(70, 95))
            print("   ✅ KPIs actualizados.")

        except Exception as e:
            print(f"\n❌ ERROR CRÍTICO: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if conn:
                await conn.close()
            print("\n✨ Generación finalizada. Reinicia el backend.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    gen = DataGenerator()
    try:
        hours_input = input("¿Horas de datos? [48]: ").strip()
        h = int(hours_input) if hours_input.isdigit() else 48
        asyncio.run(gen.run(h))
    except KeyboardInterrupt:
        pass