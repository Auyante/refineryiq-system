import os
import asyncio
import asyncpg

async def setup_db():
    print("🏗️ ACTUALIZANDO BASE DE DATOS FINAL...")
    db_url = "postgresql://postgres:307676@localhost:5432/refineryiq"
    conn = await asyncpg.connect(db_url)
    
    # 1. Tablas de Suministros (Tanques e Inventario)
    await conn.execute("DROP TABLE IF EXISTS tanks CASCADE")
    await conn.execute("DROP TABLE IF EXISTS inventory CASCADE")
    
    await conn.execute('''
        CREATE TABLE tanks (id SERIAL PRIMARY KEY, name VARCHAR(50), product VARCHAR(50), current_level FLOAT, capacity FLOAT, status VARCHAR(20));
        CREATE TABLE inventory (id SERIAL PRIMARY KEY, item_name VARCHAR(100), category VARCHAR(50), quantity INT, min_level INT, location VARCHAR(50));
    ''')
    
    # 2. Datos Iniciales
    await conn.executemany("INSERT INTO tanks (name, product, current_level, capacity, status) VALUES ($1, $2, $3, $4, $5)", [
        ('TK-101', 'Crudo Pesado', 85000, 100000, 'FILLING'), ('TK-102', 'Diesel', 78000, 80000, 'STATIC'), ('TK-201', 'Gasolina', 45000, 80000, 'DRAINING')
    ])
    await conn.executemany("INSERT INTO inventory (item_name, category, quantity, min_level, location) VALUES ($1, $2, $3, $4, $5)", [
        ('Válvula 4"', 'REPUESTOS', 2, 5, 'Almacén A'), ('Sello Mecánico', 'REPUESTOS', 8, 3, 'Almacén B'), ('Catalizador', 'QUÍMICOS', 4500, 1000, 'Silo 1')
    ])
    print("✅ Base de Datos Lista.")
    await conn.close()

def update_api():
    print("🔌 ACTUALIZANDO API (main.py)...")
    code = """
# --- BLOQUE FINAL: SEGURIDAD Y SUMINISTROS ---
from pydantic import BaseModel
from fastapi.responses import HTMLResponse

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(creds: LoginRequest):
    if creds.username == "admin" and creds.password == "admin123":
        return {"token": "jwt-123", "user": "Administrador", "role": "admin"}
    from fastapi import HTTPException
    raise HTTPException(status_code=401, detail="Credenciales incorrectas")

@app.get("/api/supplies/data")
async def get_supplies():
    conn = await get_db()
    tanks = await conn.fetch("SELECT * FROM tanks ORDER BY name")
    inv = await conn.fetch("SELECT * FROM inventory ORDER BY quantity ASC")
    await conn.close()
    return {"tanks": [dict(t) for t in tanks], "inventory": [dict(i) for i in inv]}

@app.get("/api/reports/daily", response_class=HTMLResponse)
async def report():
    return \"\"\"<html><body onload="window.print()"><h1>REPORTE OFICIAL REFINERYIQ</h1><p>Eficiencia Global: 94%</p><p>Estado: OPERATIVO</p></body></html>\"\"\"
"""
    # Agregar al main.py si no existe
    with open('main.py', 'r', encoding='utf-8') as f: content = f.read()
    if "/api/auth/login" not in content:
        with open('main.py', 'w', encoding='utf-8') as f: f.write(content.replace("if __name__", code + "\n\nif __name__"))
        print("✅ API Actualizada.")
    else: print("ℹ️ API ya estaba actualizada.")

if __name__ == "__main__":
    if os.name == 'nt': asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(setup_db())
    update_api()