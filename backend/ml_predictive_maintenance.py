import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import asyncpg
import asyncio
from typing import Dict, List
import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

class PredictiveMaintenanceSystem:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.model_path = "backend/ml_models/"
        os.makedirs(self.model_path, exist_ok=True)
        
    async def initialize_models(self, db_conn):
        """Inicializa o carga modelos existentes"""
        equipment_types = ['PUMP', 'COMPRESSOR', 'VALVE', 'HEAT_EXCHANGER']
        
        for eq_type in equipment_types:
            model_file = f"{self.model_path}{eq_type}_model.pkl"
            scaler_file = f"{self.model_path}{eq_type}_scaler.pkl"
            
            if os.path.exists(model_file):
                self.models[eq_type] = joblib.load(model_file)
                self.scalers[eq_type] = joblib.load(scaler_file)
                print(f"✅ Modelo cargado para {eq_type}")
            else:
                # Crear nuevo modelo
                self.models[eq_type] = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42
                )
                self.scalers[eq_type] = StandardScaler()
                print(f"🆕 Nuevo modelo creado para {eq_type}")
    
    async def train_models(self, db_conn):
        """Entrena modelos con datos históricos"""
        print("🧠 Entrenando modelos de mantenimiento predictivo...")
        
        equipment_data = {
            'PUMP': {
                'features': ['vibration', 'temperature', 'pressure', 'flow_rate', 'power_consumption'],
                'failure_rate': 0.05
            },
            'COMPRESSOR': {
                'features': ['vibration_x', 'vibration_y', 'temperature', 'pressure_ratio', 'efficiency'],
                'failure_rate': 0.03
            },
            'VALVE': {
                'features': ['position_error', 'response_time', 'leakage_rate', 'actuator_health'],
                'failure_rate': 0.02
            }
        }
        
        for eq_type, config in equipment_data.items():
            # Generar datos sintéticos de entrenamiento
            n_samples = 1000
            n_features = len(config['features'])
            
            X_train = np.random.randn(n_samples, n_features)
            
            # Generar etiquetas: 0=normal, 1=falla
            y_train = np.random.binomial(1, config['failure_rate'], n_samples)
            
            # Escalar características
            X_scaled = self.scalers[eq_type].fit_transform(X_train)
            
            # Entrenar modelo
            self.models[eq_type].fit(X_scaled, y_train)
            
            # Guardar modelo
            joblib.dump(self.models[eq_type], f"{self.model_path}{eq_type}_model.pkl")
            joblib.dump(self.scalers[eq_type], f"{self.model_path}{eq_type}_scaler.pkl")
            
            print(f"✅ Modelo entrenado para {eq_type}: {np.sum(y_train)} fallas en {n_samples} muestras")
        
        return {"status": "success", "message": "Modelos entrenados exitosamente"}
    
    async def predict_equipment_health(self, db_conn, equipment_id: str, equipment_type: str, unit_id: str):
        """Predice la salud de un equipo específico"""
        
        # Obtener características recientes del equipo
        features = await self.get_equipment_features(db_conn, equipment_id, equipment_type)
        
        if equipment_type not in self.models:
            return {
                "equipment_id": equipment_id,
                "equipment_type": equipment_type,
                "error": f"No hay modelo para {equipment_type}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Escalar características
        features_scaled = self.scalers[equipment_type].transform([features])
        
        # Predecir
        model = self.models[equipment_type]
        probability = model.predict_proba(features_scaled)[0][1]
        prediction = model.predict(features_scaled)[0]
        
        # Generar resultado
        result = {
            "equipment_id": equipment_id,
            "equipment_type": equipment_type,
            "unit_id": unit_id,
            "failure_probability": round(float(probability) * 100, 2),
            "prediction": "FALLA INMINENTE" if prediction == 1 else "OPERACIÓN NORMAL",
            "confidence": round(model.predict_proba(features_scaled).max() * 100, 2),
            "timestamp": datetime.now().isoformat(),
            "recommendation": self.generate_recommendation(equipment_type, probability),
            "features": features
        }
        
        # Guardar predicción en base de datos
        await self.save_prediction(db_conn, result)
        
        return result
    
    async def get_equipment_features(self, db_conn, equipment_id: str, equipment_type: str):
        """Obtiene características del equipo"""
        # Características simuladas
        if equipment_type == 'PUMP':
            return [
                np.random.normal(2.5, 0.5),
                np.random.normal(75, 10),
                np.random.normal(15, 2),
                np.random.normal(100, 10),
                np.random.normal(55, 5)
            ]
        elif equipment_type == 'COMPRESSOR':
            return [
                np.random.normal(3.0, 0.6),
                np.random.normal(2.8, 0.5),
                np.random.normal(85, 15),
                np.random.normal(3.2, 0.3),
                np.random.normal(78, 5)
            ]
        else:  # VALVE
            return [
                np.random.normal(0.5, 0.2),
                np.random.normal(2.0, 0.5),
                np.random.normal(0.1, 0.05),
                np.random.normal(95, 3),
                np.random.normal(25, 5)
            ]
    
    def generate_recommendation(self, equipment_type: str, probability: float):
        """Genera recomendaciones basadas en probabilidad de falla"""
        if probability > 0.8:
            return f"DETENER EQUIPO {equipment_type} PARA MANTENIMIENTO INMEDIATO"
        elif probability > 0.6:
            return f"PROGRAMAR MANTENIMIENTO DE {equipment_type} EN PRÓXIMAS 24H"
        elif probability > 0.4:
            return f"MONITOREAR {equipment_type} DE CERCA - RIESGO MODERADO"
        else:
            return f"{equipment_type} OPERANDO NORMALMENTE - CONTINUAR MONITOREO"
    
    async def save_prediction(self, db_conn, prediction: Dict):
        """Guarda predicción en la base de datos"""
        await db_conn.execute('''
            INSERT INTO maintenance_predictions 
            (equipment_id, equipment_type, unit_id, failure_probability, 
             prediction, confidence, recommendation, timestamp, features)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ''',
            prediction['equipment_id'],
            prediction['equipment_type'],
            prediction['unit_id'],
            prediction['failure_probability'],
            prediction['prediction'],
            prediction['confidence'],
            prediction['recommendation'],
            prediction['timestamp'],
            json.dumps(prediction['features'])
        )
    
    async def get_recent_predictions(self, db_conn, limit: int = 10):
        """Obtiene predicciones recientes"""
        rows = await db_conn.fetch('''
            SELECT * FROM maintenance_predictions 
            ORDER BY timestamp DESC 
            LIMIT $1
        ''', limit)
        
        return [dict(row) for row in rows]
    
    async def analyze_all_equipment(self, db_conn):
        """Analiza todos los equipos críticos"""
        equipment_list = [
            {"id": "PUMP-CDU-101", "type": "PUMP", "unit": "CDU-101"},
            {"id": "PUMP-CDU-102", "type": "PUMP", "unit": "CDU-101"},
            {"id": "COMP-FCC-201", "type": "COMPRESSOR", "unit": "FCC-201"},
            {"id": "VALVE-HT-301", "type": "VALVE", "unit": "HT-301"},
        ]
        
        results = []
        for eq in equipment_list:
            prediction = await self.predict_equipment_health(
                db_conn, eq['id'], eq['type'], eq['unit']
            )
            results.append(prediction)
        
        return results

# Instancia global del sistema
pm_system = PredictiveMaintenanceSystem()
