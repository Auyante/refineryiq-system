import os
import logging
import asyncio
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from scipy.optimize import minimize
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text

# Configuración de Logs
logger = logging.getLogger("RefineryIQ_ML")
logging.basicConfig(level=logging.INFO)

# ==============================================================================
# CONFIGURACIÓN DE BASE DE DATOS Y MAPEO DE SENSORES
# ==============================================================================

# Detectar URL de Base de Datos (Misma lógica que auto_generator.py)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:307676@localhost:5432/refineryiq")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Motor síncrono para Pandas
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Mapeo de Tags Físicos a Variables del Modelo
# Esto conecta los nombres "genericos" del ML con los Tags reales de la planta.
UNIT_TAG_MAPPING = {
    'CDU-101': {
        'temperature': 'TI-101', # Temp. Salida Horno
        'pressure':    'PI-103', # Presión Torre
        'flow_rate':   'FI-102'  # Flujo Carga Crudo
    },
    # Puedes agregar más unidades aquí en el futuro
    'FCC-201': {
        'temperature': 'TI-203',
        'pressure':    'PI-201',
        'flow_rate':   None      # Si falta un sensor, se manejará como 0
    }
}

class ProcessOptimizer:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.model_path = "ml_models_opt/"
        os.makedirs(self.model_path, exist_ok=True)
        
        # Restricciones Operativas (Hard Constraints)
        self.constraints = {
            'CDU-101': {
                'temperature': (340.0, 365.0), # Rango seguro estricto
                'pressure': (15.0, 25.0),
                'flow_rate': (9000.0, 11000.0)
            }
        }

    def _fetch_data_from_db(self, unit_id: str):
        """
        Extrae datos reales de PostgreSQL y los formatea para entrenamiento.
        Realiza Pivot de tablas y cruce de timestamps (Merge AsOf).
        """
        tags_map = UNIT_TAG_MAPPING.get(unit_id)
        if not tags_map:
            raise ValueError(f"No hay configuración de sensores para {unit_id}")

        logger.info(f"📡 Consultando historial de DB para {unit_id}...")
        
        # Filtrar tags que no sean None
        tag_ids = [v for v in tags_map.values() if v]
        if not tag_ids:
            logger.warning("⚠️ No hay tags configurados para esta unidad.")
            return None

        # 1. Traer datos de sensores (Formato Largo)
        # CORRECCIÓN: Cambiar 'time' por 'timestamp' en SELECT y condiciones
        query_sensors = text("""
            SELECT timestamp, tag_id, value 
            FROM process_data 
            WHERE unit_id = :uid 
            AND tag_id = ANY(:tags)
            AND timestamp > NOW() - INTERVAL '7 days'
            ORDER BY timestamp ASC
        """)
        
        # 2. Traer KPIs (Target)
        query_kpis = text("""
            SELECT timestamp, energy_efficiency as target
            FROM kpis
            WHERE unit_id = :uid
            AND timestamp > NOW() - INTERVAL '7 days'
            ORDER BY timestamp ASC
        """)

        try:
            with engine.connect() as conn:
                df_sensors = pd.read_sql(query_sensors, conn, params={"uid": unit_id, "tags": tag_ids})
                df_kpis = pd.read_sql(query_kpis, conn, params={"uid": unit_id})
        except Exception as e:
            logger.error(f"Error al leer de la base de datos: {e}")
            return None

        if df_sensors.empty or df_kpis.empty:
            logger.warning("⚠️ Base de datos vacía. Usando datos sintéticos para evitar crash.")
            return None

        # 3. Pivotar Sensores (De filas a columnas)
        df_sensors['timestamp'] = pd.to_datetime(df_sensors['timestamp'])
        df_kpis['timestamp'] = pd.to_datetime(df_kpis['timestamp'])

        # Pivot: index=timestamp, columns=tag_id, values=value
        df_pivot = df_sensors.pivot_table(index='timestamp', columns='tag_id', values='value')
        df_pivot = df_pivot.sort_index()

        # 4. Unir Sensores con KPIs (Merge AsOf)
        # Usamos merge_asof para unir por tiempos cercanos (tolerancia 5 min)
        df_final = pd.merge_asof(
            df_kpis, 
            df_pivot, 
            on='timestamp', 
            direction='nearest', 
            tolerance=pd.Timedelta('5 minutes')
        )
        
        # Limpieza
        df_final = df_final.dropna()
        
        # Renombrar columnas de Tags a Nombres Genéricos (temp, press, flow)
        rename_map = {v: k for k, v in tags_map.items() if v}
        df_final.rename(columns=rename_map, inplace=True)
        
        logger.info(f"✅ Dataset preparado: {len(df_final)} registros reales encontrados.")
        return df_final

    async def train_optimization_model(self, unit_id: str):
        """
        Entrena el modelo usando datos reales. Ejecuta la parte pesada en un Thread aparte
        para no bloquear el servidor FastAPI.
        """
        loop = asyncio.get_event_loop()
        # Ejecutar en thread pool porque pandas/sklearn son bloqueantes
        return await loop.run_in_executor(None, self._train_sync, unit_id)

    def _train_sync(self, unit_id: str):
        """Lógica síncrona de entrenamiento"""
        try:
            # 1. Obtener Datos
            df = self._fetch_data_from_db(unit_id)
            
            # Fallback a datos sintéticos si no hay suficientes datos reales (<50 registros)
            if df is None or len(df) < 50:
                logger.warning(f"⚠️ Insuficientes datos reales para {unit_id}. Entrenando modo Simulación.")
                return self._train_synthetic(unit_id)

            # 2. Definir Features (X) y Target (y)
            features = ['temperature', 'pressure', 'flow_rate']
            # Asegurar que existan las columnas, si falta alguna rellenar con media
            for f in features:
                if f not in df.columns:
                    df[f] = 0.0

            X = df[features].values
            y = df['target'].values

            # 3. Preprocesamiento
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # 4. Entrenar Random Forest
            model = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42)
            model.fit(X_scaled, y)

            # 5. Guardar
            joblib.dump(model, f"{self.model_path}{unit_id}_opt_model.pkl")
            joblib.dump(scaler, f"{self.model_path}{unit_id}_opt_scaler.pkl")
            
            self.models[unit_id] = model
            self.scalers[unit_id] = scaler
            
            score = model.score(X_scaled, y)
            logger.info(f"🎉 Modelo {unit_id} entrenado con DATOS REALES. R2: {score:.4f}")
            return {"status": "trained_real", "accuracy": f"{score:.2f}", "samples": len(df)}

        except Exception as e:
            logger.error(f"❌ Error entrenando modelo: {e}")
            # Si falla algo crítico, fallback a sintético para no detener el sistema
            return self._train_synthetic(unit_id)

    def _train_synthetic(self, unit_id: str):
        """Generador de respaldo (Tu código anterior)"""
        logger.info("🤖 Iniciando entrenamiento sintético de respaldo...")
        # Generar datos sintéticos (puramente para que el sistema no falle)
        np.random.seed(42)
        X = np.random.rand(100, 3) * 10  # Valores aleatorios
        y = 100 - (X[:, 0] * 2 + X[:, 1] * 0.5 + X[:, 2] * 0.1) + np.random.randn(100) * 2
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X_scaled, y)
        
        self.models[unit_id] = model
        self.scalers[unit_id] = scaler
        
        # Guardar modelos sintéticos también
        joblib.dump(model, f"{self.model_path}{unit_id}_opt_model.pkl")
        joblib.dump(scaler, f"{self.model_path}{unit_id}_opt_scaler.pkl")
        
        return {"status": "trained_synthetic", "reason": "No DB data or error"}

    def _objective_function(self, x, model, scaler):
        x_reshaped = x.reshape(1, -1)
        x_scaled = scaler.transform(x_reshaped)
        return -model.predict(x_scaled)[0]

    async def find_optimal_parameters(self, unit_id: str, current_values: dict):
        """
        Encuentra el punto óptimo de operación.
        """
        # Cargar modelo (lazy)
        if unit_id not in self.models:
            try:
                self.models[unit_id] = joblib.load(f"{self.model_path}{unit_id}_opt_model.pkl")
                self.scalers[unit_id] = joblib.load(f"{self.model_path}{unit_id}_opt_scaler.pkl")
                logger.info(f"✅ Modelo cargado desde archivo para {unit_id}")
            except FileNotFoundError:
                logger.info(f"⚠️ No se encontró modelo guardado para {unit_id}. Entrenando...")
                await self.train_optimization_model(unit_id)
            except Exception as e:
                logger.error(f"Error cargando modelo: {e}")
                await self.train_optimization_model(unit_id)

        # Verificar que el modelo esté disponible
        if unit_id not in self.models:
            raise RuntimeError(f"No se pudo obtener un modelo para {unit_id}")

        model = self.models[unit_id]
        scaler = self.scalers[unit_id]
        
        # Límites operativos de seguridad
        constraints = self.constraints.get(unit_id, self.constraints.get('CDU-101', {
            'temperature': (300, 400),
            'pressure': (10, 30),
            'flow_rate': (8000, 12000)
        }))
        
        bounds = [constraints['temperature'], constraints['pressure'], constraints['flow_rate']]
        
        # Valores iniciales (Setpoints actuales)
        x0 = np.array([
            current_values.get('temperature', constraints['temperature'][0]),
            current_values.get('pressure', constraints['pressure'][0]),
            current_values.get('flow_rate', constraints['flow_rate'][0])
        ])

        # Optimización
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: minimize(
            self._objective_function, 
            x0, 
            args=(model, scaler), 
            method='SLSQP', 
            bounds=bounds,
            tol=1e-3
        ))

        # Resultados
        optimal_eff = -result.fun
        current_eff = -self._objective_function(x0, model, scaler)
        
        return {
            "unit_id": unit_id,
            "timestamp": datetime.now().isoformat(),
            "optimization_source": "real_data" if hasattr(self, '_last_train_source') and self._last_train_source == 'real' else "synthetic",
            "metrics": {
                "current_efficiency": round(float(current_eff), 2),
                "potential_efficiency": round(float(optimal_eff), 2),
                "gain_percentage": round(float(optimal_eff - current_eff), 2)
            },
            "recommendations": {
                "set_temperature": round(result.x[0], 1),
                "set_pressure": round(result.x[1], 1),
                "set_flow_rate": round(result.x[2], 1)
            }
        }

optimizer = ProcessOptimizer()