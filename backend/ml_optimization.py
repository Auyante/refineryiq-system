import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from scipy.optimize import minimize
import joblib
import os
import logging
from datetime import datetime

# Configuración de logs
logger = logging.getLogger("RefineryIQ_Optimization")

class ProcessOptimizer:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.model_path = "ml_models_opt/"
        os.makedirs(self.model_path, exist_ok=True)
        
        # Límites operativos seguros (Constraints) para la optimización
        # Ejemplo: La temperatura del horno no puede pasar de 380°C
        self.constraints = {
            'CDU-101': {
                'temperature': (340.0, 380.0), # Min, Max °C
                'pressure': (10.0, 25.0),      # Min, Max Bar
                'flow_rate': (80.0, 120.0)     # Min, Max m3/h
            }
        }

    async def train_optimization_model(self, unit_id: str):
        """
        Entrena un modelo específico para predecir Eficiencia basado en variables de control.
        """
        logger.info(f"🧠 Entrenando modelo de optimización para {unit_id}...")
        
        # 1. Simular datos históricos (En producción, esto vendría de `process_data`)
        # Variables de entrada (X): Temp, Presión, Flujo
        n_samples = 5000
        X = np.random.rand(n_samples, 3)
        
        # Escalar a rangos reales según constraints
        bounds = self.constraints.get(unit_id, {'temperature': (0,100), 'pressure':(0,10), 'flow_rate':(0,10)})
        X[:, 0] = X[:, 0] * (bounds['temperature'][1] - bounds['temperature'][0]) + bounds['temperature'][0]
        X[:, 1] = X[:, 1] * (bounds['pressure'][1] - bounds['pressure'][0]) + bounds['pressure'][0]
        X[:, 2] = X[:, 2] * (bounds['flow_rate'][1] - bounds['flow_rate'][0]) + bounds['flow_rate'][0]
        
        # Variable objetivo (y): Eficiencia Energética (simulada con una función compleja no lineal)
        # Eficiencia = base + f(temp) + f(press) - penalizaciones
        y = (
            85.0 
            - 0.05 * (X[:, 0] - 360)**2      # Temperatura óptima ~360
            - 0.2 * (X[:, 1] - 18)**2        # Presión óptima ~18
            + 0.1 * X[:, 2]                  # Mayor flujo ayuda un poco
            + np.random.normal(0, 0.5, n_samples) # Ruido
        )
        # Normalizar eficiencia entre 0 y 100
        y = np.clip(y, 60, 99.9)

        # 2. Preprocesamiento
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 3. Entrenamiento (Random Forest Regressor)
        model = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42)
        model.fit(X_scaled, y)
        
        # 4. Guardar
        joblib.dump(model, f"{self.model_path}{unit_id}_opt_model.pkl")
        joblib.dump(scaler, f"{self.model_path}{unit_id}_opt_scaler.pkl")
        
        self.models[unit_id] = model
        self.scalers[unit_id] = scaler
        
        logger.info(f"✅ Modelo de optimización guardado para {unit_id}. R2 Score: {model.score(X_scaled, y):.4f}")
        return {"status": "trained", "accuracy": f"{model.score(X_scaled, y):.2f}"}

    def _objective_function(self, x, model, scaler):
        """Función que queremos MINIMIZAR (para maximizar eficiencia, retornamos negativo)."""
        # x es un array [temp, press, flow]
        x_reshaped = x.reshape(1, -1)
        x_scaled = scaler.transform(x_reshaped)
        predicted_efficiency = model.predict(x_scaled)[0]
        return -predicted_efficiency # Negativo porque scipy.minimize busca el mínimo

    async def find_optimal_parameters(self, unit_id: str, current_values: dict):
        """
        Encuentra los setpoints ideales para maximizar la eficiencia.
        """
        # Cargar modelo si no existe
        if unit_id not in self.models:
            try:
                self.models[unit_id] = joblib.load(f"{self.model_path}{unit_id}_opt_model.pkl")
                self.scalers[unit_id] = joblib.load(f"{self.model_path}{unit_id}_opt_scaler.pkl")
            except:
                await self.train_optimization_model(unit_id)

        model = self.models[unit_id]
        scaler = self.scalers[unit_id]
        bounds_dict = self.constraints.get(unit_id)
        
        # Definir límites para el optimizador [(min, max), (min, max), ...]
        bounds = [bounds_dict['temperature'], bounds_dict['pressure'], bounds_dict['flow_rate']]
        
        # Punto de inicio (valores actuales del sensor)
        x0 = np.array([
            current_values.get('temperature', 350.0),
            current_values.get('pressure', 15.0),
            current_values.get('flow_rate', 100.0)
        ])

        # EJECUTAR OPTIMIZACIÓN (SLSQP es excelente para problemas con límites)
        result = minimize(
            self._objective_function, 
            x0, 
            args=(model, scaler), 
            method='SLSQP', 
            bounds=bounds,
            tol=1e-3
        )

        optimal_efficiency = -result.fun # Invertir signo
        optimal_params = result.x
        
        return {
            "unit_id": unit_id,
            "timestamp": datetime.now().isoformat(),
            "current_efficiency": float(model.predict(scaler.transform([x0]))[0]),
            "optimized_efficiency_projected": round(optimal_efficiency, 2),
            "improvement_potential": round(optimal_efficiency - model.predict(scaler.transform([x0]))[0], 2),
            "recommendations": {
                "set_temperature": round(optimal_params[0], 1),
                "set_pressure": round(optimal_params[1], 1),
                "set_flow_rate": round(optimal_params[2], 1)
            },
            "status": "OPTIMAL_FOUND" if result.success else "OPTIMIZATION_FAILED"
        }

# Instancia global
optimizer = ProcessOptimizer()