import os
import json
import re
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import joblib
from datetime import datetime
import sys

# ── Portable path import ──────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATASET_PATH, MODEL_PATH, SCALER_PATH, ML_RESULTS_PATH
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────
# FEATURES USED FOR ML
# ─────────────────────────────────────────────
FEATURES = [
    "usagestats_size",
    "dropbox_count",
    "dropbox_size",
    "notification_entries",
    "notification_size",
    "packages_size",
    "netstats_size",
    "ishredder_pdf",
    "shreddit_count",
    "secure_eraser_ts",
    "factory_reset",
    "unknown_wiping_app_detected"
]


def load_dataset():
    """Load and prepare dataset for training."""
    print("\n[📊] Loading dataset...")
    df = pd.read_csv(DATASET_PATH)

      # ── R11 compatibility ──────────────────────────────────────────
    # R11 detects ANY unknown wiping app behaviorally.
    # Column missing because R11 was added after dataset was built
    # and never fired on any scan — so 0 is correct for all rows.
    if "unknown_wiping_app_detected" not in df.columns:
        print("[INFO] unknown_wiping_app_detected not in dataset — zero-filling (R11             never fired)")
        df["unknown_wiping_app_detected"] = 0
    # ──────────────────────────────────────────────────────────────

    print(f"[✅] Loaded {len(df)} samples")
    print(f"   Normal:  {len(df[df['label'] == 'normal'])}")
    print(f"   Anomaly: {len(df[df['label'] == 'anomaly'])}")
    return df


def prepare_features(df):
    """Extract and scale feature matrix."""
    # Select only feature columns
    available_features = [f for f in FEATURES if f in df.columns]
    X = df[available_features].fillna(0)

    # Convert secure_eraser_ts to binary
    # (0 = not used, 1 = used) — timestamp too large for scaling
    if "secure_eraser_ts" in X.columns:
        X["secure_eraser_ts"] = (X["secure_eraser_ts"] > 0).astype(int)

    return X, available_features


def train_model(df):
    """
    Train Isolation Forest on normal samples only.
    Isolation Forest learns what normal looks like
    then flags deviations as anomalies.
    """
    print("\n[🤖] Training Isolation Forest model...")

    X, features = prepare_features(df)

    # Train only on normal samples
    X_normal = X[df['label'] == 'normal']
    print(f"[✅] Training on {len(X_normal)} normal samples")
    print(f"[✅] Features used: {features}")

    # Scale features
    scaler = StandardScaler()
    X_normal_scaled = scaler.fit_transform(X_normal)

    # Train Isolation Forest
    # contamination = expected proportion of anomalies in new data
    # Lowered from 0.3 -> 0.18 after testing confirmed this parameter
    # (not the data overlap) was the direct cause of normal samples
    # being misclassified as anomaly at a near-constant ~30% rate
    # regardless of dataset changes. 0.18 still keeps the model
    # sensitive to real anomalies while reducing false positives.
    model = IsolationForest(
        n_estimators=100,
        contamination=0.18,
        random_state=42
    )
    model.fit(X_normal_scaled)

    print(f"[✅] Model trained successfully")

    # Save model and scaler
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"[✅] Model saved: {MODEL_PATH}")
    print(f"[✅] Scaler saved: {SCALER_PATH}")

    return model, scaler, features


def validate_model(df, model, scaler, features):
    """
    Validate model on all samples.
    Compare ML predictions vs actual labels.
    """
    print("\n[🔍] Validating model on all samples...")

    X, _ = prepare_features(df)
    X_scaled = scaler.transform(X[features])

    # Predict — IsolationForest returns:
    # 1 = normal (inlier)
    # -1 = anomaly (outlier)
    predictions = model.predict(X_scaled)
    scores = model.score_samples(X_scaled)

    # Convert to our labels
    pred_labels = ["anomaly" if p == -1 else "normal" for p in predictions]
    actual_labels = df['label'].tolist()

    # Calculate accuracy
    correct = sum(1 for p, a in zip(pred_labels, actual_labels) if p == a)
    accuracy = round((correct / len(actual_labels)) * 100, 1)

    print(f"\n[✅] Validation Results:")
    print(f"   Accuracy: {accuracy}%")
    print(f"   Correct:  {correct}/{len(actual_labels)}")

    print(f"\n   {'Scan':<35} {'Actual':<10} {'Predicted':<10} {'Score':<10} {'Match'}")
    print(f"   {'-'*75}")

    results = []
    for i, (scan, actual, predicted, score) in enumerate(
        zip(df['scan'], actual_labels, pred_labels, scores)
    ):
        match = "✅" if actual == predicted else "❌"
        print(f"   {scan:<35} {actual:<10} {predicted:<10} {score:<10.4f} {match}")
        results.append({
            "scan": scan,
            "actual": actual,
            "predicted": predicted,
            "score": float(score),
            "correct": actual == predicted
        })

    # Classification report
    print(f"\n[📊] Classification Report:")
    print(classification_report(actual_labels, pred_labels))

    # Confusion matrix
    cm = confusion_matrix(actual_labels, pred_labels,
                          labels=["normal", "anomaly"])
    print(f"[📊] Confusion Matrix:")
    print(f"   {'':15} Predicted Normal  Predicted Anomaly")
    print(f"   Actual Normal  {cm[0][0]:<18} {cm[0][1]}")
    print(f"   Actual Anomaly {cm[1][0]:<18} {cm[1][1]}")

    return results, accuracy


