"""
RefineryIQ AI Core — Real-Time Inference Engine
=================================================
Production-grade inference pipeline with:
  • Per-equipment sliding window buffers (ready for MQTT/Kafka)
  • Lazy model loading from MLflow registry (with local fallback)
  • Combined RUL + anomaly score output
  • SHAP explanations and human-readable narratives
  • Async-compatible (heavy inference offloaded to thread pool)
  • Memory-safe: loads one model at a time on constrained environments
"""

import asyncio
import gc
import logging
import os
import time
import numpy as np
import torch
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

from ai_core.config import (
    EQUIPMENT_PROFILES,
    MAX_BUFFER_SIZE,
    WINDOW_SIZE,
    RUL_CRITICAL,
    RUL_WARNING,
    RUL_CAUTION,
    MEMORY_CONSTRAINED,
)
from ai_core.models import LSTMRULModel, ConvAutoencoder
from ai_core.explainability import SHAPExplainer
from ai_core.mlflow_manager import MLflowManager

logger = logging.getLogger("RefineryIQ_Inference")

LOCAL_MODEL_DIR = "ml_models_v2"


class PredictiveMaintenanceEngine:
    """
    Real-time predictive maintenance inference engine.

    Manages per-equipment sliding window buffers, loads the latest
    production models from MLflow (with local fallback), and produces
    predictions enriched with SHAP explanations.

    On memory-constrained environments, models are loaded lazily (one at
    a time) and unloaded after use to keep RAM usage low.
    """

    def __init__(self):
        self.device = torch.device("cpu")  # Inference always on CPU for latency
        self.mlflow = MLflowManager()

        # Models indexed by equipment_type (may be empty on constrained envs)
        self.rul_models: Dict[str, torch.nn.Module] = {}
        self.ae_models: Dict[str, ConvAutoencoder] = {}
        self.explainers: Dict[str, SHAPExplainer] = {}

        # Normalization stats indexed by equipment_type
        self.norm_stats: Dict[str, Dict] = {}

        # Sliding window buffers indexed by equipment_id
        self.buffers: Dict[str, deque] = {}

        # Background data for SHAP (small sample per equipment_type)
        self.background_data: Dict[str, np.ndarray] = {}

        # Track which model types are available (registered in MLflow/local)
        self._available_rul: set = set()
        self._available_ae: set = set()

        # Track the last loaded model type (for lazy unloading)
        self._last_loaded_type: Optional[str] = None

        self._initialized = False

    # ================================================================== #
    #  Initialization                                                      #
    # ================================================================== #
    async def initialize(self):
        """
        Initialise the engine.

        On memory-constrained environments, only *checks* which models
        exist without loading them.  On full-memory environments, loads
        all models eagerly (original behaviour).
        """
        if self._initialized:
            return

        logger.info("🔄 Initialising Predictive Maintenance Engine...")

        for eq_type, profile in EQUIPMENT_PROFILES.items():
            if MEMORY_CONSTRAINED:
                # --- LAZY MODE: just check availability ---
                rul_name = f"RefineryIQ_RUL_{eq_type}"
                ae_name = f"RefineryIQ_AE_{eq_type}"

                if self.mlflow.load_production_model(rul_name, metadata_only=True):
                    self._available_rul.add(eq_type)
                else:
                    local_path = os.path.join(LOCAL_MODEL_DIR, f"{eq_type}_rul_model.pt")
                    if os.path.exists(local_path):
                        self._available_rul.add(eq_type)

                if self.mlflow.load_production_model(ae_name, metadata_only=True):
                    self._available_ae.add(eq_type)
                else:
                    local_path = os.path.join(LOCAL_MODEL_DIR, f"{eq_type}_ae_model.pt")
                    if os.path.exists(local_path):
                        self._available_ae.add(eq_type)
            else:
                # --- EAGER MODE: load all models ---
                rul_model = await self._load_rul_model(eq_type, profile)
                if rul_model is not None:
                    self.rul_models[eq_type] = rul_model
                    self.explainers[eq_type] = SHAPExplainer(profile.features)

                ae_model = await self._load_ae_model(eq_type, profile)
                if ae_model is not None:
                    self.ae_models[eq_type] = ae_model

        if MEMORY_CONSTRAINED:
            n_rul = len(self._available_rul)
            n_ae = len(self._available_ae)
            logger.info(
                f"✅ Engine initialised (LAZY): {n_rul} RUL models, "
                f"{n_ae} anomaly detectors available (loaded on-demand)"
            )
        else:
            n_rul = len(self.rul_models)
            n_ae = len(self.ae_models)
            logger.info(
                f"✅ Engine initialised: {n_rul} RUL models, {n_ae} anomaly detectors"
            )

        self._initialized = True

    async def _load_rul_model(
        self, eq_type: str, profile
    ) -> Optional[torch.nn.Module]:
        """Load RUL model from MLflow or local checkpoint."""
        # Try MLflow first
        model_name = f"RefineryIQ_RUL_{eq_type}"
        mlflow_model = self.mlflow.load_production_model(model_name)
        if mlflow_model is not None:
            mlflow_model.eval()
            return mlflow_model

        # Local fallback
        local_path = os.path.join(LOCAL_MODEL_DIR, f"{eq_type}_rul_model.pt")
        if os.path.exists(local_path):
            try:
                checkpoint = torch.load(local_path, map_location="cpu", weights_only=False)
                model = LSTMRULModel(n_features=len(profile.features))
                model.load_state_dict(checkpoint["model_state_dict"])
                model.eval()

                self.norm_stats[eq_type] = {
                    "means": checkpoint.get("means"),
                    "stds": checkpoint.get("stds"),
                }

                logger.info(f"📂 RUL model loaded from local: {eq_type}")
                return model
            except Exception as e:
                logger.warning(f"⚠️ Error loading local RUL model {eq_type}: {e}")

        logger.info(f"ℹ️ No RUL model available for {eq_type}")
        return None

    async def _load_ae_model(
        self, eq_type: str, profile
    ) -> Optional[ConvAutoencoder]:
        """Load Autoencoder from MLflow or local checkpoint."""
        model_name = f"RefineryIQ_AE_{eq_type}"
        mlflow_model = self.mlflow.load_production_model(model_name)
        if mlflow_model is not None:
            mlflow_model.eval()
            return mlflow_model

        local_path = os.path.join(LOCAL_MODEL_DIR, f"{eq_type}_ae_model.pt")
        if os.path.exists(local_path):
            try:
                checkpoint = torch.load(local_path, map_location="cpu", weights_only=False)
                model = ConvAutoencoder(
                    n_features=len(profile.features), seq_len=WINDOW_SIZE
                )
                model.load_state_dict(checkpoint["model_state_dict"])
                model.threshold = torch.tensor(checkpoint["threshold"])
                model.recon_mean = torch.tensor(checkpoint["recon_mean"])
                model.recon_std = torch.tensor(checkpoint["recon_std"])
                model.eval()

                # Also load normalization stats for anomaly model
                if eq_type not in self.norm_stats:
                    self.norm_stats[eq_type] = {
                        "means": checkpoint.get("means"),
                        "stds": checkpoint.get("stds"),
                    }

                logger.info(f"📂 AE model loaded from local: {eq_type}")
                return model
            except Exception as e:
                logger.warning(f"⚠️ Error loading local AE model {eq_type}: {e}")

        return None

    def _lazy_load_for_type(self, equipment_type: str):
        """
        On memory-constrained envs, load only the models for the given
        equipment type, unloading any previously loaded models first.
        """
        if not MEMORY_CONSTRAINED:
            return  # Eager mode — models already loaded

        # If already loaded, skip
        if self._last_loaded_type == equipment_type:
            return

        # Unload previous models
        if self._last_loaded_type is not None:
            prev = self._last_loaded_type
            if prev in self.rul_models:
                del self.rul_models[prev]
            if prev in self.ae_models:
                del self.ae_models[prev]
            if prev in self.explainers:
                del self.explainers[prev]
            gc.collect()

        # Load models for this equipment type
        profile = EQUIPMENT_PROFILES.get(equipment_type)
        if profile is None:
            return

        if equipment_type in self._available_rul:
            model_name = f"RefineryIQ_RUL_{equipment_type}"
            model = self.mlflow.load_production_model(model_name)
            if model is not None:
                model.eval()
                self.rul_models[equipment_type] = model
                self.explainers[equipment_type] = SHAPExplainer(profile.features)
            else:
                # Local fallback
                local_path = os.path.join(LOCAL_MODEL_DIR, f"{equipment_type}_rul_model.pt")
                if os.path.exists(local_path):
                    try:
                        checkpoint = torch.load(local_path, map_location="cpu", weights_only=False)
                        m = LSTMRULModel(n_features=len(profile.features))
                        m.load_state_dict(checkpoint["model_state_dict"])
                        m.eval()
                        self.rul_models[equipment_type] = m
                        self.explainers[equipment_type] = SHAPExplainer(profile.features)
                        self.norm_stats[equipment_type] = {
                            "means": checkpoint.get("means"),
                            "stds": checkpoint.get("stds"),
                        }
                    except Exception as e:
                        logger.warning(f"⚠️ Lazy load RUL {equipment_type}: {e}")

        if equipment_type in self._available_ae:
            model_name = f"RefineryIQ_AE_{equipment_type}"
            model = self.mlflow.load_production_model(model_name)
            if model is not None:
                model.eval()
                self.ae_models[equipment_type] = model
            else:
                local_path = os.path.join(LOCAL_MODEL_DIR, f"{equipment_type}_ae_model.pt")
                if os.path.exists(local_path):
                    try:
                        checkpoint = torch.load(local_path, map_location="cpu", weights_only=False)
                        m = ConvAutoencoder(n_features=len(profile.features), seq_len=WINDOW_SIZE)
                        m.load_state_dict(checkpoint["model_state_dict"])
                        m.threshold = torch.tensor(checkpoint["threshold"])
                        m.recon_mean = torch.tensor(checkpoint["recon_mean"])
                        m.recon_std = torch.tensor(checkpoint["recon_std"])
                        m.eval()
                        self.ae_models[equipment_type] = m
                        if equipment_type not in self.norm_stats:
                            self.norm_stats[equipment_type] = {
                                "means": checkpoint.get("means"),
                                "stds": checkpoint.get("stds"),
                            }
                    except Exception as e:
                        logger.warning(f"⚠️ Lazy load AE {equipment_type}: {e}")

        self._last_loaded_type = equipment_type

    # ================================================================== #
    #  Data Ingestion (Sliding Window Buffer)                              #
    # ================================================================== #
    def ingest_reading(
        self, equipment_id: str, sensor_data: Dict[str, float]
    ):
        """
        Append a single sensor reading to the equipment's sliding window.

        This method is designed to be called from MQTT/Kafka consumers in
        the future, or from database polling.

        Parameters
        ----------
        equipment_id : str
            e.g. "PUMP-101"
        sensor_data : dict
            e.g. {"vibration_x": 3.1, "vibration_y": 2.9, "temperature": 80}
        """
        if equipment_id not in self.buffers:
            self.buffers[equipment_id] = deque(maxlen=MAX_BUFFER_SIZE)

        self.buffers[equipment_id].append({
            "timestamp": datetime.now().isoformat(),
            **sensor_data,
        })

    def _get_window(
        self, equipment_id: str, equipment_type: str
    ) -> Optional[np.ndarray]:
        """
        Extract the latest sliding window from the buffer.

        Returns (WINDOW_SIZE, n_features) or None if insufficient data.
        """
        buf = self.buffers.get(equipment_id)
        if buf is None or len(buf) < WINDOW_SIZE:
            return None

        profile = EQUIPMENT_PROFILES.get(equipment_type)
        if profile is None:
            return None

        features = profile.features
        readings = list(buf)[-WINDOW_SIZE:]

        window = np.array(
            [[r.get(f, 0.0) for f in features] for r in readings],
            dtype=np.float32,
        )

        # Normalise using stored stats
        stats = self.norm_stats.get(equipment_type)
        if stats and stats["means"] is not None:
            means = stats["means"]
            stds = stats["stds"]
            stds[stds == 0] = 1.0
            window = (window - means) / stds

        return window

    # ================================================================== #
    #  Synthetic data injection (for demo without real sensors)            #
    # ================================================================== #
    def inject_synthetic_readings(
        self, equipment_id: str, equipment_type: str, n_readings: int = 60
    ):
        """
        Fill buffer with synthetic sensor readings for demonstration.
        Uses nominal values with small noise from the equipment profile.
        """
        profile = EQUIPMENT_PROFILES.get(equipment_type)
        if profile is None:
            return

        rng = np.random.default_rng(hash(equipment_id) % (2**31))

        for _ in range(n_readings):
            reading = {}
            for feat in profile.features:
                nominal = profile.nominal_values[feat]
                vol = profile.volatilities[feat]
                reading[feat] = nominal + rng.normal(0, vol * 0.5)
            self.ingest_reading(equipment_id, reading)

    # ================================================================== #
    #  Prediction                                                          #
    # ================================================================== #
    async def predict(
        self, equipment_id: str, equipment_type: str
    ) -> Dict:
        """
        Full prediction: RUL + anomaly score + SHAP explanation.

        If the model is not loaded or the buffer is insufficient, returns
        a graceful fallback result.
        """
        result = {
            "equipment_id": equipment_id,
            "equipment_type": equipment_type,
            "timestamp": datetime.now().isoformat(),
            "rul_hours": None,
            "failure_probability": None,
            "anomaly_score": None,
            "is_anomaly": False,
            "shap_explanation": None,
            "narrative": None,
            "recommendation": None,
            "confidence": None,
            "model_source": "none",
        }

        # Ensure buffer has enough data
        if equipment_id not in self.buffers or len(self.buffers[equipment_id]) < WINDOW_SIZE:
            # Auto-inject synthetic readings for demo
            self.inject_synthetic_readings(equipment_id, equipment_type, WINDOW_SIZE + 10)

        window = self._get_window(equipment_id, equipment_type)
        if window is None:
            result["recommendation"] = "DATOS INSUFICIENTES — Esperando lecturas de sensores"
            return result

        # Lazy-load models for this equipment type (memory-constrained envs)
        self._lazy_load_for_type(equipment_type)

        # Run inference in thread pool (non-blocking)
        return await asyncio.get_event_loop().run_in_executor(
            None, self._predict_sync, equipment_id, equipment_type, window, result
        )

    def _predict_sync(
        self,
        equipment_id: str,
        equipment_type: str,
        window: np.ndarray,
        result: Dict,
    ) -> Dict:
        """Synchronous prediction logic (runs in thread pool)."""
        inp = torch.tensor(window, dtype=torch.float32).unsqueeze(0)  # (1, T, F)

        # --- RUL Prediction ---
        rul_model = self.rul_models.get(equipment_type)
        if rul_model is not None:
            with torch.no_grad():
                rul_pred = rul_model(inp).item()
                rul_pred = max(0, rul_pred)

            result["rul_hours"] = round(rul_pred, 1)
            result["failure_probability"] = round(
                min(99.0, 100.0 * np.exp(-rul_pred / 168.0)), 1
            )
            result["model_source"] = "lstm_rul"

            # Calculate confidence based on attention distribution
            try:
                attn = rul_model.attention_weights
                if attn is not None:
                    entropy = -(attn * torch.log(attn + 1e-8)).sum()
                    max_entropy = np.log(WINDOW_SIZE)
                    confidence = max(0, min(100, (1 - entropy.item() / max_entropy) * 100))
                    result["confidence"] = round(confidence, 1)
            except Exception:
                result["confidence"] = 75.0

        # --- Anomaly Detection ---
        ae_model = self.ae_models.get(equipment_type)
        if ae_model is not None:
            with torch.no_grad():
                flags, scores = ae_model.is_anomaly(inp)
                result["anomaly_score"] = round(scores.item(), 4)
                result["is_anomaly"] = bool(flags.item())

        # --- XAI Explanation ---
        explainer = self.explainers.get(equipment_type)
        if explainer is not None and rul_model is not None:
            try:
                explanation = explainer.explain_prediction(
                    rul_model, window, background_data=None
                )
                result["shap_explanation"] = {
                    "feature_importance": explanation["feature_importance"],
                    "top_drivers": [
                        {"feature": f, "contribution_pct": p, "direction": d}
                        for f, p, d in explanation["top_drivers"]
                    ],
                }
                result["narrative"] = explainer.generate_narrative(
                    explanation,
                    rul_hours=result.get("rul_hours", 0),
                    anomaly_score=result.get("anomaly_score"),
                    lang="es",
                )
            except Exception as e:
                logger.warning(f"XAI explanation error: {e}")

        # --- Recommendation ---
        result["recommendation"] = self._generate_recommendation(
            equipment_type,
            result.get("rul_hours"),
            result.get("is_anomaly", False),
        )

        return result

    async def predict_batch(
        self, equipment_list: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        Batch prediction for multiple equipment.

        Parameters
        ----------
        equipment_list : list of {"equipment_id": str, "equipment_type": str}
        """
        # On constrained envs, run sequentially to avoid loading multiple models
        if MEMORY_CONSTRAINED:
            results = []
            for eq in equipment_list:
                r = await self.predict(eq["equipment_id"], eq["equipment_type"])
                results.append(r)
            return results

        # Full mode: concurrent predictions
        tasks = [
            self.predict(eq["equipment_id"], eq["equipment_type"])
            for eq in equipment_list
        ]
        return await asyncio.gather(*tasks)

    # ================================================================== #
    #  Helpers                                                             #
    # ================================================================== #
    @staticmethod
    def _generate_recommendation(
        equipment_type: str,
        rul_hours: Optional[float],
        is_anomaly: bool,
    ) -> str:
        """Generate actionable maintenance recommendation."""
        if is_anomaly:
            return (
                f"🚨 ANOMALÍA ZERO-DAY DETECTADA en {equipment_type}. "
                f"Inspección inmediata requerida — patrón no visto en entrenamiento."
            )

        if rul_hours is None:
            return f"{equipment_type} — Modelo no disponible. Monitoreo manual recomendado."

        if rul_hours < RUL_CRITICAL:
            return (
                f"🔴 DETENER {equipment_type} PARA MANTENIMIENTO INMEDIATO. "
                f"RUL estimado: {rul_hours:.0f}h."
            )
        elif rul_hours < RUL_WARNING:
            return (
                f"🟠 PROGRAMAR MANTENIMIENTO de {equipment_type} en próximas 24h. "
                f"RUL estimado: {rul_hours:.0f}h."
            )
        elif rul_hours < RUL_CAUTION:
            return (
                f"🟡 MONITOREAR {equipment_type} de cerca — riesgo moderado. "
                f"RUL estimado: {rul_hours:.0f}h."
            )
        else:
            return (
                f"🟢 {equipment_type} operando normalmente. "
                f"RUL estimado: {rul_hours:.0f}h. Continuar monitoreo."
            )

    def get_engine_status(self) -> Dict:
        """Return engine health info."""
        return {
            "initialized": self._initialized,
            "rul_models_loaded": list(self.rul_models.keys()),
            "ae_models_loaded": list(self.ae_models.keys()),
            "rul_models_available": list(self._available_rul),
            "ae_models_available": list(self._available_ae),
            "lazy_mode": MEMORY_CONSTRAINED,
            "active_buffers": {
                eid: len(buf) for eid, buf in self.buffers.items()
            },
            "device": str(self.device),
        }

    # Backward compatibility with old PredictiveMaintenanceSystem
    async def get_recent_predictions(self, db_conn, limit: int = 10):
        """Compatibility stub for the old DummyML interface."""
        return []

    async def get_recent_analysis(self, db_conn, limit: int = 5):
        """Compatibility stub."""
        return []
