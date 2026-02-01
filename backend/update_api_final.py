import os

def update_api_final():
    print("🔌 CONECTANDO BACKEND A MÓDULOS INTELIGENTES...")
    
    file_path = 'main.py'
    if not os.path.exists(file_path):
        print("❌ No se encuentra main.py")
        return

    # Código de los nuevos endpoints conectados a la BD real
    new_endpoints = """

# ==========================================
# 🚀 ENDPOINTS PROFESIONALES (CONECTADOS A BD)
# ==========================================

@app.get("/api/maintenance/predictions")
async def get_maintenance_predictions():
    \"\"\"Obtiene predicciones reales de ML desde la BD\"\"\"
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
    \"\"\"Obtiene análisis energético desde la vista enriquecida\"\"\"
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
    \"\"\"Obtiene historial completo de alertas para la tabla\"\"\"
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
"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Insertamos los endpoints antes del bloque "if __name__"
    if "if __name__" in content:
        final_content = content.replace("if __name__", new_endpoints + "\n\nif __name__")
    else:
        final_content = content + new_endpoints

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print("✅ main.py actualizado con endpoints reales.")
    print("👉 REINICIA TU SERVIDOR: uvicorn main:app --reload")

if __name__ == "__main__":
    update_api_final()