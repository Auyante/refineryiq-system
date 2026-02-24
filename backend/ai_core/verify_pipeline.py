"""
RefineryIQ AI Core — Verification Pipeline
============================================
Standalone script to verify all components work end-to-end.

Run from the backend directory:
    python -m ai_core.verify_pipeline
"""

import sys
import os
import time
import numpy as np
import torch

# Ensure backend dir is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def divider(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_data_generator():
    """Test 1: Digital Twin Data Generator"""
    divider("TEST 1: Digital Twin Data Generator")

    from ai_core.data_generator import DigitalTwinGenerator
    from ai_core.config import EQUIPMENT_PROFILES

    gen = DigitalTwinGenerator(seed=42)

    # Single cycle
    df = gen.generate_degradation_cycle("PUMP", duration_hours=720, cycle_id=0)
    print(f"✅ Single cycle: {len(df)} samples")
    print(f"   Columns: {list(df.columns)}")
    print(f"   States: {df['state'].value_counts().to_dict()}")
    print(f"   RUL range: {df['rul_hours'].min():.1f} — {df['rul_hours'].max():.1f} hours")

    # Verify features are in expected range
    profile = EQUIPMENT_PROFILES["PUMP"]
    for feat in profile.features:
        vals = df[feat]
        print(f"   {feat}: min={vals.min():.2f}, max={vals.max():.2f}, mean={vals.mean():.2f}")

    # Multi-cycle dataset
    df_full = gen.generate_dataset(n_cycles_per_type=3, equipment_types=["PUMP", "COMPRESSOR"])
    print(f"✅ Full dataset: {len(df_full)} samples, {df_full['cycle_id'].nunique()} cycles")

    # Normal-only dataset
    df_normal = gen.generate_normal_dataset("PUMP", n_samples=500)
    print(f"✅ Normal dataset: {len(df_normal)} samples")

    assert len(df) > 100, "Single cycle too short"
    assert "rul_hours" in df.columns, "Missing rul_hours column"
    assert len(df_full) > len(df), "Multi-cycle should be larger"
    print("✅ TEST 1 PASSED")


def test_models():
    """Test 2: PyTorch Model Architectures"""
    divider("TEST 2: PyTorch Models (LSTM + Autoencoder)")

    from ai_core.models import LSTMRULModel, ConvAutoencoder, AsymmetricRULLoss
    from ai_core.config import WINDOW_SIZE

    n_features = 5
    batch_size = 8

    # LSTM RUL Model
    model = LSTMRULModel(n_features=n_features)
    x = torch.randn(batch_size, WINDOW_SIZE, n_features)
    out = model(x)
    print(f"✅ LSTM forward: input={x.shape} → output={out.shape}")
    assert out.shape == (batch_size, 1), f"Bad LSTM output shape: {out.shape}"
    assert (out >= 0).all(), "RUL should be non-negative"

    # Attention weights
    attn = model.attention_weights
    print(f"   Attention weights: {attn.shape}")
    assert attn.shape == (batch_size, WINDOW_SIZE, 1)

    # Asymmetric loss
    criterion = AsymmetricRULLoss(late_weight=2.0, early_weight=1.0)
    target = torch.rand(batch_size, 1) * 100
    loss = criterion(out, target)
    print(f"✅ Asymmetric loss: {loss.item():.4f}")

    # Gradient flow
    loss.backward()
    grad_ok = all(p.grad is not None for p in model.parameters() if p.requires_grad)
    print(f"✅ Gradient flow: {'OK' if grad_ok else 'BROKEN'}")
    assert grad_ok, "Broken gradient flow"

    # Convolutional Autoencoder
    ae = ConvAutoencoder(n_features=n_features, seq_len=WINDOW_SIZE)
    recon = ae(x)
    print(f"✅ Autoencoder forward: input={x.shape} → output={recon.shape}")
    assert recon.shape == x.shape, f"Bad AE output shape: {recon.shape}"

    # Anomaly detection
    scores = ae.compute_anomaly_score(x)
    print(f"   Anomaly scores: shape={scores.shape}, mean={scores.mean():.4f}")
    ae.set_threshold(scores, n_sigma=3.0)
    print(f"   Threshold set: {ae.threshold.item():.6f}")

    flags, scores2 = ae.is_anomaly(x)
    print(f"   Anomaly flags: {flags.sum().item()}/{len(flags)} detected")

    print("✅ TEST 2 PASSED")


