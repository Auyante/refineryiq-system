"""
RefineryIQ AI Core — Enterprise Predictive Maintenance Engine
==============================================================
Tier-1 ML subsystem featuring:
  • LSTM-based Remaining Useful Life (RUL) prediction
  • Convolutional Autoencoder anomaly detection (Zero-Day)
  • SHAP-powered Explainable AI (XAI)
  • MLflow experiment tracking & model registry
  • Physics-informed synthetic data generation (Digital Twin)
  • Real-time sliding-window inference pipeline
"""

from ai_core.data_generator import DigitalTwinGenerator
from ai_core.models import LSTMRULModel, ConvAutoencoder
from ai_core.explainability import SHAPExplainer
from ai_core.inference_engine import PredictiveMaintenanceEngine
from ai_core.mlflow_manager import MLflowManager

__version__ = "2.0.0"

__all__ = [
    "DigitalTwinGenerator",
    "LSTMRULModel",
    "ConvAutoencoder",
    "SHAPExplainer",
    "PredictiveMaintenanceEngine",
    "MLflowManager",
]
