import numpy as np
from datetime import datetime, timedelta
import asyncpg
import json
from typing import Dict, List
import random

class EnergyOptimizationSystem:
    def __init__(self):
        self.benchmarks = {
            'CDU-101': {'energy_per_barrel': 45, 'target': 42},
            'FCC-201': {'energy_per_barrel': 65, 'target': 60},
            'HT-301': {'energy_per_barrel': 35, 'target': 32}
        }
    
    async def analyze_unit_energy(self, db_conn, unit_id: str, hours: int = 24):
        """Analiza eficiencia energética de una unidad"""
        try:
            if unit_id not in self.benchmarks:
                return {
                    "error": f"Unidad {unit_id} no encontrada en benchmarks",
                    "unit_id": unit_id,
                    "timestamp": datetime.now().isoformat()
                }
            
            benchmark = self.benchmarks[unit_id]['energy_per_barrel']
            target = self.benchmarks[unit_id]['target']
            
            # Simular consumo (en un sistema real, esto vendría de la BD)
            avg_consumption = benchmark * (0.9 + random.random() * 0.2)
            
            # Calcular métricas
            efficiency_score = max(0, min(100, (target / avg_consumption) * 100))
            
            # Identificar ineficiencias
            inefficiencies = []
            if avg_consumption > benchmark * 1.1:
                inefficiencies.append({
                    'type': 'HIGH_CONSUMPTION',
                    'severity': 'HIGH',
                    'message': f"Consumo {avg_consumption:.1f} kWh/bbl excede benchmark {benchmark}",
                    'savings_potential': round(avg_consumption - target, 2)
                })
            
            # Generar recomendaciones
            recommendations = []
            if avg_consumption > benchmark:
                recommendations.append({
                    'action': 'OPTIMIZE_HEAT_EXCHANGERS',
                    'priority': 'HIGH',
                    'description': 'Limpiar y optimizar intercambiadores de calor',
                    'expected_savings': '3-5%',
                    'implementation_time': '2-3 días'
                })
            
            analysis = {
                'unit_id': unit_id,
                'analysis_date': datetime.now().date().isoformat(),
                'avg_energy_consumption': round(avg_consumption, 2),
                'benchmark': benchmark,
                'target': target,
                'efficiency_score': round(efficiency_score, 2),
                'status': self.get_efficiency_status(efficiency_score),
                'inefficiencies': inefficiencies,
                'recommendations': recommendations,
                'estimated_savings': round(max(0, avg_consumption - target), 2),
                'timestamp': datetime.now().isoformat()
            }
            
            # Guardar análisis
            await self.save_energy_analysis(db_conn, analysis)
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error en análisis energético: {e}")
            return None
    
    def get_efficiency_status(self, efficiency_score: float):
        """Determina estado de eficiencia"""
        if efficiency_score >= 95:
            return 'EXCELLENT'
        elif efficiency_score >= 85:
            return 'GOOD'
        elif efficiency_score >= 70:
            return 'NEEDS_IMPROVEMENT'
        else:
            return 'POOR'
    
    async def save_energy_analysis(self, db_conn, analysis: Dict):
        """Guarda análisis energético en base de datos"""
        try:
            await db_conn.execute('''
                INSERT INTO energy_analysis 
                (unit_id, analysis_date, avg_energy_consumption, benchmark, target,
                 efficiency_score, status, inefficiencies, recommendations, estimated_savings, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ''',
                analysis['unit_id'],
                analysis['analysis_date'],
                analysis['avg_energy_consumption'],
                analysis['benchmark'],
                analysis['target'],
                analysis['efficiency_score'],
                analysis['status'],
                json.dumps(analysis['inefficiencies']),
                json.dumps(analysis['recommendations']),
                analysis['estimated_savings'],
                analysis['timestamp']
            )
        except Exception as e:
            print(f"⚠️ Error guardando análisis energético: {e}")
            # Si la tabla no existe, crearla
            if 'relation "energy_analysis" does not exist' in str(e):
                await self.create_energy_analysis_table(db_conn)
                # Intentar de nuevo
                await self.save_energy_analysis(db_conn, analysis)
    
    async def create_energy_analysis_table(self, db_conn):
        """Crea la tabla energy_analysis si no existe"""
        try:
            await db_conn.execute('''
                CREATE TABLE IF NOT EXISTS energy_analysis (
                    id SERIAL PRIMARY KEY,
                    unit_id VARCHAR(20),
                    analysis_date DATE,
                    avg_energy_consumption FLOAT,
                    benchmark FLOAT,
                    target FLOAT,
                    efficiency_score FLOAT,
                    status VARCHAR(20),
                    inefficiencies JSONB,
                    recommendations JSONB,
                    estimated_savings FLOAT,
                    timestamp TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            print("✅ Tabla 'energy_analysis' creada")
        except Exception as e:
            print(f"❌ Error creando tabla energy_analysis: {e}")
    
    async def get_recent_analysis(self, db_conn, unit_id: str = None, limit: int = 5):
        """Obtiene análisis energéticos recientes"""
        try:
            if unit_id:
                rows = await db_conn.fetch('''
                    SELECT * FROM energy_analysis 
                    WHERE unit_id = $1
                    ORDER BY timestamp DESC 
                    LIMIT $2
                ''', unit_id, limit)
            else:
                rows = await db_conn.fetch('''
                    SELECT * FROM energy_analysis 
                    ORDER BY timestamp DESC 
                    LIMIT $1
                ''', limit)
            
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Error obteniendo análisis energéticos: {e}")
            return []

# Instancia global
energy_system = EnergyOptimizationSystem()