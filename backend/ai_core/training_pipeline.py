"""
RefineryIQ AI Core — Training Pipeline
========================================
End-to-end orchestrator that ties together data generation, model training,
evaluation, SHAP analysis, and MLflow registration.

Usage::

    pipeline = TrainingPipeline()
    results = pipeline.train_all()
"""

import logging
import os
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from typing import Dict, List, Optional, Tuple

from ai_core.config import (
    EQUIPMENT_PROFILES,
    WINDOW_SIZE,
    STRIDE,
    BATCH_SIZE,
    MAX_EPOCHS,
    EARLY_STOPPING_PATIENCE,
    LEARNING_RATE,
    WEIGHT_DECAY,
    LATE_PENALTY_FACTOR,
    EARLY_PENALTY_FACTOR,
    AE_EPOCHS,
    AE_LEARNING_RATE,
    AE_ANOMALY_SIGMA,
)
from ai_core.data_generator import DigitalTwinGenerator
from ai_core.models import LSTMRULModel, AsymmetricRULLoss, ConvAutoencoder
from ai_core.mlflow_manager import MLflowManager

logger = logging.getLogger("RefineryIQ_Training")

# Default local save path
LOCAL_MODEL_DIR = "ml_models_v2"


class TrainingPipeline:
    """
    Full training pipeline for RUL and anomaly detection models.
    """

    def __init__(self, device: Optional[str] = None):
        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.generator = DigitalTwinGenerator()
        self.mlflow = MLflowManager()
        os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)

        logger.info(f"🔧 Training pipeline initialised on device: {self.device}")

    # ================================================================== #
    #  Sliding-Window Preprocessor                                        #
    # ================================================================== #
    @staticmethod
    def prepare_sliding_windows(
        df, features: List[str], window_size: int = WINDOW_SIZE, stride: int = STRIDE
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert a time-series DataFrame into sliding-window tensors.

        Returns
        -------
        X : (n_windows, window_size, n_features)
        y : (n_windows,) — RUL at the end of each window
        """
        values = df[features].values
        rul = df["rul_hours"].values

        windows_X, windows_y = [], []

        for start in range(0, len(values) - window_size, stride):
            end = start + window_size
            windows_X.append(values[start:end])
            windows_y.append(rul[end - 1])

        X = np.array(windows_X, dtype=np.float32)
        y = np.array(windows_y, dtype=np.float32)
        return X, y

    # ================================================================== #
    #  Feature Normalization (per equipment type)                          #
    # ================================================================== #
    @staticmethod
    def normalize_features(
        X_train: np.ndarray, X_val: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Z-score normalise using training statistics.

        Returns X_train_norm, X_val_norm, means, stds
        """
        # Flatten to (n_samples * seq_len, n_features) for stats
        shape_orig = X_train.shape
        flat = X_train.reshape(-1, shape_orig[-1])
        means = flat.mean(axis=0)
        stds = flat.std(axis=0)
        stds[stds == 0] = 1.0  # avoid division by zero

        X_train_n = (X_train - means) / stds
        X_val_n = (X_val - means) / stds

        return X_train_n.astype(np.float32), X_val_n.astype(np.float32), means, stds

    # ================================================================== #
    #  Train RUL Model (LSTM)                                              #
    # ================================================================== #
    def train_rul_model(
        self,
        equipment_type: str,
        n_cycles: int = 15,
        duration_hours: int = 4320,
    ) -> Dict:
        """
        Full training loop for the LSTM RUL model on one equipment type.

        Returns
        -------
        dict with training metrics.
        """
        logger.info(f"🧠 Training RUL model for {equipment_type}...")
        profile = EQUIPMENT_PROFILES[equipment_type]
        features = profile.features

        # 1. Generate data
        t0 = time.time()
        df = self.generator.generate_dataset(
            n_cycles_per_type=n_cycles,
            equipment_types=[equipment_type],
            duration_hours=duration_hours,
        )
        gen_time = time.time() - t0
        logger.info(f"📊 Data generated in {gen_time:.1f}s: {len(df)} samples")

        # 2. Prepare sliding windows (per cycle)
        all_X, all_y = [], []
        for cycle_id in df["cycle_id"].unique():
            df_cycle = df[df["cycle_id"] == cycle_id].sort_values("timestamp")
            if len(df_cycle) < WINDOW_SIZE + 10:
                continue
            X_c, y_c = self.prepare_sliding_windows(df_cycle, features)
            all_X.append(X_c)
            all_y.append(y_c)

        X = np.concatenate(all_X)
        y = np.concatenate(all_y)

        # 3. Train / Validation split (80/20, by position — not random)
        split = int(0.8 * len(X))
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]

        # Normalise
        X_train, X_val, means, stds = self.normalize_features(X_train, X_val)

        # 4. DataLoaders
        train_ds = TensorDataset(
            torch.tensor(X_train), torch.tensor(y_train).unsqueeze(-1)
        )
        val_ds = TensorDataset(
            torch.tensor(X_val), torch.tensor(y_val).unsqueeze(-1)
        )
        train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)

        # 5. Model
        model = LSTMRULModel(n_features=len(features)).to(self.device)
        criterion = AsymmetricRULLoss(LATE_PENALTY_FACTOR, EARLY_PENALTY_FACTOR)
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=5
        )

        # 6. MLflow logging
        self.mlflow.set_experiment(f"RefineryIQ_RUL_{equipment_type}")
        self.mlflow.start_run(
            run_name=f"RUL_{equipment_type}_{int(time.time())}",
            tags={"equipment_type": equipment_type, "model_type": "LSTM_RUL"},
        )
        self.mlflow.log_params({
            "equipment_type": equipment_type,
            "n_cycles": n_cycles,
            "window_size": WINDOW_SIZE,
            "hidden_dim": model.hidden_dim,
            "n_layers": model.n_layers,
            "learning_rate": LEARNING_RATE,
            "batch_size": BATCH_SIZE,
            "n_train_samples": len(X_train),
            "n_val_samples": len(X_val),
        })

        # 7. Training loop with early stopping
        best_val_loss = float("inf")
        patience_counter = 0
        best_metrics = {}

        for epoch in range(1, MAX_EPOCHS + 1):
            # --- Train ---
            model.train()
            train_loss = 0.0
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)

                optimizer.zero_grad()
                pred = model(X_batch)
                loss = criterion(pred, y_batch)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                train_loss += loss.item() * len(X_batch)

            train_loss /= len(train_ds)

            # --- Validate ---
            model.eval()
            val_loss = 0.0
            all_preds, all_targets = [], []
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)
                    pred = model(X_batch)
                    loss = criterion(pred, y_batch)
                    val_loss += loss.item() * len(X_batch)
                    all_preds.append(pred.cpu())
                    all_targets.append(y_batch.cpu())

            val_loss /= len(val_ds)
            scheduler.step(val_loss)

            preds = torch.cat(all_preds).squeeze()
            targets = torch.cat(all_targets).squeeze()
            rmse = torch.sqrt(torch.mean((preds - targets) ** 2)).item()
            mae = torch.mean(torch.abs(preds - targets)).item()
            ss_res = torch.sum((targets - preds) ** 2)
            ss_tot = torch.sum((targets - targets.mean()) ** 2)
            r2 = (1 - ss_res / (ss_tot + 1e-8)).item()

            # Log to MLflow
            self.mlflow.log_metrics(
                {"train_loss": train_loss, "val_loss": val_loss,
                 "rmse": rmse, "mae": mae, "r2": r2},
                step=epoch,
            )

            if epoch % 10 == 0 or epoch == 1:
                logger.info(
                    f"  Epoch {epoch}/{MAX_EPOCHS} — "
                    f"train: {train_loss:.4f}, val: {val_loss:.4f}, "
                    f"RMSE: {rmse:.2f}h, MAE: {mae:.2f}h, R²: {r2:.4f}"
                )

            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_metrics = {
                    "best_val_loss": val_loss,
                    "best_rmse": rmse,
                    "best_mae": mae,
                    "best_r2": r2,
                    "best_epoch": epoch,
                }
                # Save best model
                local_path = os.path.join(
                    LOCAL_MODEL_DIR, f"{equipment_type}_rul_model.pt"
                )
                torch.save({
                    "model_state_dict": model.state_dict(),
                    "means": means,
                    "stds": stds,
                    "features": features,
                    "equipment_type": equipment_type,
                }, local_path)
            else:
                patience_counter += 1
                if patience_counter >= EARLY_STOPPING_PATIENCE:
                    logger.info(f"  ⏹ Early stopping at epoch {epoch}")
                    break

        # 8. Log best model to MLflow
        self.mlflow.log_metrics(best_metrics)
        model_name = f"RefineryIQ_RUL_{equipment_type}"
        self.mlflow.log_pytorch_model(
            model, artifact_path="model", registered_model_name=model_name
        )
        self.mlflow.end_run()

        logger.info(
            f"🎉 RUL model trained for {equipment_type}: "
            f"RMSE={best_metrics.get('best_rmse', 0):.2f}h, "
            f"R²={best_metrics.get('best_r2', 0):.4f}"
        )
        return {
            "status": "success",
            "equipment_type": equipment_type,
            "model_type": "LSTM_RUL",
            **best_metrics,
        }

    # ================================================================== #
    #  Train Anomaly Detector (Autoencoder)                                #
    # ================================================================== #
    def train_anomaly_detector(
        self,
        equipment_type: str,
        n_normal_samples: int = 8000,
    ) -> Dict:
        """
        Train the Convolutional Autoencoder on normal-only data.
        """
        logger.info(f"🔍 Training anomaly detector for {equipment_type}...")
        profile = EQUIPMENT_PROFILES[equipment_type]
        features = profile.features

        # 1. Generate normal data
        df_normal = self.generator.generate_normal_dataset(equipment_type, n_normal_samples)
        values = df_normal[features].values.astype(np.float32)

        # Normalise
        means = values.mean(axis=0)
        stds = values.std(axis=0)
        stds[stds == 0] = 1.0
        values_norm = (values - means) / stds

        # Create pseudo-windows (reshape sequential chunks)
        n_windows = len(values_norm) // WINDOW_SIZE
        trimmed = values_norm[: n_windows * WINDOW_SIZE]
        X = trimmed.reshape(n_windows, WINDOW_SIZE, len(features))

        # Split
        split = int(0.8 * len(X))
        X_train, X_val = X[:split], X[split:]

        train_ds = TensorDataset(torch.tensor(X_train))
        val_ds = TensorDataset(torch.tensor(X_val))
        train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)

        # 2. Model
        model = ConvAutoencoder(
            n_features=len(features), seq_len=WINDOW_SIZE
        ).to(self.device)

        optimizer = torch.optim.Adam(model.parameters(), lr=AE_LEARNING_RATE)
        criterion = nn.MSELoss()

        # 3. MLflow
        self.mlflow.set_experiment(f"RefineryIQ_AnomalyDetector_{equipment_type}")
        self.mlflow.start_run(
            run_name=f"AE_{equipment_type}_{int(time.time())}",
            tags={"equipment_type": equipment_type, "model_type": "ConvAutoencoder"},
        )
        self.mlflow.log_params({
            "equipment_type": equipment_type,
            "n_samples": n_normal_samples,
            "window_size": WINDOW_SIZE,
            "latent_dim": model.latent_dim,
        })

        # 4. Training
        best_val_loss = float("inf")

        for epoch in range(1, AE_EPOCHS + 1):
            model.train()
            train_loss = 0.0
            for (X_batch,) in train_loader:
                X_batch = X_batch.to(self.device)
                optimizer.zero_grad()
                recon = model(X_batch)
                loss = criterion(recon, X_batch)
                loss.backward()
                optimizer.step()
                train_loss += loss.item() * len(X_batch)

            train_loss /= len(train_ds)

            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for (X_batch,) in val_loader:
                    X_batch = X_batch.to(self.device)
                    recon = model(X_batch)
                    loss = criterion(recon, X_batch)
                    val_loss += loss.item() * len(X_batch)

            val_loss /= len(val_ds)

            self.mlflow.log_metrics(
                {"ae_train_loss": train_loss, "ae_val_loss": val_loss}, step=epoch
            )

            if epoch % 20 == 0 or epoch == 1:
                logger.info(
                    f"  AE Epoch {epoch}/{AE_EPOCHS} — "
                    f"train: {train_loss:.6f}, val: {val_loss:.6f}"
                )

            if val_loss < best_val_loss:
                best_val_loss = val_loss

        # 5. Set anomaly threshold from training reconstruction errors
        model.eval()
        all_scores = []
        with torch.no_grad():
            for (X_batch,) in train_loader:
                X_batch = X_batch.to(self.device)
                scores = model.compute_anomaly_score(X_batch)
                all_scores.append(scores.cpu())

        all_scores = torch.cat(all_scores)
        model.set_threshold(all_scores, n_sigma=AE_ANOMALY_SIGMA)

        threshold_val = model.threshold.item()
        logger.info(f"  Anomaly threshold set: {threshold_val:.6f}")
        self.mlflow.log_metrics({
            "anomaly_threshold": threshold_val,
            "recon_error_mean": model.recon_mean.item(),
            "recon_error_std": model.recon_std.item(),
        })

        # 6. Save
        local_path = os.path.join(LOCAL_MODEL_DIR, f"{equipment_type}_ae_model.pt")
        torch.save({
            "model_state_dict": model.state_dict(),
            "threshold": model.threshold.item(),
            "recon_mean": model.recon_mean.item(),
            "recon_std": model.recon_std.item(),
            "means": means,
            "stds": stds,
            "features": features,
            "equipment_type": equipment_type,
        }, local_path)

        model_name = f"RefineryIQ_AE_{equipment_type}"
        self.mlflow.log_pytorch_model(
            model, artifact_path="model", registered_model_name=model_name
        )
        self.mlflow.end_run()

        logger.info(f"🎉 Anomaly detector trained for {equipment_type}")
        return {
            "status": "success",
            "equipment_type": equipment_type,
            "model_type": "ConvAutoencoder",
            "threshold": threshold_val,
            "best_val_loss": best_val_loss,
        }

    # ================================================================== #
    #  Train All                                                           #
    # ================================================================== #
    def train_all(
        self,
        equipment_types: Optional[List[str]] = None,
        n_cycles: int = 15,
    ) -> Dict:
        """
        Train both RUL and anomaly models for all equipment types.
        """
        if equipment_types is None:
            equipment_types = list(EQUIPMENT_PROFILES.keys())

        results = {"rul_models": {}, "anomaly_models": {}, "status": "success"}
        total_start = time.time()

        for eq_type in equipment_types:
            try:
                rul_result = self.train_rul_model(eq_type, n_cycles=n_cycles)
                results["rul_models"][eq_type] = rul_result
            except Exception as e:
                logger.error(f"❌ Error training RUL for {eq_type}: {e}")
                results["rul_models"][eq_type] = {"status": "error", "error": str(e)}

            try:
                ae_result = self.train_anomaly_detector(eq_type)
                results["anomaly_models"][eq_type] = ae_result
            except Exception as e:
                logger.error(f"❌ Error training AE for {eq_type}: {e}")
                results["anomaly_models"][eq_type] = {"status": "error", "error": str(e)}

        elapsed = time.time() - total_start
        results["total_training_time_sec"] = round(elapsed, 1)
        logger.info(f"🏁 All models trained in {elapsed:.1f}s")
        return results
