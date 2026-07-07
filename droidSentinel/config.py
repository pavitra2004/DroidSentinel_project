# config.py
# Centralized path configuration for DroidSentinel.
#
# Instead of hardcoding "D:\DroidSentinel\..." in every script, every
# script imports its paths from here. This file auto-detects the
# project's own root folder (the folder this file lives in), so the
# entire project becomes portable — copy the whole DroidSentinel folder
# anywhere (any drive letter, any machine, any folder name) and it will
# still work without editing a single path.
#
# HOW IT WORKS:
#   PROJECT_ROOT is computed from this file's own location on disk,
#   using Python's __file__. Wherever config.py physically sits, that
#   folder is treated as the project root, and every other path is
#   built relative to it.
#
# REQUIRED FOLDER STRUCTURE (must stay consistent wherever it's copied):
#   DroidSentinel/
#     ├── config.py            <- this file
#     ├── app.py
#     ├── report_generator.py
#     ├── collector/
#     │     └── artifact_collector.py
#     ├── engine/
#     │     ├── rule_engine.py
#     │     ├── ml_detector.py
#     │     ├── build_dataset.py
#     │     ├── add_real_sample.py
#     │     ├── generate_synthetic_data.py
#     │     ├── dataset.csv
#     │     ├── ml_results.json
#     │     ├── isolation_forest_model.pkl
#     │     └── scaler.pkl
#     └── scans/
#           └── baseline_scan/  (and all other scan_* folders)

import os

# ─────────────────────────────────────────────
# PROJECT ROOT — auto-detected, do not hardcode
# ─────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
# DERIVED PATHS — used throughout the project
# ─────────────────────────────────────────────
SCANS_DIR     = os.path.join(PROJECT_ROOT, "scans")
ENGINE_DIR    = os.path.join(PROJECT_ROOT, "engine")
COLLECTOR_DIR = os.path.join(PROJECT_ROOT, "collector")

BASELINE_SCAN_DIR = os.path.join(SCANS_DIR, "baseline_scan")

DATASET_PATH       = os.path.join(ENGINE_DIR, "dataset.csv")
ML_RESULTS_PATH    = os.path.join(ENGINE_DIR, "ml_results.json")
MODEL_PATH         = os.path.join(ENGINE_DIR, "isolation_forest_model.pkl")
SCALER_PATH        = os.path.join(ENGINE_DIR, "scaler.pkl")


def ensure_directories():
    """
    Create the core folder structure if it doesn't exist yet.
    Safe to call multiple times — only creates missing folders.
    Useful when this project is copied to a brand new machine for
    the first time and the scans/engine folders don't exist yet.
    """
    for folder in (SCANS_DIR, ENGINE_DIR, COLLECTOR_DIR):
        os.makedirs(folder, exist_ok=True)


if __name__ == "__main__":
    # Quick sanity check you can run directly:
    #   python config.py
    # to confirm paths resolve correctly on this machine.
    print("DroidSentinel — Path Configuration")
    print("=" * 50)
    print(f"PROJECT_ROOT:       {PROJECT_ROOT}")
    print(f"SCANS_DIR:          {SCANS_DIR}")
    print(f"ENGINE_DIR:         {ENGINE_DIR}")
    print(f"COLLECTOR_DIR:      {COLLECTOR_DIR}")
    print(f"BASELINE_SCAN_DIR:  {BASELINE_SCAN_DIR}")
    print(f"DATASET_PATH:       {DATASET_PATH}")
    print(f"ML_RESULTS_PATH:    {ML_RESULTS_PATH}")
    print(f"MODEL_PATH:         {MODEL_PATH}")
    print(f"SCALER_PATH:        {SCALER_PATH}")
    print("=" * 50)
    print(f"PROJECT_ROOT exists on disk: {os.path.exists(PROJECT_ROOT)}")
    print(f"SCANS_DIR exists on disk:    {os.path.exists(SCANS_DIR)}")
    print(f"ENGINE_DIR exists on disk:   {os.path.exists(ENGINE_DIR)}")