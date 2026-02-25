"""
RefineryIQ AI Core — Centralized Configuration
================================================
All hyperparameters, equipment profiles, sensor mappings, and physics
constants for the Tier-1 predictive maintenance system.
"""

import os
import psutil
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# =============================================================================
# Environment Detection — auto-tune for memory-constrained servers
# =============================================================================
IS_RENDER = bool(os.getenv("RENDER") or os.getenv("RENDER_EXTERNAL_HOSTNAME"))
try:
    AVAILABLE_RAM_MB = psutil.virtual_memory().total / (1024 * 1024)
except Exception:
    AVAILABLE_RAM_MB = 512 if IS_RENDER else 4096

MEMORY_CONSTRAINED = IS_RENDER or AVAILABLE_RAM_MB < 1024

# =============================================================================
# MLflow Configuration
# =============================================================================
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
MLFLOW_EXPERIMENT_NAME = "RefineryIQ_PredictiveMaintenance"

# =============================================================================
# Sliding Window Configuration
# =============================================================================
if MEMORY_CONSTRAINED:
    WINDOW_SIZE = 20          # Smaller windows for fast training
    STRIDE = 10               # Larger stride = fewer windows
else:
    WINDOW_SIZE = 50          # Number of timesteps per input window
    STRIDE = 1                # Sliding window stride

PREDICTION_HORIZON = 1    # Predict RUL at next step

# =============================================================================
# LSTM Model Hyperparameters
# =============================================================================
if MEMORY_CONSTRAINED:
    # --- LITE MODE (Render / <1GB RAM) ---
    LSTM_HIDDEN_DIM = 32
    LSTM_NUM_LAYERS = 1
    LSTM_DROPOUT = 0.1
    LSTM_BIDIRECTIONAL = False
    ATTENTION_HEADS = 1
    LEARNING_RATE = 5e-3
    BATCH_SIZE = 64
    MAX_EPOCHS = 10
    EARLY_STOPPING_PATIENCE = 5
    WEIGHT_DECAY = 1e-5
    DEFAULT_N_CYCLES = 3
else:
    # --- FULL MODE (>=1GB RAM) ---
    LSTM_HIDDEN_DIM = 128
    LSTM_NUM_LAYERS = 2
    LSTM_DROPOUT = 0.3
    LSTM_BIDIRECTIONAL = True
    ATTENTION_HEADS = 4
    LEARNING_RATE = 1e-3
    BATCH_SIZE = 64
    MAX_EPOCHS = 100
    EARLY_STOPPING_PATIENCE = 10
    WEIGHT_DECAY = 1e-5
    DEFAULT_N_CYCLES = 15

# Asymmetric loss: penalize late predictions (under-estimating RUL) more
LATE_PENALTY_FACTOR = 2.0   # multiplier for under-estimated RUL
EARLY_PENALTY_FACTOR = 1.0  # multiplier for over-estimated RUL

# =============================================================================
# Autoencoder Hyperparameters
# =============================================================================
AE_LATENT_DIM = 4 if MEMORY_CONSTRAINED else 16
AE_LEARNING_RATE = 1e-3
AE_EPOCHS = 10 if MEMORY_CONSTRAINED else 80
AE_NORMAL_SAMPLES = 1000 if MEMORY_CONSTRAINED else 8000
AE_ANOMALY_SIGMA = 3.0  # threshold = mean + N*sigma of reconstruction error

# =============================================================================
# Equipment Profiles & Sensor Definitions
# =============================================================================

@dataclass
class EquipmentProfile:
    """Defines sensor features and physics parameters for an equipment type."""
    equipment_type: str
    features: List[str]
    nominal_values: Dict[str, float]
    failure_thresholds: Dict[str, float]
    drift_rates: Dict[str, float]       # Brownian motion drift (μ)
    volatilities: Dict[str, float]      # Brownian motion volatility (σ)
    mtbf_hours: float                   # Mean Time Between Failures
    degradation_states: List[str] = field(
        default_factory=lambda: ["NORMAL", "DEGRADING", "PRE_FAILURE", "FAILURE"]
    )


