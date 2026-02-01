import asyncpg
import asyncio

async def detect_postgres():
    print("🔍 DETECTANDO CONFIGURACIÓN DE POSTGRESQL")
    print("="*50)
    
    # Posibles configuraciones
    configs = [
        {"version": "PostgreSQL 14", "port": 5432, "db": "refineryiq"},
        {"version": "PostgreSQL 14", "port": 5432, "db": "RefineryIQ Local"},
        {"version": "PostgreSQL 18", "port": 5432, "db": "refineryiq"},
        {"version": "PostgreSQL 18", "port": 5432, "db": "RefineryIQ Local"},
        {"version": "PostgreSQL 14", "port": 5433, "db": "refineryiq"},
        {"version": "PostgreSQL 14", "port": 5433, "db": "RefineryIQ Local"},
        {"version": "PostgreSQL 18", "port": 5433, "db": "refineryiq"},
        {"version": "PostgreSQL 18", "port": 5433, "db": "RefineryIQ Local"},
    ]
    
    for config in configs:
        try:
            print(f"\nProbando: {config['version']} - Puerto {config['port']} - BD: {config['db']}")
            conn = await asyncpg.connect(
                user='postgres',
                password='307676',
                database=config['db'],
                host='localhost',
                port=config['port'],
                timeout=3
            )
            print(f"✅ CONEXIÓN EXITOSA!")
            
            # Ver tablas
            tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
            print(f"   Tablas encontradas: {[t['tablename'] for t in tables] if tables else 'Ninguna'}")
            
            await conn.close()
            
            # Recomendar esta configuración
            print(f"\n🎯 RECOMENDACIÓN: Usa esta configuración en main.py:")
            db_encoded = config['db'].replace(' ', '%20')
            print(f'   DATABASE_URL = "postgresql://postgres:307676@localhost:{config["port"]}/{db_encoded}"')
            return config
            
        except Exception as e:
            if "does not exist" in str(e):
                print(f"   ❌ La base de datos '{config['db']}' no existe")
            elif "password authentication" in str(e):
                print(f"   ❌ Error de autenticación (contraseña incorrecta)")
            elif "connection" in str(e).lower():
                print(f"   ❌ No hay servicio en puerto {config['port']}")
            else:
                print(f"   ❌ Error: {str(e)[:100]}")
    
    print("\n" + "="*50)
    print("❌ No se pudo conectar a ninguna configuración")
    print("\n📋 CREA LA BASE DE DATOS 'refineryiq' (sin espacios):")
    print("   1. Abre pgAdmin")
    print("   2. Haz clic derecho en 'Databases' → 'Create' → 'Database'")
    print("   3. Name: refineryiq")
    print("   4. Owner: postgres")
    print("   5. Click 'Save'")
    return None

asyncio.run(detect_postgres())
