import os

def inject_advanced_stats():
    print("🧠 INYECTANDO CEREBRO ANALÍTICO AVANZADO...")
    
    file_path = 'main.py'
    if not os.path.exists(file_path):
        print("❌ No se encuentra main.py")
        return

    # Código de los nuevos endpoints analíticos
    advanced_code = """
# ==========================================
# 🧠 ANALÍTICA AVANZADA & HISTÓRICOS
# ==========================================

@app.get("/api/dashboard/history")
async def get_dashboard_history():
    \"\"\"Obtiene tendencia histórica real de KPIs (últimas 24h)\"\"\"
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
    \"\"\"Calcula métricas de ingeniería complejas (OEE, Estabilidad, Costos)\"\"\"
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
"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Insertar antes del main
    if "if __name__" in content:
        final_content = content.replace("if __name__", advanced_code + "\n\nif __name__")
    else:
        final_content = content + advanced_code

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print("✅ Backend actualizado con Cerebro Analítico.")
    print("👉 REINICIA EL SERVIDOR: uvicorn main:app --reload")

if __name__ == "__main__":
    inject_advanced_stats()