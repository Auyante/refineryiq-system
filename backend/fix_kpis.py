import asyncio
import asyncpg
import sys

async def fix_kpis_table():
    print("🔧 REPARANDO TABLA KPIS...")
    db_url = "postgresql://postgres:307676@localhost:5432/refineryiq"
    
    try:
        conn = await asyncpg.connect(db_url)
        
        # 1. Eliminar tabla antigua si existe
        print("🗑️ Eliminando tabla kpis antigua...")
        await conn.execute("DROP TABLE IF EXISTS kpis CASCADE")
        
        # 2. Crear tabla nueva con la estructura correcta
        print("🔨 Creando tabla kpis nueva...")
        await conn.execute('''
            CREATE TABLE kpis (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                unit_id VARCHAR(20) NOT NULL,
                energy_efficiency FLOAT,
                throughput FLOAT,
                quality_score FLOAT,
                maintenance_score FLOAT,
                CONSTRAINT fk_kpis_unit FOREIGN KEY (unit_id) REFERENCES process_units(unit_id)
            )
        ''')
        
        # 3. Crear índice para velocidad
        await conn.execute("CREATE INDEX idx_kpis_timestamp ON kpis(timestamp DESC)")
        
        print("✅ Tabla 'kpis' reconstruida correctamente con todas las columnas.")
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(fix_kpis_table())