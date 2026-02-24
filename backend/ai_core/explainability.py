"""
RefineryIQ AI Core — Explainable AI (XAI) with SHAP
=====================================================
Provides SHAP-based explanations for RUL predictions so operators
understand *why* the model is predicting a failure, not just *what*.

Output example:
  "El riesgo es del 85% impulsado en un 40% por el aumento de vibration_x
   en las últimas 2 horas y un 30% por la caída de pressure_ratio"
"""

import logging
import numpy as np
import torch
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("RefineryIQ_XAI")


class SHAPExplainer:
    """
    SHAP-based explanation engine for RUL and anomaly predictions.

    Uses a gradient-based approximation compatible with PyTorch LSTM models.
    Falls back to permutation-based importance if SHAP is unavailable.
    """

    def __init__(self, feature_names: List[str]):
        self.feature_names = feature_names
        self._shap_available = False
        try:
            import shap
            self._shap = shap
            self._shap_available = True
            logger.info("✅ SHAP library available for explanations")
        except ImportError:
            logger.warning("⚠️ SHAP not installed — using permutation-based fallback")

    # ------------------------------------------------------------------ #
    #  Main API                                                           #
    # ------------------------------------------------------------------ #
    def explain_prediction(
        self,
        model: torch.nn.Module,
        input_window: np.ndarray,
        background_data: Optional[np.ndarray] = None,
    ) -> Dict:
        """
        Generate feature-level explanations for a single prediction.

        Parameters
        ----------
        model : torch.nn.Module
            Trained LSTM or Autoencoder model.
        input_window : np.ndarray
            Shape (seq_len, n_features).
        background_data : np.ndarray, optional
            Shape (n_background, seq_len, n_features) for SHAP baseline.

        Returns
        -------
        dict with keys:
            - feature_importance: {feature_name: float} percentage contributions
            - raw_shap_values: np.ndarray per-feature SHAP values
            - top_drivers: list of (feature, pct, direction) tuples
        """
        if self._shap_available and background_data is not None:
            return self._explain_with_shap(model, input_window, background_data)
        else:
            return self._explain_with_permutation(model, input_window)

    def generate_narrative(
        self,
        explanation: Dict,
        rul_hours: float,
        anomaly_score: Optional[float] = None,
        lang: str = "es",
    ) -> str:
        """
        Generate a human-readable narrative from explanation results.

        Parameters
        ----------
        explanation : dict
            Output from ``explain_prediction``.
        rul_hours : float
            Predicted remaining useful life in hours.
        anomaly_score : float, optional
            Anomaly score from autoencoder.
        lang : str
            Language code ("es" for Spanish, "en" for English).

        Returns
        -------
        str — Natural language explanation.
        """
        top_drivers = explanation.get("top_drivers", [])

        # Calculate risk percentage from RUL
        risk_pct = self._rul_to_risk_pct(rul_hours)

        if lang == "es":
            return self._narrative_es(risk_pct, rul_hours, top_drivers, anomaly_score)
        else:
            return self._narrative_en(risk_pct, rul_hours, top_drivers, anomaly_score)

    # ------------------------------------------------------------------ #
    #  SHAP-based explanation                                             #
    # ------------------------------------------------------------------ #
    def _explain_with_shap(
        self,
        model: torch.nn.Module,
        input_window: np.ndarray,
        background_data: np.ndarray,
    ) -> Dict:
        """Use SHAP DeepExplainer for attribution."""
        model.eval()
        device = next(model.parameters()).device

        bg = torch.tensor(background_data, dtype=torch.float32).to(device)
        inp = torch.tensor(input_window, dtype=torch.float32).unsqueeze(0).to(device)

        try:
            explainer = self._shap.DeepExplainer(model, bg)
            shap_values = explainer.shap_values(inp)

            if isinstance(shap_values, list):
                shap_values = shap_values[0]

            shap_array = np.array(shap_values).squeeze()  # (seq_len, n_features)

            return self._process_shap_values(shap_array)

        except Exception as e:
            logger.warning(f"SHAP DeepExplainer failed: {e}, using permutation fallback")
            return self._explain_with_permutation(model, input_window)

    # ------------------------------------------------------------------ #
    #  Permutation-based fallback                                         #
    # ------------------------------------------------------------------ #
    def _explain_with_permutation(
        self,
        model: torch.nn.Module,
        input_window: np.ndarray,
        n_permutations: int = 30,
    ) -> Dict:
        """
        Permutation importance: shuffle each feature and measure
        change in prediction.
        """
        model.eval()
        device = next(model.parameters()).device

        inp = torch.tensor(input_window, dtype=torch.float32).unsqueeze(0).to(device)

        with torch.no_grad():
            baseline_pred = model(inp).item()

        importances = np.zeros(len(self.feature_names))

        for feat_idx in range(len(self.feature_names)):
            deltas = []
            for _ in range(n_permutations):
                permuted = input_window.copy()
                np.random.shuffle(permuted[:, feat_idx])
                inp_perm = torch.tensor(permuted, dtype=torch.float32).unsqueeze(0).to(device)
                with torch.no_grad():
                    perm_pred = model(inp_perm).item()
                deltas.append(abs(baseline_pred - perm_pred))
            importances[feat_idx] = np.mean(deltas)

        return self._process_importance_values(importances, input_window)

    # ------------------------------------------------------------------ #
    #  Processing helpers                                                  #
    # ------------------------------------------------------------------ #
    def _process_shap_values(self, shap_array: np.ndarray) -> Dict:
        """Convert raw SHAP values into structured explanation."""
        # Aggregate across time: mean of absolute SHAP values per feature
        if shap_array.ndim == 2:
            feature_importance_raw = np.abs(shap_array).mean(axis=0)
        else:
            feature_importance_raw = np.abs(shap_array)

        total = feature_importance_raw.sum()
        if total == 0:
            total = 1.0

        feature_importance = {
            name: round(float(val / total * 100), 1)
            for name, val in zip(self.feature_names, feature_importance_raw)
        }

        # Top drivers sorted by importance
        sorted_features = sorted(
            feature_importance.items(), key=lambda x: x[1], reverse=True
        )

        # Determine direction (sign of recent SHAP values)
        if shap_array.ndim == 2:
            recent_shap = shap_array[-5:].mean(axis=0)
        else:
            recent_shap = shap_array

        top_drivers = []
        for name, pct in sorted_features[:5]:
            idx = self.feature_names.index(name)
            direction = "aumento" if recent_shap[idx] > 0 else "disminución"
            top_drivers.append((name, pct, direction))

        return {
            "feature_importance": feature_importance,
            "raw_shap_values": shap_array,
            "top_drivers": top_drivers,
        }

    def _process_importance_values(
        self, importances: np.ndarray, input_window: np.ndarray
    ) -> Dict:
        """Convert permutation importances into structured explanation."""
        total = importances.sum()
        if total == 0:
            total = 1.0

        feature_importance = {
            name: round(float(val / total * 100), 1)
            for name, val in zip(self.feature_names, importances)
        }

        sorted_features = sorted(
            feature_importance.items(), key=lambda x: x[1], reverse=True
        )

        # Direction: compare last 5 vs first 5 readings
        top_drivers = []
        for name, pct in sorted_features[:5]:
            idx = self.feature_names.index(name)
            recent_avg = input_window[-5:, idx].mean()
            early_avg = input_window[:5, idx].mean()
            direction = "aumento" if recent_avg > early_avg else "disminución"
            top_drivers.append((name, pct, direction))

        return {
            "feature_importance": feature_importance,
            "raw_shap_values": importances,
            "top_drivers": top_drivers,
        }

    # ------------------------------------------------------------------ #
    #  Narrative generation                                                #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _rul_to_risk_pct(rul_hours: float) -> float:
        """Convert RUL hours into a 0-100% risk score."""
        if rul_hours <= 0:
            return 99.0
        elif rul_hours >= 720:
            return max(1.0, 5.0)
        else:
            # Exponential decay risk curve
            return round(min(99.0, 100.0 * np.exp(-rul_hours / 168.0)), 1)

    def _narrative_es(
        self,
        risk_pct: float,
        rul_hours: float,
        top_drivers: List[Tuple],
        anomaly_score: Optional[float],
    ) -> str:
        """Generate Spanish narrative."""
        parts = [
            f"El riesgo de fallo es del {risk_pct:.0f}% "
            f"(vida útil remanente estimada: {rul_hours:.0f} horas)"
        ]

        if top_drivers:
            driver_strs = []
            for name, pct, direction in top_drivers[:3]:
                name_display = name.replace("_", " ")
                driver_strs.append(
                    f"{pct:.0f}% por el {direction} de {name_display}"
                )
            parts.append("impulsado en un " + ", ".join(driver_strs))

        if anomaly_score is not None and anomaly_score > 0.5:
            parts.append(
                f"⚠️ Anomalía Zero-Day detectada (score: {anomaly_score:.2f})"
            )

        return ", ".join(parts) + "."

    def _narrative_en(
        self,
        risk_pct: float,
        rul_hours: float,
        top_drivers: List[Tuple],
        anomaly_score: Optional[float],
    ) -> str:
        """Generate English narrative."""
        parts = [
            f"Failure risk at {risk_pct:.0f}% "
            f"(estimated RUL: {rul_hours:.0f} hours)"
        ]

        if top_drivers:
            driver_strs = []
            for name, pct, direction in top_drivers[:3]:
                dir_en = "increase" if direction == "aumento" else "decrease"
                driver_strs.append(f"{pct:.0f}% driven by {dir_en} in {name}")
            parts.append("driven by " + ", ".join(driver_strs))

        if anomaly_score is not None and anomaly_score > 0.5:
            parts.append(
                f"⚠️ Zero-Day anomaly detected (score: {anomaly_score:.2f})"
            )

        return ", ".join(parts) + "."
