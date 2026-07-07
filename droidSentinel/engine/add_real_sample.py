import os
import sys
import json
import sqlite3
import xml.etree.ElementTree as ET
import csv
import argparse

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
SCANS_ROOT = r"D:\DroidSentinel\scans"
DATASET_PATH = r"D:\DroidSentinel\engine\dataset.csv"

# ─────────────────────────────────────────────
# FEATURE EXTRACTION
# (identical logic to build_dataset.py's extract_features,
#  kept in sync so new real rows match existing ones exactly)
# ─────────────────────────────────────────────

def get_folder_size(folder):
    total = 0
    if os.path.exists(folder):
        for root, dirs, files in os.walk(folder):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
    return total


def get_file_count(folder):
    count = 0
    if os.path.exists(folder):
        for root, dirs, files in os.walk(folder):
            count += len(files)
    return count


def get_notification_entries(scan_folder):
    KNOWN_PKGS = [
        "com.projectstar.ishredder.android.standard",
        "com.palmtronix.shreddit.v1",
        "com.aiuspaktyn.secureeraser"
    ]
    db_path = os.path.join(scan_folder, "system", "notification_log.db")
    count = 0
    if not os.path.exists(db_path):
        return 0
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT pkg FROM log")
        rows = cursor.fetchall()
        conn.close()
        for (pkg,) in rows:
            if pkg and any(p in pkg for p in KNOWN_PKGS):
                count += 1
    except Exception:
        pass
    return count


def get_ishredder_pdf(scan_folder):
    reports_folder = os.path.join(
        scan_folder, "app_data", "ishredder",
        "files_reports", "reports"
    )
    if not os.path.exists(reports_folder):
        return 0
    pdfs = [f for f in os.listdir(reports_folder) if f.endswith(".pdf")]
    return 1 if pdfs else 0


def get_shreddit_count(scan_folder):
    prefs_folder = os.path.join(
        scan_folder, "app_data", "shreddit",
        "shared_prefs", "shared_prefs"
    )
    if not os.path.exists(prefs_folder):
        return 0
    for f in os.listdir(prefs_folder):
        if f.endswith(".xml"):
            try:
                tree = ET.parse(os.path.join(prefs_folder, f))
                root = tree.getroot()
                for elem in root.findall('int'):
                    if elem.get('name') == 'shredjob.count':
                        return int(elem.get('value', 0))
            except Exception:
                pass
    return 0


def get_secure_eraser_timestamps(scan_folder):
    admob_path = os.path.join(
        scan_folder, "app_data", "secureeraser",
        "shared_prefs", "admob.xml"
    )
    if not os.path.exists(admob_path):
        return 0
    try:
        tree = ET.parse(admob_path)
        root = tree.getroot()
        for elem in root.findall('long'):
            if elem.get('name') == 'app_last_background_time_ms':
                return int(elem.get('value', 0))
    except Exception:
        pass
    return 0


def get_factory_reset(scan_folder):
    summary_path = os.path.join(scan_folder, "scan_summary.json")
    if not os.path.exists(summary_path):
        return 0
    try:
        with open(summary_path, 'r') as f:
            summary = json.load(f)
        return 1 if summary.get("factory_reset_detected") else 0
    except Exception:
        return 0


def get_unknown_wiping_app(scan_folder):
    results_path = os.path.join(scan_folder, "analysis_results.json")
    if not os.path.exists(results_path):
        return 0
    try:
        with open(results_path, 'r') as f:
            results = json.load(f)
        for rule in results.get("rules", []):
            if rule.get("rule_id") == "R11":
                return 1 if rule.get("fired") else 0
    except Exception:
        pass
    return 0


def extract_features(scan_folder):
    """Extract all numerical features from a scan folder.
    Mirrors build_dataset.py's extract_features() exactly."""
    system_folder = os.path.join(scan_folder, "system")

    features = {
        "usagestats_size": get_folder_size(
            os.path.join(system_folder, "usagestats")
        ),
        "dropbox_count": get_file_count(
            os.path.join(system_folder, "dropbox")
        ),
        "dropbox_size": get_folder_size(
            os.path.join(system_folder, "dropbox")
        ),
        "notification_entries": get_notification_entries(scan_folder),
        "notification_size": os.path.getsize(
            os.path.join(system_folder, "notification_log.db")
        ) if os.path.exists(
            os.path.join(system_folder, "notification_log.db")
        ) else 0,
        "packages_size": os.path.getsize(
            os.path.join(system_folder, "packages.xml")
        ) if os.path.exists(
            os.path.join(system_folder, "packages.xml")
        ) else 0,
        "netstats_size": get_folder_size(
            os.path.join(system_folder, "netstats")
        ),
        "ishredder_pdf": get_ishredder_pdf(scan_folder),
        "shreddit_count": get_shreddit_count(scan_folder),
        "secure_eraser_ts": get_secure_eraser_timestamps(scan_folder),
        "factory_reset": get_factory_reset(scan_folder),
        "unknown_wiping_app_detected": get_unknown_wiping_app(scan_folder),
    }

    return features


