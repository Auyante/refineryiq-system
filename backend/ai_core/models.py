"""
RefineryIQ AI Core — PyTorch Model Architectures
==================================================
1. LSTMRULModel  — Bidirectional LSTM with Attention for RUL prediction
2. ConvAutoencoder — 1D Convolutional Autoencoder for anomaly detection
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple

from ai_core.config import (
    LSTM_HIDDEN_DIM,
    LSTM_NUM_LAYERS,
    LSTM_DROPOUT,
    LSTM_BIDIRECTIONAL,
    AE_LATENT_DIM,
)


# ============================================================================
# 1. LSTM with Attention for Remaining Useful Life (RUL)
# ============================================================================

class TemporalAttention(nn.Module):
    """Additive (Bahdanau-style) attention over LSTM hidden states."""

    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.Tanh(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, lstm_output: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Parameters
        ----------
        lstm_output : (batch, seq_len, hidden_dim)

        Returns
        -------
        context : (batch, hidden_dim)
        weights : (batch, seq_len, 1)
        """
        scores = self.attn(lstm_output)          # (B, T, 1)
        weights = F.softmax(scores, dim=1)       # (B, T, 1)
        context = (lstm_output * weights).sum(dim=1)  # (B, H)
        return context, weights


class LSTMRULModel(nn.Module):
    """
    Bidirectional LSTM → Temporal Attention → FC → RUL prediction.

    Input:  (batch, seq_len, n_features)
    Output: (batch, 1)  — predicted RUL in hours
    """

    def __init__(
        self,
        n_features: int,
        hidden_dim: int = LSTM_HIDDEN_DIM,
        n_layers: int = LSTM_NUM_LAYERS,
        dropout: float = LSTM_DROPOUT,
        bidirectional: bool = LSTM_BIDIRECTIONAL,
    ):
        super().__init__()
        self.n_features = n_features
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        self.bidirectional = bidirectional
        self.n_directions = 2 if bidirectional else 1

        # Input batch normalization
        self.input_bn = nn.BatchNorm1d(n_features)

        # LSTM
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_dim,
            num_layers=n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
            bidirectional=bidirectional,
        )

        lstm_out_dim = hidden_dim * self.n_directions

        # Attention
        self.attention = TemporalAttention(lstm_out_dim)

        # Regression head
        self.fc = nn.Sequential(
            nn.Linear(lstm_out_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout / 2),
            nn.Linear(hidden_dim // 2, 1),
            nn.ReLU(),  # RUL is always ≥ 0
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x : (batch, seq_len, n_features)

        Returns
        -------
        rul : (batch, 1)
        """
        # Batch norm across features (permute to B, F, T then back)
        x = x.permute(0, 2, 1)
        x = self.input_bn(x)
        x = x.permute(0, 2, 1)

        # LSTM encoding
        lstm_out, _ = self.lstm(x)  # (B, T, H*dirs)

        # Attention pooling
        context, self._attn_weights = self.attention(lstm_out)  # (B, H*dirs)

        # Regression
        rul = self.fc(context)  # (B, 1)
        return rul

    @property
    def attention_weights(self) -> torch.Tensor:
        """Access last computed attention weights for interpretability."""
        return self._attn_weights


# ============================================================================
# Asymmetric RUL Loss (penalise late predictions more than early)
# ============================================================================

class AsymmetricRULLoss(nn.Module):
    """
    Asymmetric loss for RUL prediction.

    Late predictions (predicted RUL > actual → equipment fails unexpectedly)
    are penalized more heavily than early predictions.
    """

    def __init__(self, late_weight: float = 2.0, early_weight: float = 1.0):
        super().__init__()
        self.late_weight = late_weight
        self.early_weight = early_weight

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        diff = pred - target  # positive = over-estimate (late), negative = under-estimate (early)
        weights = torch.where(diff > 0, self.late_weight, self.early_weight)
        loss = weights * (diff ** 2)
        return loss.mean()


# ============================================================================
# 2. 1D Convolutional Autoencoder for Anomaly Detection
# ============================================================================

class ConvAutoencoder(nn.Module):
    """
    1D Convolutional Autoencoder for detecting Zero-Day anomalies.

    Trained on NORMAL data only. At inference, high reconstruction error
    indicates an anomaly unseen during training.

    Input:  (batch, seq_len, n_features)
    Output: (batch, seq_len, n_features)  — reconstruction
    """

    def __init__(
        self,
        n_features: int,
        seq_len: int = 50,
        latent_dim: int = AE_LATENT_DIM,
    ):
        super().__init__()
        self.n_features = n_features
        self.seq_len = seq_len
        self.latent_dim = latent_dim

        # Encoder: Conv1d expects (B, C, L) where C=features, L=seq_len
        self.encoder = nn.Sequential(
            nn.Conv1d(n_features, 32, kernel_size=7, padding=3),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            nn.Conv1d(32, 16, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.BatchNorm1d(16),
            nn.Conv1d(16, latent_dim, kernel_size=3, padding=1),
            nn.ReLU(),
        )

        # Decoder: mirror of encoder
        self.decoder = nn.Sequential(
            nn.ConvTranspose1d(latent_dim, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(16),
            nn.ConvTranspose1d(16, 32, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            nn.ConvTranspose1d(32, n_features, kernel_size=7, padding=3),
        )

        # Anomaly threshold (set during training)
        self.register_buffer("threshold", torch.tensor(float("inf")))
        self.register_buffer("recon_mean", torch.tensor(0.0))
        self.register_buffer("recon_std", torch.tensor(1.0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x : (batch, seq_len, n_features)

        Returns
        -------
        reconstructed : (batch, seq_len, n_features)
        """
        # (B, T, F) → (B, F, T) for Conv1d
        x_t = x.permute(0, 2, 1)
        latent = self.encoder(x_t)
        decoded = self.decoder(latent)
        return decoded.permute(0, 2, 1)  # back to (B, T, F)

    def compute_anomaly_score(self, x: torch.Tensor) -> torch.Tensor:
        """
        Compute per-sample reconstruction error (anomaly score).

        Returns
        -------
        scores : (batch,) MSE per sample
        """
        with torch.no_grad():
            recon = self.forward(x)
            mse = ((x - recon) ** 2).mean(dim=(1, 2))
        return mse

    def is_anomaly(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Detect anomalies by comparing reconstruction error to threshold.

        Returns
        -------
        flags : (batch,) bool tensor
        scores : (batch,) anomaly scores
        """
        scores = self.compute_anomaly_score(x)
        flags = scores > self.threshold
        return flags, scores

    def set_threshold(self, normal_scores: torch.Tensor, n_sigma: float = 3.0):
        """
        Set anomaly threshold from reconstruction errors on normal data.
        threshold = mean + n_sigma * std
        """
        self.recon_mean = normal_scores.mean()
        self.recon_std = normal_scores.std()
        self.threshold = self.recon_mean + n_sigma * self.recon_std
