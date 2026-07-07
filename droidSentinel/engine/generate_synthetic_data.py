# generate_synthetic_data.py
# Generates synthetic data samples based on REAL scan patterns only
# (never samples from previously-generated synthetic rows, to avoid
# synthetic-data drift across repeated runs).

import pandas as pd
import numpy as np
import os

DATASET_PATH = r"D:\DroidSentinel\engine\dataset.csv"
OUTPUT_PATH  = r"D:\DroidSentinel\engine\dataset.csv"  # overwrites with augmented data

np.random.seed(42)

# ─────────────────────────────────────────────
# HOW MANY *ADDITIONAL* SYNTHETIC SAMPLES TO ADD
# (split evenly between normal/anomaly; if odd,
#  the extra one goes to anomaly)
#
# This is now asked at runtime instead of hardcoded —
# just run the script and type the number when prompted.
# ─────────────────────────────────────────────
def get_n_new_synthetic_total(default=20):
    raw = input(
        f"How many NEW synthetic samples do you want to add? "
        f"(press Enter for default = {default}): "
    ).strip()

    if raw == "":
        return default

    try:
        n = int(raw)
        if n <= 0:
            print(f"[⚠️] Must be a positive number — using default ({default}) instead.")
            return default
        return n
    except ValueError:
        print(f"[⚠️] Not a valid number — using default ({default}) instead.")
        return default


def load_data():
    df = pd.read_csv(DATASET_PATH)

    # Backward-compatible: if this is the very first run (no "source"
    # column yet), treat every existing row as real.
    if "source" not in df.columns:
        df["source"] = "real"

    real_df = df[df["source"] == "real"]
    synthetic_df = df[df["source"] == "synthetic"]

    print(f"[📊] Loaded {len(df)} total samples")
    print(f"   Real:      {len(real_df)} "
          f"(normal: {len(real_df[real_df['label']=='normal'])}, "
          f"anomaly: {len(real_df[real_df['label']=='anomaly'])})")
    print(f"   Synthetic: {len(synthetic_df)} (from previous runs)")

    return df, real_df


def next_synthetic_index(df, prefix):
    """
    Find the next available index for synthetic_normal_NN / synthetic_anomaly_NN
    so re-running this script doesn't overwrite/duplicate previous synthetic scan names.
    """
    existing = df[df["scan"].str.startswith(prefix, na=False)]["scan"]
    max_idx = 0
    for name in existing:
        try:
            idx = int(name.replace(prefix, ""))
            max_idx = max(max_idx, idx)
        except ValueError:
            pass
    return max_idx + 1


def generate_normal_samples(real_normal, n, start_idx):
    samples = []
    for i in range(n):
        base = real_normal.sample(1).iloc[0]
        idx = start_idx + i
        sample = {
            "scan": f"synthetic_normal_{idx:02d}",
            "label": "normal",
            "source": "synthetic",
            "usagestats_size": int(base["usagestats_size"] * np.random.uniform(0.85, 1.15)),
            "dropbox_count": int(np.random.randint(70, 100)),
            "dropbox_size": int(np.random.randint(100000, 250000)),
            "notification_entries": 0,
            "notification_size": int(base["notification_size"] * np.random.uniform(0.9, 1.1)),
            "packages_size": int(base["packages_size"] * np.random.uniform(0.98, 1.02)),
            "netstats_size": int(np.random.randint(3000, 8000)),
            "ishredder_pdf": 0,
            "shreddit_count": 0,
            "secure_eraser_ts": 0,
            "factory_reset": 0,
            "unknown_wiping_app_detected": 0,
        }
        samples.append(sample)

    print(f"[✅] Generated {n} new synthetic normal samples "
          f"(indices {start_idx:02d}-{start_idx+n-1:02d})")
    return samples


