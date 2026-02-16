import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from scipy.optimize import minimize
import joblib
import os
import logging
from datetime import datetime

# Configuración de logs específica para este módulo
logger = logging.getLogger("RefineryIQ_Optimization")

class ProcessOptimizer:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.model_path = "ml_models_opt/"
        
        # Crear directorio si no existe
        os.makedirs(self.model_path, exist_ok=True)
        
        # Restricciones operativas reales (Hard Constraints)
        # El optimizador NUNCA sugerirá valores fuera de estos rangos seguros.
        self.constraints = {
            'CDU-101': {
                'temperature': (340.0, 390.0), # °C
                'pressure': (10.0, 25.0),      # Bar
                'flow_rate': (80.0, 150.0)     # m3/h
            },
            'FCC-201': {
                'temperature': (500.0, 560.0),
                'pressure': (2.0, 5.0),
                'flow_rate': (200.0, 300.0)
            }
        }

    async def train_optimization_model(self, unit_id: str):
        """
        Entrena un modelo predictivo (Surrogate Model) que aprende cómo
        las variables afectan la eficiencia. Si no hay datos reales, genera sintéticos.
        """
        logger.info(f"🧠 Entrenando modelo de optimización para {unit_id}...")
        
        try:
            # 1. Generación de Datos Sintéticos de Entrenamiento (Simulación de Historial)
            # En producción, aquí haríamos: df = await get_data_from_db(unit_id)
            n_samples = 5000
            
            # Obtener límites para generar datos realistas
            bounds = self.constraints.get(unit_id, {
                'temperature': (100, 500), 'pressure': (1, 50), 'flow_rate': (50, 500)
            })
            
            # Generar matriz de características (X): [Temp, Pressure, Flow]
            X = np.zeros((n_samples, 3))
            X[:, 0] = np.random.uniform(bounds['temperature'][0], bounds['temperature'][1], n_samples)
            X[:, 1] = np.random.uniform(bounds['pressure'][0], bounds['pressure'][1], n_samples)
            X[:, 2] = np.random.uniform(bounds['flow_rate'][0], bounds['flow_rate'][1], n_samples)
            
            # Generar objetivo (y): Eficiencia Energética (Función física simulada con ruido)
            # Fórmula compleja para que el modelo tenga algo difícil que aprender
            t_norm = (X[:, 0] - bounds['temperature'][0]) / (bounds['temperature'][1] - bounds['temperature'][0])
            p_norm = (X[:, 1] - bounds['pressure'][0]) / (bounds['pressure'][1] - bounds['pressure'][0])
            
            # Eficiencia base no lineal
            y = 90.0 - 10 * (t_norm - 0.6)**2 - 5 * (p_norm - 0.4)**2 + np.random.normal(0, 0.5, n_samples)
            y = np.clip(y, 60.0, 99.9) # Recortar a rangos lógicos

            # 2. Preprocesamiento
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # 3. Entrenamiento (Random Forest es robusto y no lineal)
            model = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42, n_jobs=-1)
            model.fit(X_scaled, y)
            
            # 4. Guardar artefactos
            joblib.dump(model, f"{self.model_path}{unit_id}_opt_model.pkl")
            joblib.dump(scaler, f"{self.model_path}{unit_id}_opt_scaler.pkl")
            
            # Actualizar memoria
            self.models[unit_id] = model
            self.scalers[unit_id] = scaler
            
            score = model.score(X_scaled, y)
            logger.info(f"✅ Modelo {unit_id} entrenado. R2 Score: {score:.4f}")
            return {"status": "trained", "accuracy": f"{score:.2f}", "unit": unit_id}
            
        except Exception as e:
            logger.error(f"❌ Error entrenando modelo: {e}")
            raise e

    def _objective_function(self, x, model, scaler):
        """
        Función objetivo interna que el optimizador matemático intentará minimizar.
        Retornamos eficiencia negativa porque 'minimize' busca valores bajos.
        """
        # x es el vector [temp, press, flow] que prueba el optimizador
        x_reshaped = x.reshape(1, -1)
        x_scaled = scaler.transform(x_reshaped)
        predicted_efficiency = model.predict(x_scaled)[0]
        return -predicted_efficiency 

    async def find_optimal_parameters(self, unit_id: str, current_values: dict):
        """
        Utiliza algoritmos matemáticos (SLSQP) para encontrar la configuración perfecta
        de la máquina, navegando sobre el modelo de IA.
        """
        # Cargar modelo (lazy loading)
        if unit_id not in self.models:
            try:
                self.models[unit_id] = joblib.load(f"{self.model_path}{unit_id}_opt_model.pkl")
                self.scalers[unit_id] = joblib.load(f"{self.model_path}{unit_id}_opt_scaler.pkl")
            except:
                # Si no existe, entrenarlo al vuelo
                await self.train_optimization_model(unit_id)

        model = self.models[unit_id]
        scaler = self.scalers[unit_id]
        bounds_dict = self.constraints.get(unit_id, self.constraints['CDU-101']) # Default si no existe la unidad
        
        # Definir límites para el optimizador matemático
        bounds = [bounds_dict['temperature'], bounds_dict['pressure'], bounds_dict['flow_rate']]
        
        # Punto de partida (Valores actuales)
        x0 = np.array([
            current_values.get('temperature', (bounds[0][0] + bounds[0][1])/2),
            current_values.get('pressure', (bounds[1][0] + bounds[1][1])/2),
            current_values.get('flow_rate', (bounds[2][0] + bounds[2][1])/2)
        ])

        # --- FASE DE OPTIMIZACIÓN MATEMÁTICA ---
        result = minimize(
            self._objective_function, 
            x0, 
            args=(model, scaler), 
            method='SLSQP', # Sequential Least SQuares Programming (Ideal para restricciones)
            bounds=bounds,
            tol=1e-3
        )

        optimal_efficiency = -result.fun # Invertir signo para obtener valor real
        optimal_params = result.x
        
        # Calcular eficiencia actual para comparar
        current_efficiency = model.predict(scaler.transform([x0]))[0]
        
        return {
            "unit_id": unit_id,
            "timestamp": datetime.now().isoformat(),
            "optimization_status": "SUCCESS" if result.success else "PARTIAL",
            "metrics": {
                "current_efficiency": round(float(current_efficiency), 2),
                "potential_efficiency": round(float(optimal_efficiency), 2),
                "gain_percentage": round(float(optimal_efficiency - current_efficiency), 2)
            },
            "current_inputs": {
                "temperature": round(x0[0], 1),
                "pressure": round(x0[1], 1),
                "flow": round(x0[2], 1)
            },
            "recommendations": {
                "set_temperature": round(optimal_params[0], 1),
                "set_pressure": round(optimal_params[1], 1),
                "set_flow_rate": round(optimal_params[2], 1)
            },
            "action_message": f"Ajustar Temp a {optimal_params[0]:.1f}°C y Presión a {optimal_params[1]:.1f} bar para maximizar eficiencia."
        }

# Instancia global (Singleton)
optimizer = ProcessOptimizer()