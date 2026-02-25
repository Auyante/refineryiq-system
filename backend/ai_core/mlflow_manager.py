"""
RefineryIQ AI Core — MLflow Manager
=====================================
Professional experiment tracking, model versioning, and registry
management using MLflow.  Replaces loose ``.pkl`` files with a
proper Model Registry workflow (Staging → Production).
"""

import logging
import os
import torch
import tempfile
from typing import Any, Dict, Optional

from ai_core.config import MLFLOW_TRACKING_URI, MLFLOW_EXPERIMENT_NAME

logger = logging.getLogger("RefineryIQ_MLOps")


class MLflowManager:
    """
    Wrapper around MLflow for experiment tracking and model lifecycle.

    If MLflow is not installed or the tracking server is unreachable,
    all methods degrade gracefully to no-ops with warnings.
    """

    def __init__(self):
        self._available = False
        self._mlflow = None
        self._current_run = None

        try:
            import mlflow
            import mlflow.pytorch

            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            self._mlflow = mlflow
            self._pytorch = mlflow.pytorch
            self._available = True
            logger.info(f"✅ MLflow initialised — tracking URI: {MLFLOW_TRACKING_URI}")
        except ImportError:
            logger.warning("⚠️ MLflow not installed — tracking disabled")
        except Exception as e:
            logger.warning(f"⚠️ MLflow init error: {e} — tracking disabled")

    @property
    def available(self) -> bool:
        return self._available

    # ------------------------------------------------------------------ #
    #  Experiment management                                               #
    # ------------------------------------------------------------------ #
    def set_experiment(self, name: str = MLFLOW_EXPERIMENT_NAME):
        """Create or set the active experiment."""
        if not self._available:
            return
        try:
            self._mlflow.set_experiment(name)
            logger.info(f"📊 MLflow experiment set: {name}")
        except Exception as e:
            logger.warning(f"MLflow set_experiment error: {e}")

    # ------------------------------------------------------------------ #
    #  Run lifecycle                                                       #
    # ------------------------------------------------------------------ #
    def start_run(self, run_name: str, tags: Optional[Dict] = None):
        """Start an MLflow run."""
        if not self._available:
            return

        try:
            self._current_run = self._mlflow.start_run(run_name=run_name, tags=tags)
            logger.info(f"🏃 MLflow run started: {run_name}")
        except Exception as e:
            logger.warning(f"MLflow start_run error: {e}")

    def end_run(self):
        """End the current MLflow run."""
        if not self._available or self._current_run is None:
            return
        try:
            self._mlflow.end_run()
            self._current_run = None
        except Exception as e:
            logger.warning(f"MLflow end_run error: {e}")

    # ------------------------------------------------------------------ #
    #  Logging                                                             #
    # ------------------------------------------------------------------ #
    def log_params(self, params: Dict[str, Any]):
        """Log hyperparameters to the active run."""
        if not self._available:
            return
        try:
            self._mlflow.log_params(params)
        except Exception as e:
            logger.warning(f"MLflow log_params error: {e}")

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """Log metrics to the active run."""
        if not self._available:
            return
        try:
            self._mlflow.log_metrics(metrics, step=step)
        except Exception as e:
            logger.warning(f"MLflow log_metrics error: {e}")

    def log_metric(self, key: str, value: float, step: Optional[int] = None):
        """Log a single metric."""
        if not self._available:
            return
        try:
            self._mlflow.log_metric(key, value, step=step)
        except Exception as e:
            logger.warning(f"MLflow log_metric error: {e}")

    # ------------------------------------------------------------------ #
    #  Model artifact logging & registry                                   #
    # ------------------------------------------------------------------ #
    def log_pytorch_model(
        self,
        model: torch.nn.Module,
        artifact_path: str = "model",
        registered_model_name: Optional[str] = None,
    ):
        """
        Log a PyTorch model to MLflow.

        Parameters
        ----------
        model : torch.nn.Module
        artifact_path : str
            Subdirectory within the run artifacts.
        registered_model_name : str, optional
            If given, also register the model in the Model Registry.
        """
        if not self._available:
            return
        try:
            self._pytorch.log_model(
                model,
                artifact_path=artifact_path,
                registered_model_name=registered_model_name,
            )
            logger.info(
                f"📦 Model logged to MLflow"
                + (f" and registered as '{registered_model_name}'" if registered_model_name else "")
            )
        except Exception as e:
            logger.warning(f"MLflow log_model error: {e}")

    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None):
        """Log a generic artifact file."""
        if not self._available:
            return
        try:
            self._mlflow.log_artifact(local_path, artifact_path)
        except Exception as e:
            logger.warning(f"MLflow log_artifact error: {e}")

    # ------------------------------------------------------------------ #
    #  Model Registry: load production models                              #
    # ------------------------------------------------------------------ #
    def load_production_model(
        self, model_name: str, metadata_only: bool = False
    ) -> Optional[torch.nn.Module]:
        """
        Load the latest production-stage model from the registry.

        Falls back to latest version if no production alias is found.

        Parameters
        ----------
        model_name : str
            Registered model name, e.g. "RefineryIQ_RUL_PUMP".
        metadata_only : bool
            If True, only check whether a model version exists in the
            registry and return ``True`` (truthy) without loading it
            into memory.  Useful for lazy-loading initialization.
        """
        if not self._available:
            return None
        try:
            client = self._mlflow.tracking.MlflowClient()

            # Check if any version exists
            try:
                versions = client.search_model_versions(f"name='{model_name}'")
                if not versions:
                    if not metadata_only:
                        logger.warning(f"⚠️ No model found in registry: {model_name}")
                    return None
            except Exception:
                if not metadata_only:
                    logger.warning(f"⚠️ No model found in registry: {model_name}")
                return None

            # Metadata-only: just confirm existence
            if metadata_only:
                return True  # truthy sentinel

            # Try to load by alias "production" first
            try:
                model_uri = f"models:/{model_name}@production"
                model = self._pytorch.load_model(model_uri)
                logger.info(f"✅ Loaded production model: {model_name}")
                return model
            except Exception:
                pass

            # Fallback: load latest version
            latest = max(versions, key=lambda v: int(v.version))
            model_uri = f"models:/{model_name}/{latest.version}"
            model = self._pytorch.load_model(model_uri)
            logger.info(
                f"✅ Loaded model: {model_name} v{latest.version}"
            )
            return model

        except Exception as e:
            logger.warning(f"MLflow load_model error: {e}")
            return None

    def list_registered_models(self) -> list:
        """List all models in the registry with their versions."""
        if not self._available:
            return []
        try:
            client = self._mlflow.tracking.MlflowClient()
            models = client.search_registered_models()
            result = []
            for rm in models:
                versions = client.search_model_versions(f"name='{rm.name}'")
                result.append({
                    "name": rm.name,
                    "latest_versions": [
                        {
                            "version": v.version,
                            "stage": getattr(v, 'current_stage', 'None'),
                            "status": v.status,
                            "run_id": v.run_id,
                        }
                        for v in versions
                    ],
                })
            return result
        except Exception as e:
            logger.warning(f"MLflow list_models error: {e}")
            return []

    # ------------------------------------------------------------------ #
    #  Local fallback: save/load .pt files                                 #
    # ------------------------------------------------------------------ #
    @staticmethod
    def save_model_local(model: torch.nn.Module, path: str):
        """Save model state dict locally as fallback."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        torch.save(model.state_dict(), path)
        logger.info(f"💾 Model saved locally: {path}")

    @staticmethod
    def load_model_local(model: torch.nn.Module, path: str) -> torch.nn.Module:
        """Load model state dict from local file."""
        model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        model.eval()
        logger.info(f"📂 Model loaded from: {path}")
        return model