EQUIPMENT_PROFILES: Dict[str, EquipmentProfile] = {
    "PUMP": EquipmentProfile(
        equipment_type="PUMP",
        features=["vibration_x", "vibration_y", "temperature", "pressure", "flow_rate"],
        nominal_values={
            "vibration_x": 2.5, "vibration_y": 2.3,
            "temperature": 75.0, "pressure": 15.0, "flow_rate": 100.0
        },
        failure_thresholds={
            "vibration_x": 8.0, "vibration_y": 7.5,
            "temperature": 120.0, "pressure": 5.0, "flow_rate": 60.0
        },
        drift_rates={
            "vibration_x": 0.005, "vibration_y": 0.004,
            "temperature": 0.01, "pressure": -0.003, "flow_rate": -0.008
        },
        volatilities={
            "vibration_x": 0.3, "vibration_y": 0.25,
            "temperature": 1.5, "pressure": 0.5, "flow_rate": 2.0
        },
        mtbf_hours=4320  # ~6 months
    ),
    "COMPRESSOR": EquipmentProfile(
        equipment_type="COMPRESSOR",
        features=["vibration_x", "vibration_y", "temperature", "pressure_ratio", "efficiency"],
        nominal_values={
            "vibration_x": 3.0, "vibration_y": 2.8,
            "temperature": 85.0, "pressure_ratio": 3.2, "efficiency": 92.0
        },
        failure_thresholds={
            "vibration_x": 10.0, "vibration_y": 9.0,
            "temperature": 140.0, "pressure_ratio": 1.5, "efficiency": 65.0
        },
        drift_rates={
            "vibration_x": 0.006, "vibration_y": 0.005,
            "temperature": 0.012, "pressure_ratio": -0.002, "efficiency": -0.01
        },
        volatilities={
            "vibration_x": 0.35, "vibration_y": 0.3,
            "temperature": 2.0, "pressure_ratio": 0.15, "efficiency": 1.0
        },
        mtbf_hours=6720  # ~9 months
    ),
    "VALVE": EquipmentProfile(
        equipment_type="VALVE",
        features=["position_error", "response_time", "leakage_rate", "actuator_pressure"],
        nominal_values={
            "position_error": 0.5, "response_time": 1.5,
            "leakage_rate": 0.02, "actuator_pressure": 95.0
        },
        failure_thresholds={
            "position_error": 5.0, "response_time": 8.0,
            "leakage_rate": 2.0, "actuator_pressure": 50.0
        },
        drift_rates={
            "position_error": 0.003, "response_time": 0.004,
            "leakage_rate": 0.002, "actuator_pressure": -0.005
        },
        volatilities={
            "position_error": 0.1, "response_time": 0.2,
            "leakage_rate": 0.05, "actuator_pressure": 1.5
        },
        mtbf_hours=8760  # ~12 months
    ),
    "EXCHANGER": EquipmentProfile(
        equipment_type="EXCHANGER",
        features=["delta_t", "fouling_factor", "pressure_drop", "flow_rate", "efficiency"],
        nominal_values={
            "delta_t": 45.0, "fouling_factor": 0.001,
            "pressure_drop": 0.5, "flow_rate": 200.0, "efficiency": 95.0
        },
        failure_thresholds={
            "delta_t": 15.0, "fouling_factor": 0.01,
            "pressure_drop": 3.0, "flow_rate": 120.0, "efficiency": 70.0
        },
        drift_rates={
            "delta_t": -0.008, "fouling_factor": 0.0001,
            "pressure_drop": 0.003, "flow_rate": -0.006, "efficiency": -0.007
        },
        volatilities={
            "delta_t": 1.0, "fouling_factor": 0.0005,
            "pressure_drop": 0.1, "flow_rate": 3.0, "efficiency": 0.8
        },
        mtbf_hours=10080  # ~14 months
    ),
    "FURNACE": EquipmentProfile(
        equipment_type="FURNACE",
        features=["firebox_temp", "stack_temp", "excess_o2", "draft_pressure", "efficiency"],
        nominal_values={
            "firebox_temp": 850.0, "stack_temp": 180.0,
            "excess_o2": 3.0, "draft_pressure": -0.5, "efficiency": 90.0
        },
        failure_thresholds={
            "firebox_temp": 1050.0, "stack_temp": 350.0,
            "excess_o2": 8.0, "draft_pressure": -3.0, "efficiency": 70.0
        },
        drift_rates={
            "firebox_temp": 0.015, "stack_temp": 0.02,
            "excess_o2": 0.005, "draft_pressure": -0.002, "efficiency": -0.008
        },
        volatilities={
            "firebox_temp": 5.0, "stack_temp": 3.0,
            "excess_o2": 0.3, "draft_pressure": 0.1, "efficiency": 0.5
        },
        mtbf_hours=5040  # ~7 months
    ),
}

# =============================================================================
# Markov Chain Transition Probabilities (per hour)
# =============================================================================
# State transitions: NORMAL → DEGRADING → PRE_FAILURE → FAILURE
# These are base probabilities; actual transitions are modulated by sensor drift.
MARKOV_TRANSITIONS = {
    "NORMAL":      {"NORMAL": 0.998, "DEGRADING": 0.002, "PRE_FAILURE": 0.0,   "FAILURE": 0.0},
    "DEGRADING":   {"NORMAL": 0.0,   "DEGRADING": 0.990, "PRE_FAILURE": 0.010, "FAILURE": 0.0},
    "PRE_FAILURE": {"NORMAL": 0.0,   "DEGRADING": 0.0,   "PRE_FAILURE": 0.970, "FAILURE": 0.030},
    "FAILURE":     {"NORMAL": 0.0,   "DEGRADING": 0.0,   "PRE_FAILURE": 0.0,   "FAILURE": 1.0},
}

# =============================================================================
# Inference Configuration
# =============================================================================
MAX_BUFFER_SIZE = 200       # Max readings in sliding window buffer per equipment
INFERENCE_TIMEOUT_SEC = 5   # Max seconds for single prediction
MODEL_RELOAD_INTERVAL = 3600  # Seconds between checking for new model versions

# Recommendation thresholds (based on RUL hours)
RUL_CRITICAL = 24       # < 24h → STOP IMMEDIATELY
RUL_WARNING = 72        # < 72h → Schedule maintenance in 24h
RUL_CAUTION = 168       # < 1 week → Monitor closely
