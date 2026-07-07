import os
import json
import sqlite3
import xml.etree.ElementTree as ET
import csv

# ─────────────────────────────────────────────
# SCAN FOLDERS AND THEIR LABELS
# ─────────────────────────────────────────────
SCANS = [
    # ── NORMAL SAMPLES ──
    {
        "folder": r"D:\DroidSentinel\scans\baseline_scan",
        "label": "normal"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260615_145928",
        "label": "normal"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260615_151217",
        "label": "normal"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260618_102522",
        "label": "normal"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260618_102956",
        "label": "normal"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260618_103609",
        "label": "normal"
    },

    # ── ANOMALY SAMPLES ──
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260615_152150",
        "label": "anomaly"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260617_151004",
        "label": "anomaly"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260617_151530",
        "label": "anomaly"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260618_104018",
        "label": "anomaly"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260618_104208",
        "label": "anomaly"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260618_104523",
        "label": "anomaly"
    },

    # ── NEW NORMAL SAMPLES ──
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260622_104830",
        "label": "anomaly"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260622_114030",
        "label": "anomaly"
    },

# ── NEW ANOMALY SAMPLES ──
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260622_105235",
        "label": "anomaly"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260622_105433",
        "label": "anomaly"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260622_105814",
        "label": "anomaly"
    },
    {
        "folder": r"D:\DroidSentinel\scans\scan_20260622_110305",
        "label": "anomaly"
    },

    {
        "folder": r"D:\DroidSentinel\scans\scan_20260622_155941",
        "label": "anomaly"
    },
    
]
OUTPUT_CSV = r"D:\DroidSentinel\engine\dataset.csv"


def get_folder_size(folder):
    """Get total size of all files in a folder."""
    total = 0
    if os.path.exists(folder):
        for root, dirs, files in os.walk(folder):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
    return total


def get_file_count(folder):
    """Count files in a folder."""
    count = 0
    if os.path.exists(folder):
        for root, dirs, files in os.walk(folder):
            count += len(files)
    return count


def get_notification_entries(scan_folder):
    """Count wiping app entries in notification_log.db."""
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
    """Check if iShredder erasure PDF exists."""
    reports_folder = os.path.join(
        scan_folder, "app_data", "ishredder",
        "files_reports", "reports"
    )
    if not os.path.exists(reports_folder):
        return 0
    pdfs = [f for f in os.listdir(reports_folder) if f.endswith(".pdf")]
    return 1 if pdfs else 0


def get_shreddit_count(scan_folder):
    """Get Shreddit job counter value."""
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
    """Get Secure Eraser last background timestamp."""
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
    """Check if factory reset was detected."""
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
    """
    Detect any unknown wiping app by behavioral signature.
    Returns 1 if R11 fired (unknown wiping app found), else 0.
    Reads from analysis_results.json of the scan.
    """
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
    """Extract all numerical features from a scan folder."""
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
        "unknown_wiping_app_detected": get_unknown_wiping_app(scan_folder),   # ← R11
    }

    return features


def build_dataset():
    """Build dataset CSV from all scan folders."""
    print("\n" + "="*50)
    print("  DroidSentinel — Dataset Builder")
    print("="*50)

    rows = []

    for scan in SCANS:
        folder = scan["folder"]
        label = scan["label"]

        if not os.path.exists(folder):
            print(f"[⚠️] Folder not found: {folder}")
            continue

        print(f"\n[🔍] Processing: {os.path.basename(folder)} ({label})")

        features = extract_features(folder)
        row = {"scan": os.path.basename(folder), "label": label}
        row.update(features)
        rows.append(row)

        print(f"   usagestats_size:      {features['usagestats_size']:,}")
        print(f"   dropbox_count:        {features['dropbox_count']}")
        print(f"   notification_entries: {features['notification_entries']}")
        print(f"   packages_size:        {features['packages_size']:,}")
        print(f"   ishredder_pdf:        {features['ishredder_pdf']}")
        print(f"   shreddit_count:       {features['shreddit_count']}")
        print(f"   secure_eraser_ts:     {features['secure_eraser_ts']}")
        print(f"   factory_reset:        {features['factory_reset']}")
        print(f"   unknown_wiping_app:   {features['unknown_wiping_app_detected']}")  # ← R11

    # Write CSV
    if rows:
        fieldnames = list(rows[0].keys())
        with open(OUTPUT_CSV, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"\n[✅] Dataset saved: {OUTPUT_CSV}")
        print(f"[✅] Total samples: {len(rows)}")
        print(f"[✅] Normal:  {sum(1 for r in rows if r['label'] == 'normal')}")
        print(f"[✅] Anomaly: {sum(1 for r in rows if r['label'] == 'anomaly')}")
    else:
        print("[❌] No data collected")

    print("="*50)


if __name__ == "__main__":
    build_dataset()