# ─────────────────────────────────────────────
# APPEND LOGIC — never overwrites, only adds
# ─────────────────────────────────────────────

def load_existing_dataset():
    """Read dataset.csv as a list of dict rows, preserving column order."""
    if not os.path.exists(DATASET_PATH):
        return [], None

    with open(DATASET_PATH, 'r', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    return rows, fieldnames


def add_real_sample(scan_name, label):
    if label not in ("normal", "anomaly"):
        print(f"[❌] Invalid label '{label}' — must be exactly 'normal' or 'anomaly'")
        return False

    scan_folder = os.path.join(SCANS_ROOT, scan_name)
    if not os.path.exists(scan_folder):
        print(f"[❌] Scan folder not found: {scan_folder}")
        return False

    rows, fieldnames = load_existing_dataset()

    # Avoid duplicate scan names
    existing_names = {r["scan"] for r in rows}
    if scan_name in existing_names:
        print(f"[⚠️] '{scan_name}' already exists in dataset.csv — skipping "
              f"to avoid a duplicate row. Remove it first if you want to re-add.")
        return False

    print(f"[🔍] Extracting features from: {scan_name}")
    features = extract_features(scan_folder)

    new_row = {"scan": scan_name, "label": label, "source": "real"}
    new_row.update(features)

    # If dataset.csv didn't exist yet, build fieldnames from this row
    if fieldnames is None:
        fieldnames = list(new_row.keys())

    # Make sure every existing row also has a "source" value (older rows
    # created before the source column existed default to "real")
    for r in rows:
        if "source" not in r or not r["source"]:
            r["source"] = "real"

    rows.append(new_row)

    with open(DATASET_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    real_count = sum(1 for r in rows if r.get("source") == "real")
    synthetic_count = sum(1 for r in rows if r.get("source") == "synthetic")

    print(f"\n[✅] Added new REAL sample: {scan_name}  (label: {label})")
    print(f"   usagestats_size:      {features['usagestats_size']:,}")
    print(f"   dropbox_count:        {features['dropbox_count']}")
    print(f"   notification_entries: {features['notification_entries']}")
    print(f"   packages_size:        {features['packages_size']:,}")
    print(f"   ishredder_pdf:        {features['ishredder_pdf']}")
    print(f"   shreddit_count:       {features['shreddit_count']}")
    print(f"   secure_eraser_ts:     {features['secure_eraser_ts']}")
    print(f"   factory_reset:        {features['factory_reset']}")
    print(f"   unknown_wiping_app:   {features['unknown_wiping_app_detected']}")
    print(f"\n[✅] dataset.csv updated: {DATASET_PATH}")
    print(f"[✅] Total rows now: {len(rows)}  "
          f"(real: {real_count}, synthetic: {synthetic_count})")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Append a new REAL labeled sample to dataset.csv "
                    "without overwriting existing rows."
    )
    parser.add_argument(
        "--scan", required=False,
        help="Scan folder name under D:\\DroidSentinel\\scans\\ "
             "(e.g. scan_20260626_140000)"
    )
    parser.add_argument(
        "--label", required=False, choices=["normal", "anomaly"],
        help="True label for this scan: 'normal' or 'anomaly'"
    )
    args = parser.parse_args()

    scan_name = args.scan
    label = args.label

    # Interactive fallback if run without arguments
    if not scan_name:
        scan_name = input("Scan folder name (e.g. scan_20260626_140000): ").strip()
    if not label:
        label = input("Label ('normal' or 'anomaly'): ").strip().lower()

    print("\n" + "="*55)
    print("  DroidSentinel — Add Real Sample to Dataset")
    print("="*55)

    add_real_sample(scan_name, label)


if __name__ == "__main__":
    main()