def predict_scan(scan_folder, baseline_folder=None):
    """
    Predict if a new scan folder shows anomalous behavior.
    This is called from app.py during live scanning.
    """
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        return {
            "ml_prediction": "unknown",
            "ml_score": 0,
            "ml_confidence": 0,
            "error": "Model not trained yet"
        }

    # Load model and scaler
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    # Extract features from scan folder
    from build_dataset import extract_features
    features = extract_features(scan_folder)

    # Prepare feature vector
    feature_values = []
    for f in FEATURES:
        val = features.get(f, 0)
        # Convert secure_eraser_ts to binary
        if f == "secure_eraser_ts":
            val = 1 if val > 0 else 0
        # unknown_wiping_app_detected is already binary from rule_engine.py
        # (R11 fired = 1, not fired = 0) — no conversion needed
        feature_values.append(val)

    X = np.array(feature_values).reshape(1, -1)
    X_scaled = scaler.transform(X)

    # Predict
    prediction = model.predict(X_scaled)[0]
    score = model.score_samples(X_scaled)[0]

    # Convert score to confidence percentage
    # More negative score = more anomalous
    ml_label = "anomaly" if prediction == -1 else "normal"

    # Normalize score to 0-100 confidence
    # Typical scores range from -0.5 to 0.5
    normalized = min(max(((-score) + 0.5) * 100, 0), 100)
    ml_confidence = round(normalized, 1)

    return {
        "ml_prediction": ml_label,
        "ml_score": round(float(score), 4),
        "ml_confidence": ml_confidence,
        "features_used": FEATURES,
        "feature_values": feature_values
    }


LIVE_SCAN_PATTERN = re.compile(r"^scan_\d{8}_\d{6}$")


def merge_live_scan_entries(dataset_scan_names, results_path):
    """
    Preserve any "live" scan entries (created by the dashboard's
    "Run New Scan" button via app.py's update_ml_results()) that are
    NOT part of the training dataset.csv, so retraining the model
    doesn't wipe out your dashboard scan history.

    IMPORTANT: a scan only counts as "live" if its name actually
    matches the dashboard's real scan-folder naming pattern
    (scan_YYYYMMDD_HHMMSS) AND it's no longer in the dataset.
    Just checking "not in dataset.csv" used to also catch stale
    synthetic_* rows left behind from a previous dataset version
    (e.g. synthetic_normal_31 after the dataset was reset to fewer
    samples) — those are NOT real dashboard scans and should be
    dropped, not preserved forever.
    """
    if not os.path.exists(results_path):
        return []

    try:
        with open(results_path, "r") as f:
            old_data = json.load(f)
    except Exception:
        return []

    old_vr = old_data.get("validation_results", [])
    dataset_scan_names = set(dataset_scan_names)

    live_entries = [
        r for r in old_vr
        if r.get("scan") not in dataset_scan_names
        and LIVE_SCAN_PATTERN.match(r.get("scan", ""))
    ]

    if live_entries:
        print(f"[INFO] Preserving {len(live_entries)} live dashboard scan(s) "
              f"not present in dataset.csv: "
              f"{[r['scan'] for r in live_entries]}")

    return live_entries


def train_and_validate():
    """Main function — train model and validate."""
    print("\n" + "="*55)
    print("  DroidSentinel — ML Detector v1.0")
    print("  Isolation Forest Anomaly Detection")
    print("="*55)

    # Load dataset
    df = load_dataset()

    # Train model
    model, scaler, features = train_model(df)

    # Validate
    results, accuracy = validate_model(df, model, scaler, features)

    results_path = ML_RESULTS_PATH

    # ── Preserve live dashboard scans not part of dataset.csv ──
    live_entries = merge_live_scan_entries(df['scan'].tolist(), results_path)
    merged_results = results + live_entries

    # Save validation results
    output = {
        "training_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_samples": len(df),
        "normal_samples": len(df[df['label'] == 'normal']),
        "anomaly_samples": len(df[df['label'] == 'anomaly']),
        "accuracy": accuracy,
        "features": features,
        "r11_note": "unknown_wiping_app_detected: binary feature for R11 — detects any   unknown wiping app by behavioral signature (storage perms + no network + active   usage). Zero-filled as R11 never fired on any scan.",
        "validation_results": merged_results
    }

    with open(results_path, 'w') as f:
        json.dump(output, f, indent=4)

    print(f"\n[✅] ML results saved: {results_path}")
    if live_entries:
        print(f"[✅] Merged in {len(live_entries)} preserved live dashboard scan(s)")

    print("\n" + "="*55)
    print(f"  FINAL ML ACCURACY: {accuracy}%")
    print("="*55)

    return output


if __name__ == "__main__":
    train_and_validate()