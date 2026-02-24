"""
RefineryIQ AI Core — FastAPI Routes
=====================================
API endpoints for the AI subsystem.  Mounted on the main FastAPI app
as a router under ``/api/ai``.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ai_core.config import EQUIPMENT_PROFILES
from ai_core.inference_engine import PredictiveMaintenanceEngine
from ai_core.training_pipeline import TrainingPipeline

logger = logging.getLogger("RefineryIQ_AI_Routes")

# ============================================================================
# Router & shared instances
# ============================================================================
router = APIRouter(prefix="/api/ai", tags=["AI / Predictive Maintenance"])

# Singleton instances (initialised at import time; lifespan inits engine)
engine = PredictiveMaintenanceEngine()
_training_status: Dict = {"status": "idle", "last_run": None, "results": None}


# ============================================================================
# Pydantic schemas
# ============================================================================

class PredictionResponse(BaseModel):
    equipment_id: str
    equipment_type: str
    timestamp: str
    rul_hours: Optional[float] = None
    failure_probability: Optional[float] = None
    anomaly_score: Optional[float] = None
    is_anomaly: bool = False
    shap_explanation: Optional[Dict] = None
    narrative: Optional[str] = None
    recommendation: Optional[str] = None
    confidence: Optional[float] = None
    model_source: str = "none"


class BatchPredictionRequest(BaseModel):
    equipment: List[Dict[str, str]]  # [{"equipment_id": "...", "equipment_type": "..."}]


class TrainRequest(BaseModel):
    equipment_types: Optional[List[str]] = None
    n_cycles: int = 15


class SensorReading(BaseModel):
    equipment_id: str
    equipment_type: str
    readings: Dict[str, float]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/health")
async def ai_health():
    """AI subsystem health check."""
    status = engine.get_engine_status()
    return {
        "status": "operational" if status["initialized"] else "not_initialized",
        "engine": status,
        "available_equipment_types": list(EQUIPMENT_PROFILES.keys()),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/predict/{equipment_id}", response_model=PredictionResponse)
async def predict_equipment(equipment_id: str, equipment_type: Optional[str] = None):
    """
    Predict RUL, anomaly score, and SHAP explanation for a single equipment.

    If ``equipment_type`` is not provided, it's inferred from the equipment_id prefix.
    """
    if not engine._initialized:
        await engine.initialize()

    # Infer type from ID prefix (e.g. PUMP-101 → PUMP)
    if equipment_type is None:
        for et in EQUIPMENT_PROFILES:
            if equipment_id.upper().startswith(et):
                equipment_type = et
                break
        if equipment_type is None:
            equipment_type = "PUMP"  # safe default

    try:
        result = await engine.predict(equipment_id, equipment_type)
        return result
    except Exception as e:
        logger.error(f"Prediction error for {equipment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/batch")
async def predict_batch(request: BatchPredictionRequest):
    """Batch prediction for multiple equipment in parallel."""
    if not engine._initialized:
        await engine.initialize()

    try:
        results = await engine.predict_batch(request.equipment)
        return {"predictions": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest_sensor_reading(reading: SensorReading):
    """
    Ingest a single sensor reading into the sliding window buffer.

    In the future, this will be replaced by direct MQTT/Kafka consumers.
    """
    engine.ingest_reading(reading.equipment_id, reading.readings)
    buffer_size = len(engine.buffers.get(reading.equipment_id, []))
    return {
        "status": "ingested",
        "equipment_id": reading.equipment_id,
        "buffer_size": buffer_size,
    }


@router.post("/train")
async def trigger_training(
    request: TrainRequest, background_tasks: BackgroundTasks
):
    """
    Trigger model training in the background.

    Training runs asynchronously and results can be checked via ``/api/ai/train/status``.
    """
    global _training_status

    if _training_status["status"] == "running":
        return {
            "status": "already_running",
            "message": "Training is already in progress. Check /api/ai/train/status",
        }

    _training_status = {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "results": None,
    }

    async def _run_training():
        global _training_status
        try:
            pipeline = TrainingPipeline()
            results = pipeline.train_all(
                equipment_types=request.equipment_types,
                n_cycles=request.n_cycles,
            )
            _training_status = {
                "status": "completed",
                "last_run": datetime.now().isoformat(),
                "results": results,
            }
            # Re-initialize engine to load new models
            engine._initialized = False
            await engine.initialize()
        except Exception as e:
            logger.error(f"Training error: {e}")
            _training_status = {
                "status": "error",
                "last_run": datetime.now().isoformat(),
                "error": str(e),
            }

    background_tasks.add_task(_run_training)

    return {
        "status": "started",
        "message": "Training pipeline started in background",
        "equipment_types": request.equipment_types or list(EQUIPMENT_PROFILES.keys()),
    }


@router.get("/train/status")
async def get_training_status():
    """Get the current training pipeline status."""
    return _training_status


@router.get("/anomalies")
async def get_recent_anomalies():
    """Get equipment with detected anomalies from the current buffers."""
    if not engine._initialized:
        await engine.initialize()

    anomalies = []
    default_equipment = [
        {"equipment_id": "PUMP-101", "equipment_type": "PUMP"},
        {"equipment_id": "COMP-201", "equipment_type": "COMPRESSOR"},
        {"equipment_id": "VALVE-401", "equipment_type": "VALVE"},
    ]

    for eq in default_equipment:
        try:
            result = await engine.predict(eq["equipment_id"], eq["equipment_type"])
            if result.get("is_anomaly") or (result.get("rul_hours") is not None and result["rul_hours"] < 168):
                anomalies.append(result)
        except Exception:
            pass

    return {"anomalies": anomalies, "count": len(anomalies)}


@router.get("/models")
async def list_models():
    """List all registered ML models and their versions."""
    models = engine.mlflow.list_registered_models()
    return {
        "models": models,
        "local_models": {
            "rul": list(engine.rul_models.keys()),
            "anomaly": list(engine.ae_models.keys()),
        },
    }
