"""
RefineryIQ AI Core — Digital Twin Data Generator
==================================================
Physics-informed synthetic data generation using Brownian motion (Wiener
process) and Markov chain state transitions to simulate realistic equipment
degradation cycles for PUMPs, COMPRESSORs, VALVEs, EXCHANGERs, and FURNACEs.

Replaces naive ``np.random.randn`` generation with run-to-failure profiles
that model gradual wear, anomalous spikes, and eventual breakdown.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from ai_core.config import (
    EQUIPMENT_PROFILES,
    MARKOV_TRANSITIONS,
    EquipmentProfile,
)

logger = logging.getLogger("RefineryIQ_DataGen")


class DigitalTwinGenerator:
    """Generates realistic run-to-failure degradation datasets."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    # --------------------------------------------------------------------- #
    #  Core: Single degradation cycle                                        #
    # --------------------------------------------------------------------- #
    def generate_degradation_cycle(
        self,
        equipment_type: str,
        duration_hours: int = 4320,
        sample_interval_min: int = 15,
        cycle_id: int = 0,
        equipment_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Simulate one run-to-failure cycle using Brownian motion with drift.

        Parameters
        ----------
        equipment_type : str
            Key in ``EQUIPMENT_PROFILES`` (e.g. "PUMP").
        duration_hours : int
            Maximum duration in hours for the cycle.
        sample_interval_min : int
            Sampling interval in minutes (default 15-min ~ typical SCADA).
        cycle_id : int
            Identifier for this degradation cycle.
        equipment_id : str, optional
            If not given, auto-generated from equipment_type + cycle_id.

        Returns
        -------
        pd.DataFrame
            Columns: timestamp, equipment_id, equipment_type, cycle_id,
            <feature columns>, rul_hours, state
        """
        profile = EQUIPMENT_PROFILES.get(equipment_type)
        if profile is None:
            raise ValueError(
                f"Unknown equipment type '{equipment_type}'. "
                f"Available: {list(EQUIPMENT_PROFILES)}"
            )

        if equipment_id is None:
            equipment_id = f"{equipment_type}-{cycle_id:04d}"

        n_steps = int(duration_hours * 60 / sample_interval_min)
        dt = sample_interval_min / 60.0  # time step in hours

        # Randomize actual failure point (70-100% of max duration)
        failure_hour = int(self.rng.uniform(0.7, 1.0) * duration_hours)
        n_steps = min(n_steps, int(failure_hour * 60 / sample_interval_min) + 10)

        # Initialize sensors at nominal values
        sensor_values = {f: profile.nominal_values[f] for f in profile.features}
        records: List[Dict] = []
        state = "NORMAL"
        start_time = datetime.now() - timedelta(hours=duration_hours)

        for step in range(n_steps):
            current_hour = step * dt
            remaining = max(0.0, failure_hour - current_hour)

            # --- Markov state transition ---
            state = self._transition_state(state, remaining, failure_hour)

            # --- State-dependent drift multiplier ---
            drift_mult = self._get_drift_multiplier(state)

            # --- Update each sensor via Brownian motion ---
            for feat in profile.features:
                mu = profile.drift_rates[feat] * drift_mult
                sigma = profile.volatilities[feat]

                # Brownian increment: X(t+dt) = X(t) + μ·dt + σ·√dt·Z
                dW = self.rng.normal(0, 1)
                increment = mu * dt + sigma * np.sqrt(dt) * dW

                # Inject anomalous spikes in PRE_FAILURE state
                if state == "PRE_FAILURE" and self.rng.random() < 0.05:
                    spike_dir = np.sign(mu) if mu != 0 else 1.0
                    increment += spike_dir * sigma * self.rng.uniform(2, 5)

                sensor_values[feat] += increment

                # Clamp to physically realistic bounds
                nominal = profile.nominal_values[feat]
                threshold = profile.failure_thresholds[feat]
                lo = min(nominal, threshold) * 0.5
                hi = max(nominal, threshold) * 1.5
                sensor_values[feat] = np.clip(sensor_values[feat], lo, hi)

            # Build record
            record = {
                "timestamp": start_time + timedelta(minutes=step * sample_interval_min),
                "equipment_id": equipment_id,
                "equipment_type": equipment_type,
                "cycle_id": cycle_id,
                "rul_hours": round(remaining, 2),
                "state": state,
            }
            record.update({f: round(sensor_values[f], 4) for f in profile.features})
            records.append(record)

            if state == "FAILURE":
                break

        df = pd.DataFrame(records)
        logger.info(
            f"✅ Generated cycle {cycle_id} for {equipment_type}: "
            f"{len(df)} samples, failure at ~{failure_hour}h"
        )
        return df

    # --------------------------------------------------------------------- #
    #  Batch: multiple cycles for multiple equipment types                    #
    # --------------------------------------------------------------------- #
    def generate_dataset(
        self,
        n_cycles_per_type: int = 10,
        equipment_types: Optional[List[str]] = None,
        duration_hours: int = 4320,
    ) -> pd.DataFrame:
        """
        Generate a full training dataset with multiple run-to-failure cycles.

        Parameters
        ----------
        n_cycles_per_type : int
            Number of degradation cycles per equipment type.
        equipment_types : list, optional
            Equipment types to generate. Defaults to all profiles.
        duration_hours : int
            Max cycle duration in hours.

        Returns
        -------
        pd.DataFrame
        """
        if equipment_types is None:
            equipment_types = list(EQUIPMENT_PROFILES.keys())

        all_frames: List[pd.DataFrame] = []
        global_cycle = 0

        for eq_type in equipment_types:
            for i in range(n_cycles_per_type):
                df_cycle = self.generate_degradation_cycle(
                    equipment_type=eq_type,
                    duration_hours=duration_hours,
                    cycle_id=global_cycle,
                    equipment_id=f"{eq_type}-{i:04d}",
                )
                all_frames.append(df_cycle)
                global_cycle += 1

        dataset = pd.concat(all_frames, ignore_index=True)
        logger.info(
            f"📊 Full dataset: {len(dataset)} total samples across "
            f"{global_cycle} cycles for {equipment_types}"
        )
        return dataset

    # --------------------------------------------------------------------- #
    #  Normal-only dataset for Autoencoder training                          #
    # --------------------------------------------------------------------- #
    def generate_normal_dataset(
        self,
        equipment_type: str,
        n_samples: int = 5000,
    ) -> pd.DataFrame:
        """
        Generate samples from the NORMAL operating state only (no degradation).
        Used to train the Autoencoder on healthy behavior.
        """
        profile = EQUIPMENT_PROFILES[equipment_type]
        records = []
        for _ in range(n_samples):
            record = {}
            for feat in profile.features:
                nom = profile.nominal_values[feat]
                vol = profile.volatilities[feat]
                record[feat] = nom + self.rng.normal(0, vol * 0.3)
            records.append(record)
        return pd.DataFrame(records)

    # --------------------------------------------------------------------- #
    #  Internal helpers                                                       #
    # --------------------------------------------------------------------- #
    def _transition_state(
        self, current_state: str, remaining_hours: float, total_hours: float
    ) -> str:
        """Markov chain state transition modulated by degradation progress."""
        probs = MARKOV_TRANSITIONS[current_state].copy()

        # Increase transition probability as we approach failure
        progress = 1.0 - (remaining_hours / max(total_hours, 1))

        if current_state == "NORMAL" and progress > 0.5:
            boost = min(0.05, progress * 0.02)
            probs["DEGRADING"] += boost
            probs["NORMAL"] -= boost

        elif current_state == "DEGRADING" and progress > 0.75:
            boost = min(0.08, (progress - 0.5) * 0.1)
            probs["PRE_FAILURE"] += boost
            probs["DEGRADING"] -= boost

        elif current_state == "PRE_FAILURE" and progress > 0.9:
            boost = min(0.15, (progress - 0.75) * 0.3)
            probs["FAILURE"] += boost
            probs["PRE_FAILURE"] -= boost

        states = list(probs.keys())
        probabilities = list(probs.values())
        # Ensure probabilities sum to 1
        total = sum(probabilities)
        probabilities = [p / total for p in probabilities]

        return self.rng.choice(states, p=probabilities)

    @staticmethod
    def _get_drift_multiplier(state: str) -> float:
        """Returns how much to amplify the drift rate per state."""
        return {
            "NORMAL": 1.0,
            "DEGRADING": 3.0,
            "PRE_FAILURE": 8.0,
            "FAILURE": 15.0,
        }.get(state, 1.0)