def test_explainability():
    """Test 3: SHAP / Permutation Explainability"""
    divider("TEST 3: Explainable AI (XAI)")

    from ai_core.explainability import SHAPExplainer
    from ai_core.models import LSTMRULModel
    from ai_core.config import WINDOW_SIZE

    features = ["vibration_x", "vibration_y", "temperature", "pressure", "flow_rate"]
    explainer = SHAPExplainer(features)

    model = LSTMRULModel(n_features=len(features))
    model.eval()

    window = np.random.randn(WINDOW_SIZE, len(features)).astype(np.float32)

    # Permutation-based explanation (always available)
    explanation = explainer.explain_prediction(model, window)
    print(f"✅ Explanation generated:")
    print(f"   Feature importance: {explanation['feature_importance']}")
    print(f"   Top drivers: {explanation['top_drivers'][:3]}")

    assert "feature_importance" in explanation
    assert len(explanation["top_drivers"]) > 0

    # Narrative generation
    narrative = explainer.generate_narrative(
        explanation, rul_hours=48.0, anomaly_score=0.8, lang="es"
    )
    print(f"✅ Narrative (ES): {narrative[:120]}...")

    narrative_en = explainer.generate_narrative(
        explanation, rul_hours=48.0, anomaly_score=0.8, lang="en"
    )
    print(f"✅ Narrative (EN): {narrative_en[:120]}...")

    print("✅ TEST 3 PASSED")


def test_mlflow_manager():
    """Test 4: MLflow Manager"""
    divider("TEST 4: MLflow Manager")

    from ai_core.mlflow_manager import MLflowManager

    mgr = MLflowManager()
    print(f"   MLflow available: {mgr.available}")

    if mgr.available:
        mgr.set_experiment("RefineryIQ_Test")
        mgr.start_run(run_name="test_verification_run")
        mgr.log_params({"test_param": "value", "lr": 0.001})
        mgr.log_metrics({"test_rmse": 12.5, "test_r2": 0.85})
        mgr.end_run()
        print("✅ MLflow run logged successfully")
    else:
        print("⚠️ MLflow not available — skipping (non-blocking)")

    print("✅ TEST 4 PASSED")


def test_mini_training():
    """Test 5: Mini Training Loop (5 epochs, small data)"""
    divider("TEST 5: Mini Training Loop")

    from ai_core.data_generator import DigitalTwinGenerator
    from ai_core.models import LSTMRULModel, AsymmetricRULLoss
    from ai_core.training_pipeline import TrainingPipeline
    from ai_core.config import WINDOW_SIZE

    gen = DigitalTwinGenerator(seed=123)
    pipeline = TrainingPipeline()

    # Generate small dataset
    df = gen.generate_dataset(n_cycles_per_type=2, equipment_types=["PUMP"], duration_hours=720)
    features = ["vibration_x", "vibration_y", "temperature", "pressure", "flow_rate"]

    all_X, all_y = [], []
    for cid in df["cycle_id"].unique():
        dc = df[df["cycle_id"] == cid].sort_values("timestamp")
        if len(dc) < WINDOW_SIZE + 5:
            continue
        xc, yc = pipeline.prepare_sliding_windows(dc, features, window_size=WINDOW_SIZE)
        all_X.append(xc)
        all_y.append(yc)

    X = np.concatenate(all_X)
    y = np.concatenate(all_y)
    print(f"   Windows: X={X.shape}, y={y.shape}")

    # Normalize
    X_t, X_v, means, stds = pipeline.normalize_features(X[:100], X[100:150])

    # Mini train
    model = LSTMRULModel(n_features=len(features))
    criterion = AsymmetricRULLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    model.train()
    inp = torch.tensor(X_t[:32], dtype=torch.float32)
    tgt = torch.tensor(y[:32], dtype=torch.float32).unsqueeze(-1)

    losses = []
    for epoch in range(5):
        optimizer.zero_grad()
        pred = model(inp)
        loss = criterion(pred, tgt)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())
        print(f"   Epoch {epoch+1}/5 — Loss: {loss.item():.4f}")

    assert losses[-1] < losses[0] * 2, "Loss should not explode"
    print("✅ TEST 5 PASSED")


def test_inference_engine():
    """Test 6: Inference Engine End-to-End"""
    divider("TEST 6: Inference Engine")

    from ai_core.inference_engine import PredictiveMaintenanceEngine

    engine = PredictiveMaintenanceEngine()

    # Test status before init
    status = engine.get_engine_status()
    print(f"   Engine status: {status}")

    # Inject synthetic readings
    engine.inject_synthetic_readings("PUMP-TEST", "PUMP", n_readings=60)
    buf_size = len(engine.buffers.get("PUMP-TEST", []))
    print(f"   Buffer size after injection: {buf_size}")
    assert buf_size == 60, f"Expected 60 readings, got {buf_size}"

    # Test window extraction
    window = engine._get_window("PUMP-TEST", "PUMP")
    if window is not None:
        print(f"   Window shape: {window.shape}")
    else:
        print("   Window: None (no model stats loaded — expected before training)")

    print("✅ TEST 6 PASSED")


def main():
    print("\n" + "=" * 60)
    print("  RefineryIQ AI Core — Verification Pipeline")
    print("=" * 60)

    t0 = time.time()
    passed = 0
    failed = 0
    tests = [
        test_data_generator,
        test_models,
        test_explainability,
        test_mlflow_manager,
        test_mini_training,
        test_inference_engine,
    ]

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"❌ {test_fn.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    elapsed = time.time() - t0
    divider("RESULTS")
    print(f"  Passed: {passed}/{len(tests)}")
    print(f"  Failed: {failed}/{len(tests)}")
    print(f"  Time: {elapsed:.1f}s")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