def generate_anomaly_samples(real_anomaly, n, start_idx):
    samples = []

    scenarios = [
        "ishredder_only",
        "shreddit_only",
        "secure_eraser_only",
        "ishredder_shreddit",
        "ishredder_secure_eraser",
        "shreddit_secure_eraser",
        "all_three",
        "ghost_trace_only",
    ]

    for i in range(n):
        base = real_anomaly.sample(1).iloc[0]
        idx = start_idx + i
        scenario = scenarios[i % len(scenarios)]

        sample = {
            "scan": f"synthetic_anomaly_{idx:02d}",
            "label": "anomaly",
            "source": "synthetic",
            "usagestats_size": int(base["usagestats_size"] * np.random.uniform(0.9, 1.2)),
            "dropbox_count": int(np.random.randint(15, 65)),
            "dropbox_size": int(np.random.randint(20000, 90000)),
            "notification_entries": int(np.random.randint(4, 30)),
            "notification_size": int(base["notification_size"] * np.random.uniform(1.0, 1.5)),
            "packages_size": int(base["packages_size"] * np.random.uniform(0.98, 1.02)),
            "netstats_size": int(np.random.randint(3000, 8000)),
            "factory_reset": 0,
            "unknown_wiping_app_detected": 0,
        }

        if scenario == "ishredder_only":
            sample["ishredder_pdf"] = 1
            sample["shreddit_count"] = 0
            sample["secure_eraser_ts"] = 0

        elif scenario == "shreddit_only":
            sample["ishredder_pdf"] = 0
            sample["shreddit_count"] = int(np.random.randint(1, 4))
            sample["secure_eraser_ts"] = 0

        elif scenario == "secure_eraser_only":
            sample["ishredder_pdf"] = 0
            sample["shreddit_count"] = 0
            sample["secure_eraser_ts"] = int(np.random.randint(1781000000000, 1782200000000, dtype=np.int64))

        elif scenario == "ishredder_shreddit":
            sample["ishredder_pdf"] = 1
            sample["shreddit_count"] = int(np.random.randint(1, 3))
            sample["secure_eraser_ts"] = 0

        elif scenario == "ishredder_secure_eraser":
            sample["ishredder_pdf"] = 1
            sample["shreddit_count"] = 0
            sample["secure_eraser_ts"] = int(np.random.randint(1781000000000, 1782200000000, dtype=np.int64))

        elif scenario == "shreddit_secure_eraser":
            sample["ishredder_pdf"] = 0
            sample["shreddit_count"] = int(np.random.randint(1, 3))
            sample["secure_eraser_ts"] = int(np.random.randint(1781000000000, 1782200000000, dtype=np.int64))

        elif scenario == "all_three":
            sample["ishredder_pdf"] = 1
            sample["shreddit_count"] = int(np.random.randint(1, 4))
            sample["secure_eraser_ts"] = int(np.random.randint(1781000000000, 1782200000000, dtype=np.int64))

        elif scenario == "ghost_trace_only":
            sample["ishredder_pdf"] = 0
            sample["shreddit_count"] = 0
            sample["secure_eraser_ts"] = 0
            sample["notification_entries"] = int(np.random.randint(2, 10))

        samples.append(sample)

    print(f"[✅] Generated {n} new synthetic anomaly samples "
          f"(indices {start_idx:02d}-{start_idx+n-1:02d})")
    return samples


def build_augmented_dataset():
    print("\n" + "="*55)
    print("  DroidSentinel — Synthetic Data Generator")
    print("  Data Augmentation via Statistical Variation")
    print("  (always samples from REAL rows only — no drift)")
    print("="*55)

    df, real_df = load_data()
    real_normal  = real_df[real_df["label"] == "normal"]
    real_anomaly = real_df[real_df["label"] == "anomaly"]

    n_new_total = get_n_new_synthetic_total()
    n_new_normal  = n_new_total // 2
    n_new_anomaly = n_new_total - n_new_normal
    print(f"[INFO] Adding {n_new_total} new synthetic samples "
          f"({n_new_normal} normal + {n_new_anomaly} anomaly)")

    normal_start_idx  = next_synthetic_index(df, "synthetic_normal_")
    anomaly_start_idx = next_synthetic_index(df, "synthetic_anomaly_")

    synthetic_normal  = generate_normal_samples(real_normal,  n_new_normal,  normal_start_idx)
    synthetic_anomaly = generate_anomaly_samples(real_anomaly, n_new_anomaly, anomaly_start_idx)

    synthetic_df = pd.DataFrame(synthetic_normal + synthetic_anomaly)
    augmented_df = pd.concat([df, synthetic_df], ignore_index=True)

    augmented_df.to_csv(OUTPUT_PATH, index=False)

    real_total      = len(augmented_df[augmented_df["source"] == "real"])
    synthetic_total = len(augmented_df[augmented_df["source"] == "synthetic"])

    print(f"\n[✅] Augmented dataset saved: {OUTPUT_PATH}")
    print(f"[✅] Total samples:      {len(augmented_df)}")
    print(f"[✅] Real samples:       {real_total} (unchanged)")
    print(f"[✅] Synthetic samples:  {synthetic_total} (was {synthetic_total - len(synthetic_df)}, "
          f"added {len(synthetic_df)} more)")
    print(f"[✅] Normal total:       {len(augmented_df[augmented_df['label'] == 'normal'])}")
    print(f"[✅] Anomaly total:      {len(augmented_df[augmented_df['label'] == 'anomaly'])}")

    print("\n" + "="*55)
    print("  New Synthetic Normal Sample Preview:")
    print("="*55)
    for s in synthetic_normal[:3]:
        print(f"   {s['scan']}: dropbox={s['dropbox_count']}, "
              f"notif={s['notification_entries']}, "
              f"ishredder={s['ishredder_pdf']}, "
              f"shreddit={s['shreddit_count']}")

    print("\n" + "="*55)
    print("  New Synthetic Anomaly Sample Preview:")
    print("="*55)
    for s in synthetic_anomaly[:3]:
        print(f"   {s['scan']}: dropbox={s['dropbox_count']}, "
              f"notif={s['notification_entries']}, "
              f"ishredder={s['ishredder_pdf']}, "
              f"shreddit={s['shreddit_count']}, "
              f"se_ts={s['secure_eraser_ts']}")

    print("="*55)
    return augmented_df


if __name__ == "__main__":
    build_augmented_dataset()