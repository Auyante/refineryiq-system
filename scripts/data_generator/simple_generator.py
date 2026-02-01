import asyncio
import random
from datetime import datetime, timezone  # Cambiado de datetime.utcnow
import aiohttp
import json
import sys

class RefineryDataGenerator:
    def __init__(self):
        self.units = ['CDU-101', 'FCC-201', 'HT-301']
        self.tags = {
            'CDU-101': ['TEMP_TOWER', 'PRESS_TOWER', 'FLOW_FEED'],
            'FCC-201': ['TEMP_REACTOR', 'CATALYST_ACT'],
            'HT-301': ['TEMP_HYDRO', 'H2_PRESS']
        }
        
    def generate_reading(self, unit_id, tag_id):
        """Genera una lectura sintética basada en parámetros reales"""
        base_values = {
            'TEMP_TOWER': (350, 450),      # °C
            'PRESS_TOWER': (2.5, 5.0),     # bar
            'FLOW_FEED': (8000, 12000),    # bbl/day
            'TEMP_REACTOR': (480, 550),    # °C
            'CATALYST_ACT': (70, 95),      # %
            'TEMP_HYDRO': (300, 380),      # °C
            'H2_PRESS': (30, 50)           # bar
        }
        
        min_val, max_val = base_values.get(tag_id, (0, 100))
        value = random.uniform(min_val, max_val)
        
        # Usar datetime.now con timezone UTC en lugar de utcnow
        return {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "unit_id": unit_id,
            "tag_id": tag_id,
            "value": round(value, 2),
            "quality": 1
        }
    
    async def send_batch_with_retry(self, session, batch, max_retries=3):
        """Envía datos con reintentos en caso de error"""
        for attempt in range(max_retries):
            try:
                async with session.post(
                    'http://localhost:8000/api/data/ingest',
                    json=batch,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        print(f"✅ Datos enviados: {len(batch)} registros")
                        return True
                    else:
                        print(f"⚠️  Intento {attempt + 1}: Error HTTP {response.status}")
                        await asyncio.sleep(2)  # Esperar antes de reintentar
            except aiohttp.ClientConnectorError:
                print(f"⚠️  Intento {attempt + 1}: No se puede conectar al servidor")
                await asyncio.sleep(5)  # Esperar más tiempo si no hay conexión
            except Exception as e:
                print(f"⚠️  Intento {attempt + 1}: Error: {type(e).__name__}")
                await asyncio.sleep(2)
        
        print(f"❌ Fallo después de {max_retries} intentos")
        return False
    
    async def run(self, interval_seconds=5):
        """Ejecuta generación continua de datos"""
        print("=" * 50)
        print("GENERADOR DE DATOS SINTÉTICOS - REFINERYIQ")
        print("=" * 50)
        print("Unidades de proceso:")
        print("  • CDU-101: Destilación Atmosférica")
        print("  • FCC-201: Craqueo Catalítico")
        print("  • HT-301: Hidrotratamiento")
        print(f"Intervalo: {interval_seconds} segundos")
        print("=" * 50)
        
        connector = aiohttp.TCPConnector(limit_per_host=3)  # Limitar conexiones
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                while True:
                    # Generar lote de datos
                    batch = []
                    for unit_id in self.units:
                        for tag_id in self.tags[unit_id]:
                            batch.append(self.generate_reading(unit_id, tag_id))
                    
                    # Enviar datos con manejo de errores
                    await self.send_batch_with_retry(session, batch)
                    
                    # Esperar para el próximo envío
                    await asyncio.sleep(interval_seconds)
                    
            except KeyboardInterrupt:
                print("\n🛑 Generador detenido por el usuario")
            except Exception as e:
                print(f"\n💥 Error crítico: {e}")
                print("Reinicia el generador de datos si es necesario")

async def main():
    generator = RefineryDataGenerator()
    await generator.run(interval_seconds=5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Programa terminado")
    except Exception as e:
        print(f"\n🔥 Error fatal: {e}")
        input("Presiona Enter para salir...")