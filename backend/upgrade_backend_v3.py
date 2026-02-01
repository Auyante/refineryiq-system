import os
import asyncio
import asyncpg
import random

async def upgrade_database():
    print("🏗️ CONSTRUYENDO MÓDULOS FINALES (Suministros + Seguridad)...")
    db_url = "postgresql://postgres:307676@localhost:5432/refineryiq"
    
    try:
        conn = await asyncpg.connect(db_url)
        
        # 1. CREAR TABLAS DE SUMINISTROS
        print("   Creates tables: tanks & inventory...")
        await conn.execute("DROP TABLE IF EXISTS tanks CASCADE")
        await conn.execute("DROP TABLE IF EXISTS inventory CASCADE")
        
        await conn.execute('''
            CREATE TABLE tanks (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50),
                product VARCHAR(50),
                current_level FLOAT, -- Litros/Barriles
                capacity FLOAT,
                status VARCHAR(20) -- FILLING, DRAINING, STATIC
            );
            
            CREATE TABLE inventory (
                id SERIAL PRIMARY KEY,
                item_name VARCHAR(100),
                category VARCHAR(50), -- VALVULAS, SELLOS, QUIMICOS
                quantity INT,
                min_level INT,
                location VARCHAR(50)
            );
        ''')
        
        # 2. INSERTAR DATOS (TANQUES)
        tanks_data = [
            ('TK-101', 'Crudo Pesado', 85000, 100000, 'FILLING'),
            ('TK-102', 'Crudo Ligero', 42000, 100000, 'STATIC'),
            ('TK-201', 'Gasolina 95', 65000, 80000, 'DRAINING'),
            ('TK-202', 'Diesel', 78000, 80000, 'STATIC'),
            ('TK-301', 'Agua Procesada', 95000, 100000, 'FILLING')
        ]
        await conn.executemany("INSERT INTO tanks (name, product, current_level, capacity, status) VALUES ($1, $2, $3, $4, $5)", tanks_data)
        
        # 3. INSERTAR DATOS (INVENTARIO)
        inv_data = [
            ('Sello Mecánico API-682', 'REPUESTOS', 5, 10, 'Almacén A-12'),
            ('Válvula Control 4"', 'VÁLVULAS', 2, 5, 'Almacén B-03'),
            ('Catalizador FCC (Zeolita)', 'QUÍMICOS', 4500, 1000, 'Silo Ext'),
            ('Rodamiento SKF-222', 'REPUESTOS', 15, 8, 'Almacén A-15'),
            ('Empacadura Espiral 6"', 'CONSUMIBLES', 50, 20, 'Almacén C-01')
        ]
        await conn.executemany("INSERT INTO inventory (item_name, category, quantity, min_level, location) VALUES ($1, $2, $3, $4, $5)", inv_data)
        
        print("   ✅ Base de datos actualizada con éxito.")
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error DB: {e}")

def update_main_py():
    print("   🔌 Inyectando endpoints en main.py...")
    file_path = 'main.py'
    
    new_endpoints = """
# ==========================================
# 📦 SUMINISTROS, REPORTES Y SEGURIDAD
# ==========================================

from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(creds: LoginRequest):
    \"\"\"Simula autenticación segura\"\"\"
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
    \"\"\"Obtiene estado de tanques e inventario\"\"\"
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
@app.get("/api/reports/daily", response_class=HTMLResponse)
async def generate_daily_report():
    \"\"\"Genera un reporte oficial en HTML para imprimir a PDF\"\"\"
    # En un caso real, aquí consultaríamos la BD para llenar los datos
    html_content = \"\"\"
    <html>
    <head>
        <title>Reporte Diario de Operaciones - RefineryIQ</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 40px; color: #333; }
            .header { text-align: center; border-bottom: 2px solid #3b82f6; padding-bottom: 20px; margin-bottom: 30px; }
            h1 { color: #1e3a8a; margin: 0; }
            .meta { color: #666; font-size: 0.9em; margin-top: 10px; }
            .section { margin-bottom: 30px; }
            h2 { background: #f3f4f6; padding: 10px; border-left: 5px solid #3b82f6; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #f8fafc; }
            .status-ok { color: green; font-weight: bold; }
            .footer { margin-top: 50px; font-size: 0.8em; text-align: center; color: #999; border-top: 1px solid #ddd; padding-top: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>REFINERY IQ - REPORTE DIARIO DE PLANTA</h1>
            <div class="meta">Complejo Refinador Maturín | Fecha de Emisión: HOY | ID: RPT-2025-884</div>
        </div>

        <div class="section">
            <h2>1. Resumen Ejecutivo</h2>
            <p>La planta opera a un <strong>92.4% de eficiencia global</strong>. Se han detectado 3 alertas menores en las últimas 24 horas. Los niveles de suministro de crudo son óptimos para la producción semanal programada.</p>
        </div>

        <div class="section">
            <h2>2. KPIs de Producción</h2>
            <table>
                <tr><th>Unidad</th><th>Producción (bbl)</th><th>Estado</th></tr>
                <tr><td>Destilación Atmosférica (CDU)</td><td>12,450</td><td class="status-ok">OPERATIVO</td></tr>
                <tr><td>Craqueo Catalítico (FCC)</td><td>8,230</td><td class="status-ok">OPTIMO</td></tr>
                <tr><td>Hidrotratamiento (HT)</td><td>4,100</td><td class="status-ok">ESTABLE</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>3. Alertas de Seguridad</h2>
            <ul>
                <li>[08:00 AM] Vibración moderada en Bomba P-101 (Atendida)</li>
                <li>[14:30 PM] Desviación de temperatura en Horno H-201 (En observación)</li>
            </ul>
        </div>
        
        <div class="footer">
            Generado automáticamente por RefineryIQ System v2.1<br>
            Este documento es confidencial y para uso interno exclusivo.
        </div>
        
        <script>window.print();</script> </body>
    </html>
    \"\"\"
    return html_content
"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if "/api/auth/login" not in content:
        if "if __name__" in content:
            content = content.replace("if __name__", new_endpoints + "\n\nif __name__")
        else:
            content += new_endpoints
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("   ✅ Endpoints inyectados correctamente.")
    else:
        print("   ℹ️ Endpoints ya existen.")

if __name__ == "__main__":
    if os.name == 'nt': # Windows fix
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(upgrade_database())
    update_main_py()