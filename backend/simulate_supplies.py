import asyncio
import asyncpg
import random
import time

async def animate_supplies():
    print("🌊 INICIANDO SIMULACIÓN DE SUMINISTROS (Tanques e Inventario)...")
    print("   (Presiona Ctrl + C para detener)")
    
    db_url = "postgresql://postgres:307676@localhost:5432/refineryiq"
    
    try:
        conn = await asyncpg.connect(db_url)
        
        while True:
            # 1. SIMULAR TANQUES (Llenado y Vaciado)
            tanks = await conn.fetch("SELECT id, current_level, capacity, status FROM tanks")
            
            for t in tanks:
                new_level = t['current_level']
                new_status = t['status']
                
                # Lógica de física simple
                if t['status'] == 'FILLING':
                    change = random.uniform(500, 1500) # Llenar rápido
                    new_level += change
                    if new_level >= t['capacity'] * 0.98: # Si se llena, detener
                        new_level = t['capacity']
                        new_status = 'DRAINING' # Empezar a vaciar
                        
                elif t['status'] == 'DRAINING':
                    change = random.uniform(300, 800) # Vaciar consumo planta
                    new_level -= change
                    if new_level <= t['capacity'] * 0.15: # Si baja mucho
                        new_status = 'FILLING' # Empezar a llenar
                
                else: # STATIC
                    if random.random() > 0.8: # A veces cambiar estado
                        new_status = random.choice(['FILLING', 'DRAINING'])

                # Guardar cambios
                await conn.execute(
                    "UPDATE tanks SET current_level = $1, status = $2 WHERE id = $3",
                    new_level, new_status, t['id']
                )

            # 2. SIMULAR CONSUMO DE INVENTARIO
            # Cada 5 segundos, alguien saca un repuesto
            if random.random() > 0.5:
                # Elegir item al azar
                items = await conn.fetch("SELECT id, quantity FROM inventory WHERE quantity > 0")
                if items:
                    item = random.choice(items)
                    await conn.execute(
                        "UPDATE inventory SET quantity = quantity - 1 WHERE id = $1", 
                        item['id']
                    )
                    print(f"   📦 Item {item['id']} consumido. Quedan: {item['quantity']-1}")

            print("   💧 Niveles de tanques actualizados...")
            await asyncio.sleep(2) # Esperar 2 segundos

    except KeyboardInterrupt:
        print("\n🛑 Simulación detenida.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(animate_supplies())