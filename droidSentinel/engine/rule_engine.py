import os
import json
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

# ─────────────────────────────────────────────
# KNOWN WIPING APP PACKAGE NAMES
# ─────────────────────────────────────────────
KNOWN_WIPING_APPS = {
    "com.projectstar.ishredder.android.standard": "iShredder",
    "com.palmtronix.shreddit.v1": "Shreddit",
    "com.aiuspaktyn.secureeraser": "Secure Eraser"
}

# ─────────────────────────────────────────────
# RULE WEIGHTS
# ─────────────────────────────────────────────
RULE_WEIGHTS = {
    "R01": 25,
    "R02": 30,
    "R03": 15,
    "R04": 20,
    "R05": 35,
    "R06": 25,
    "R07": 35,
    "R08": 35,
    "R09": 20,
    "R10": 20,
    "R11": 25,
}

MAX_SCORE = sum(RULE_WEIGHTS.values())


def extract_strings(filepath, min_length=5):
    strings = []
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        current = ""
        for byte in data:
            if 32 <= byte <= 126:
                current += chr(byte)
            else:
                if len(current) >= min_length:
                    strings.append(current)
                current = ""
    except Exception:
        pass
    return strings


def rule_R01_usagestats(baseline_folder, current_folder):
    result = {
        "rule_id": "R01",
        "rule_name": "Wiping App Usage Session Detected in usagestats",
        "artifact": "usagestats/",
        "fired": False,
        "confidence": "NONE",
        "weight": RULE_WEIGHTS["R01"],
        "score": 0,
        "evidence": []
    }

    baseline_path = os.path.join(baseline_folder, "system", "usagestats")
    current_path = os.path.join(current_folder, "system", "usagestats")

    if not os.path.exists(current_path):
        result["evidence"].append("usagestats folder not found")
        return result

    baseline_apps = set()
    if os.path.exists(baseline_path):
        for root, dirs, files in os.walk(baseline_path):
            for filename in files:
                filepath = os.path.join(root, filename)
                strings = extract_strings(filepath)
                for s in strings:
                    for pkg in KNOWN_WIPING_APPS:
                        if pkg in s:
                            baseline_apps.add(pkg)

    current_apps = set()
    current_files = {}
    for root, dirs, files in os.walk(current_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            strings = extract_strings(filepath)
            for s in strings:
                for pkg in KNOWN_WIPING_APPS:
                    if pkg in s:
                        current_apps.add(pkg)
                        if pkg not in current_files:
                            current_files[pkg] = filename

    new_apps = current_apps - baseline_apps

    if new_apps:
        result["fired"] = True
        result["confidence"] = "HIGH"
        result["score"] = RULE_WEIGHTS["R01"]
        for pkg in new_apps:
            app_name = KNOWN_WIPING_APPS[pkg]
            filename = current_files.get(pkg, "unknown")
            result["evidence"].append(
                f"{app_name} ({pkg}) usage recorded "
                f"in usagestats file {filename} — "
                f"not present in baseline"
            )
    else:
        result["evidence"].append(
            "No new wiping app usage detected in usagestats"
        )

    return result


def rule_R02_notification_log(baseline_folder, current_folder):
    result = {
        "rule_id": "R02",
        "rule_name": "Wiping App Ghost Trace in notification_log.db",
        "artifact": "notification_log.db",
        "fired": False,
        "confidence": "NONE",
        "weight": RULE_WEIGHTS["R02"],
        "score": 0,
        "evidence": []
    }

    baseline_db = os.path.join(
        baseline_folder, "system", "notification_log.db"
    )
    current_db = os.path.join(
        current_folder, "system", "notification_log.db"
    )

    if not os.path.exists(current_db):
        result["evidence"].append("notification_log.db not found")
        return result

    def get_wiping_app_notifications(db_path):
        found = {}
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT pkg, event_time_ms FROM log ORDER BY event_time_ms"
            )
            rows = cursor.fetchall()
            conn.close()
            for pkg, timestamp in rows:
                if pkg and any(
                    known in pkg for known in KNOWN_WIPING_APPS
                ):
                    if pkg not in found:
                        found[pkg] = []
                    found[pkg].append(timestamp)
        except Exception:
            pass
        return found

    baseline_entries = get_wiping_app_notifications(baseline_db) \
        if os.path.exists(baseline_db) else {}
    current_entries = get_wiping_app_notifications(current_db)

    new_entries = {}
    for pkg, timestamps in current_entries.items():
        baseline_timestamps = baseline_entries.get(pkg, [])
        new_timestamps = [
            t for t in timestamps if t not in baseline_timestamps
        ]
        if new_timestamps:
            new_entries[pkg] = new_timestamps

    if new_entries:
        result["fired"] = True
        result["confidence"] = "HIGH"
        result["score"] = RULE_WEIGHTS["R02"]
        for pkg, timestamps in new_entries.items():
            app_name = KNOWN_WIPING_APPS.get(pkg, pkg)
            for ts in timestamps[:3]:
                try:
                    readable = datetime.fromtimestamp(
                        ts / 1000
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    result["evidence"].append(
                        f"{app_name} notification recorded "
                        f"at {readable} — ghost trace confirmed"
                    )
                except Exception:
                    result["evidence"].append(
                        f"{app_name} notification found "
                        f"(timestamp: {ts})"
                    )
    else:
        result["evidence"].append(
            "No new wiping app notifications found"
        )

    return result


def rule_R03_dropbox(baseline_folder, current_folder):
    result = {
        "rule_id": "R03",
        "rule_name": "New System Log Entries in Dropbox",
        "artifact": "dropbox/",
        "fired": False,
        "confidence": "NONE",
        "weight": RULE_WEIGHTS["R03"],
        "score": 0,
        "evidence": []
    }

    baseline_path = os.path.join(baseline_folder, "system", "dropbox")
    current_path = os.path.join(current_folder, "system", "dropbox")

    if not os.path.exists(current_path):
        result["evidence"].append("dropbox folder not found")
        return result

    baseline_files = set()
    if os.path.exists(baseline_path):
        for root, dirs, files in os.walk(baseline_path):
            for f in files:
                baseline_files.add(f)

    current_files = set()
    for root, dirs, files in os.walk(current_path):
        for f in files:
            current_files.add(f)

    new_files = current_files - baseline_files
    new_count = len(new_files)

    if new_count > 0:
        result["fired"] = True
        result["score"] = RULE_WEIGHTS["R03"]

        wiping_refs = []
        for root, dirs, files in os.walk(current_path):
            for filename in files:
                if filename in new_files:
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r', errors='ignore') as f:
                            content = f.read()
                        for pkg, name in KNOWN_WIPING_APPS.items():
                            if pkg in content:
                                wiping_refs.append(
                                    f"{name} referenced in "
                                    f"dropbox/{filename}"
                                )
                    except Exception:
                        pass

        if wiping_refs:
            result["confidence"] = "HIGH"
            result["evidence"].extend(wiping_refs)
        else:
            result["confidence"] = "MEDIUM"

        result["evidence"].append(
            f"{new_count} new dropbox entries since baseline "
            f"(baseline: {len(baseline_files)}, "
            f"current: {len(current_files)})"
        )
    else:
        result["evidence"].append(
            f"No new dropbox entries since baseline "
            f"(both have {len(current_files)} files)"
        )

    return result


def rule_R04_netstats(baseline_folder, current_folder):
    result = {
        "rule_id": "R04",
        "rule_name": "Suspicious Network Activity Detected in netstats",
        "artifact": "netstats/",
        "fired": False,
        "confidence": "NONE",
        "weight": RULE_WEIGHTS["R04"],
        "score": 0,
        "evidence": []
    }

    def get_folder_size(folder):
        total = 0
        if os.path.exists(folder):
            for root, dirs, files in os.walk(folder):
                for f in files:
                    total += os.path.getsize(os.path.join(root, f))
        return total

    baseline_size = get_folder_size(
        os.path.join(baseline_folder, "system", "netstats")
    )
    current_size = get_folder_size(
        os.path.join(current_folder, "system", "netstats")
    )
    growth = current_size - baseline_size

    if growth > 500:
        result["fired"] = True
        result["confidence"] = "MEDIUM"
        result["score"] = RULE_WEIGHTS["R04"]
        result["evidence"].append(
            f"netstats grew by {growth:,} bytes since baseline "
            f"(baseline: {baseline_size:,}, current: {current_size:,}) "
            f"— indicates network activity from installed apps"
        )
    else:
        result["evidence"].append(
            f"No significant netstats growth "
            f"(baseline: {baseline_size:,}, current: {current_size:,})"
        )

    return result


def rule_R05_factory_reset(current_folder):
    result = {
        "rule_id": "R05",
        "rule_name": "Factory Reset Detected",
        "artifact": "/data/system/factory_reset",
        "fired": False,
        "confidence": "NONE",
        "weight": RULE_WEIGHTS["R05"],
        "score": 0,
        "evidence": []
    }

    summary_path = os.path.join(current_folder, "scan_summary.json")
    if not os.path.exists(summary_path):
        result["evidence"].append("scan_summary.json not found")
        return result

    with open(summary_path, 'r') as f:
        summary = json.load(f)

    if summary.get("factory_reset_detected"):
        result["fired"] = True
        result["confidence"] = "HIGH"
        result["score"] = RULE_WEIGHTS["R05"]
        result["evidence"].append(
            "factory_reset file found at /data/system/factory_reset "
            "— device was factory reset"
        )
    else:
        result["evidence"].append(
            "No factory_reset file found — "
            "device not reset via Android Settings"
        )

    return result


def rule_R06_packages_xml(baseline_folder, current_folder):
    result = {
        "rule_id": "R06",
        "rule_name": "packages.xml Size Reduction — App Removal Detected",
        "artifact": "packages.xml",
        "fired": False,
        "confidence": "NONE",
        "weight": RULE_WEIGHTS["R06"],
        "score": 0,
        "evidence": []
    }

    baseline_xml = os.path.join(baseline_folder, "system", "packages.xml")
    current_xml = os.path.join(current_folder, "system", "packages.xml")

    if not os.path.exists(current_xml):
        result["evidence"].append("packages.xml not found")
        return result

    baseline_size = os.path.getsize(baseline_xml) \
        if os.path.exists(baseline_xml) else 0
    current_size = os.path.getsize(current_xml)
    reduction = baseline_size - current_size

    if reduction > 5000:
        result["fired"] = True
        result["confidence"] = "HIGH"
        result["score"] = RULE_WEIGHTS["R06"]
        result["evidence"].append(
            f"packages.xml reduced by {reduction:,} bytes "
            f"(baseline: {baseline_size:,}, current: {current_size:,}) "
            f"— significant app removal detected"
        )
    elif reduction > 0:
        result["fired"] = True
        result["confidence"] = "MEDIUM"
        result["score"] = RULE_WEIGHTS["R06"] // 2
        result["evidence"].append(
            f"packages.xml reduced by {reduction:,} bytes — "
            f"minor app removal detected"
        )
    else:
        result["evidence"].append(
            f"No packages.xml reduction "
            f"(baseline: {baseline_size:,}, current: {current_size:,})"
        )

    return result


def rule_R07_ishredder_pdf(current_folder):
    result = {
        "rule_id": "R07",
        "rule_name": "iShredder Erasure PDF Report Found",
        "artifact": "iShredder/files/reports/",
        "fired": False,
        "confidence": "NONE",
        "weight": RULE_WEIGHTS["R07"],
        "score": 0,
        "evidence": []
    }

    reports_folder = os.path.join(
        current_folder, "app_data", "ishredder",
        "files_reports", "reports"
    )

    if not os.path.exists(reports_folder):
        result["evidence"].append(
            "iShredder reports folder not found — "
            "app not run or data cleared"
        )
        return result

    pdf_files = [
        f for f in os.listdir(reports_folder)
        if f.endswith(".pdf")
    ]

    if pdf_files:
        result["fired"] = True
        result["confidence"] = "HIGH"
        result["score"] = RULE_WEIGHTS["R07"]
        for pdf in pdf_files:
            pdf_path = os.path.join(reports_folder, pdf)
            size = os.path.getsize(pdf_path)
            result["evidence"].append(
                f"Erasure report found: {pdf} "
                f"({size:,} bytes) — contains wiped file list "
                f"and timestamps"
            )
    else:
        result["evidence"].append(
            "No erasure PDF found in iShredder reports folder"
        )

    return result


def rule_R08_ishredder_prefs(current_folder):
    result = {
        "rule_id": "R08",
        "rule_name": "iShredder Preferences Wiping Log Found",
        "artifact": "iShredder/shared_prefs/",
        "fired": False,
        "confidence": "NONE",
        "weight": RULE_WEIGHTS["R08"],
        "score": 0,
        "evidence": []
    }

    prefs_folder = os.path.join(
        current_folder, "app_data", "ishredder",
        "shared_prefs", "shared_prefs"
    )

    if not os.path.exists(prefs_folder):
        result["evidence"].append("iShredder shared_prefs not found")
        return result

    prefs_files = [
        f for f in os.listdir(prefs_folder)
        if f.endswith(".xml")
    ]

    for prefs_file in prefs_files:
        prefs_path = os.path.join(prefs_folder, prefs_file)
        try:
            tree = ET.parse(prefs_path)
            root = tree.getroot()
            for string_elem in root.findall('string'):
                if string_elem.get('name') == 'reports_v2':
                    report_json = json.loads(string_elem.text)
                    result["fired"] = True
                    result["confidence"] = "HIGH"
                    result["score"] = RULE_WEIGHTS["R08"]
                    start = report_json.get("startDate", "unknown")
                    items = report_json.get("totalItemsWritten", 0)
                    success = report_json.get("totalSuccess", False)
                    files_wiped = report_json.get("reportDetail", [])
                    result["evidence"].append(
                        f"Wiping log found in preferences — "
                        f"Start: {start}, Items wiped: {items}, "
                        f"Success: {success}"
                    )
                    for item in files_wiped:
                        result["evidence"].append(
                            f"Wiped file: {item.get('name', 'unknown')}"
                        )
        except Exception:
            pass

    if not result["fired"]:
        result["evidence"].append(
            "No wiping log found in iShredder preferences"
        )

    return result


def rule_R09_shreddit_counter(current_folder):
    result = {
        "rule_id": "R09",
        "rule_name": "Shreddit Wiping Job Counter Detected",
        "artifact": "Shreddit/shared_prefs/",
        "fired": False,
        "confidence": "NONE",
        "weight": RULE_WEIGHTS["R09"],
        "score": 0,
        "evidence": []
    }

    prefs_folder = os.path.join(
        current_folder, "app_data", "shreddit", "shared_prefs", "shared_prefs"
    )

    if not os.path.exists(prefs_folder):
        result["evidence"].append("Shreddit shared_prefs not found")
        return result

    prefs_files = [
        f for f in os.listdir(prefs_folder)
        if f.endswith(".xml")
    ]

    for prefs_file in prefs_files:
        prefs_path = os.path.join(prefs_folder, prefs_file)
        try:
            tree = ET.parse(prefs_path)
            root = tree.getroot()
            for int_elem in root.findall('int'):
                if int_elem.get('name') == 'shredjob.count':
                    count = int(int_elem.get('value', 0))
                    if count > 0:
                        result["fired"] = True
                        result["confidence"] = "MEDIUM"
                        result["score"] = RULE_WEIGHTS["R09"]
                        result["evidence"].append(
                            f"Shreddit job counter = {count} — "
                            f"{count} wiping operation(s) performed"
                        )
        except Exception:
            pass

    if not result["fired"]:
        result["evidence"].append(
            "Shreddit job counter is 0 or not found — "
            "no wiping performed"
        )

    return result


def rule_R10_secure_eraser_timestamps(baseline_folder, current_folder):
    result = {
        "rule_id": "R10",
        "rule_name": "Secure Eraser Usage Timestamps Detected",
        "artifact": "Secure Eraser/shared_prefs/admob.xml",
        "fired": False,
        "confidence": "NONE",
        "weight": RULE_WEIGHTS["R10"],
        "score": 0,
        "evidence": []
    }

    def get_admob_timestamps(folder):
        admob_path = os.path.join(
            folder, "app_data", "secureeraser",
            "shared_prefs", "admob.xml"
        )
        timestamps = {}
        if not os.path.exists(admob_path):
            return timestamps
        try:
            tree = ET.parse(admob_path)
            root = tree.getroot()
            for long_elem in root.findall('long'):
                name = long_elem.get('name')
                value = int(long_elem.get('value', 0))
                timestamps[name] = value
        except Exception:
            pass
        return timestamps

    baseline_ts = get_admob_timestamps(baseline_folder)
    current_ts = get_admob_timestamps(current_folder)

    if not current_ts:
        result["evidence"].append(
            "Secure Eraser admob.xml not found — app not run"
        )
        return result

    first_launch = current_ts.get("first_ad_req_time_ms", 0)
    baseline_first = baseline_ts.get("first_ad_req_time_ms", 0)
    last_bg = current_ts.get("app_last_background_time_ms", 0)
    baseline_last = baseline_ts.get("app_last_background_time_ms", 0)

    if first_launch > 0 and first_launch != baseline_first:
        result["fired"] = True
        result["confidence"] = "HIGH"
        result["score"] = RULE_WEIGHTS["R10"]
        try:
            readable = datetime.fromtimestamp(
                first_launch / 1000
            ).strftime("%Y-%m-%d %H:%M:%S")
            result["evidence"].append(
                f"Secure Eraser first launched at {readable}"
            )
        except Exception:
            result["evidence"].append(
                f"Secure Eraser first launched "
                f"(timestamp: {first_launch})"
            )

    if last_bg > baseline_last:
        result["fired"] = True
        result["confidence"] = "HIGH"
        result["score"] = RULE_WEIGHTS["R10"]
        try:
            readable = datetime.fromtimestamp(
                last_bg / 1000
            ).strftime("%Y-%m-%d %H:%M:%S")
            result["evidence"].append(
                f"Secure Eraser last used at {readable}"
            )
        except Exception:
            result["evidence"].append(
                f"Secure Eraser last used (timestamp: {last_bg})"
            )

    if not result["fired"]:
        result["evidence"].append(
            "No new Secure Eraser usage detected"
        )

    return result

def rule_R11_behavioral_detection(baseline_folder, current_folder):
    """
    Dynamically detect unknown wiping apps based on
    behavioral signatures — permissions + usage patterns.
    Works for ANY wiping app regardless of package name.
    """
    result = {
        "rule_id": "R11",
        "rule_name": "Unknown Wiping App Behavioral Detection",
        "artifact": "packages.xml + usagestats/",
        "fired": False,
        "confidence": "NONE",
        "weight": 25,
        "score": 0,
        "evidence": []
    }

    current_xml = os.path.join(current_folder, "system", "packages.xml")
    baseline_xml = os.path.join(baseline_folder, "system", "packages.xml")

    if not os.path.exists(current_xml):
        result["evidence"].append("packages.xml not found")
        return result

    # ── Permissions that suggest file wiping behavior ──
    WIPING_PERMISSIONS = [
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.MANAGE_EXTERNAL_STORAGE"
    ]

    # ── Permissions that rule OUT wiping apps ──
    # Legitimate wiping apps don't need these
    EXCLUDE_PERMISSIONS = [
        "android.permission.INTERNET",
        "android.permission.CAMERA",
        "android.permission.RECORD_AUDIO",
        "android.permission.SEND_SMS"
    ]

    # ── Known system and legitimate apps to ignore ──
    KNOWN_SAFE_PREFIXES = [
        "com.android.",
        "com.google.",
        "android.",
        "com.whatsapp",
        "com.projectstar.ishredder",  # already covered by R07/R08
        "com.palmtronix.shreddit",    # already covered by R09
        "com.aiuspaktyn.secureeraser" # already covered by R10
    ]

    def get_packages_from_xml(xml_path):
        """Extract package names and permissions from packages.xml
        and merge with runtime-permissions.xml."""
        packages = {}
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for pkg in root.findall('.//package'):
                name = pkg.get('name', '')
                if not name:
                    continue
                perms = []
                for perm in pkg.findall('.//perms/item'):
                    perms.append(perm.get('name', ''))
                packages[name] = perms
        except Exception:
            pass

        # ── Merge runtime permissions ──────────────────────────────
        # Runtime permissions (WRITE_EXTERNAL_STORAGE etc) are stored
        # separately in runtime-permissions.xml, not in packages.xml
        scan_folder = os.path.dirname(os.path.dirname(xml_path))
        runtime_perms_path = os.path.join(
            scan_folder, "system", "runtime-permissions.xml"
        )
        if os.path.exists(runtime_perms_path):
            try:
                tree = ET.parse(runtime_perms_path)
                root = tree.getroot()
                for pkg in root.findall('.//pkg'):
                    name = pkg.get('name', '')
                    if not name:
                        continue
                    if name not in packages:
                        packages[name] = []
                    for perm in pkg.findall('.//perm'):
                        perm_name = perm.get('name', '')
                        if perm_name and perm_name not in packages[name]:
                            packages[name].append(perm_name)
            except Exception:
                pass
        # ──────────────────────────────────────────────────────────

        return packages
    def is_safe_app(package_name):
        """Check if app is a known safe system app."""
        for prefix in KNOWN_SAFE_PREFIXES:
            if package_name.startswith(prefix):
                return True
        return False

    def has_wiping_signature(permissions):
        """Check if permission set matches wiping app behavior."""
        has_storage = any(
            p in permissions for p in WIPING_PERMISSIONS
        )
        has_excluded = any(
            p in permissions for p in EXCLUDE_PERMISSIONS
        )
        return has_storage and not has_excluded

    # Get baseline packages
    baseline_packages = get_packages_from_xml(baseline_xml) \
        if os.path.exists(baseline_xml) else {}

    # Get current packages
    current_packages = get_packages_from_xml(current_xml)

    # Find new apps not in baseline
    new_packages = {
        pkg: perms for pkg, perms in current_packages.items()
        if pkg not in baseline_packages
    }

    # Find suspicious apps among all current packages
    suspicious_apps = []
    for pkg, perms in current_packages.items():
        if is_safe_app(pkg):
            continue
        if has_wiping_signature(perms):
            suspicious_apps.append(pkg)

    # Check if suspicious apps appear in usagestats
    current_usagestats = os.path.join(
        current_folder, "system", "usagestats"
    )
    baseline_usagestats = os.path.join(
        baseline_folder, "system", "usagestats"
    )

    # Get apps already in baseline usagestats
    baseline_usage_apps = set()
    if os.path.exists(baseline_usagestats):
        for root, dirs, files in os.walk(baseline_usagestats):
            for filename in files:
                filepath = os.path.join(root, filename)
                strings = extract_strings(filepath)
                for s in strings:
                    for pkg in suspicious_apps:
                        if pkg in s:
                            baseline_usage_apps.add(pkg)

    # Check current usagestats for suspicious apps
    flagged_apps = []
    if os.path.exists(current_usagestats):
        for root, dirs, files in os.walk(current_usagestats):
            for filename in files:
                filepath = os.path.join(root, filename)
                strings = extract_strings(filepath)
                for s in strings:
                    for pkg in suspicious_apps:
                        if pkg in s and pkg not in baseline_usage_apps:
                            if pkg not in flagged_apps:
                                flagged_apps.append(pkg)

    # Stage 1 — Apps found in usagestats (confirmed active use)
    confirmed_apps = flagged_apps

    # Stage 2 — Apps new since baseline with wiping signature
    # OR new apps with wiping-related keywords in package name
    WIPING_KEYWORDS = [
        "shred", "erase", "wipe", "delete", "secure",
        "clean", "cleaner", "privacy", "vault", "eraser"
    ]

    new_suspicious_apps = []
    for pkg in current_packages:
        if pkg in baseline_packages:
            continue
        if pkg in confirmed_apps:
            continue
        # Skip known safe apps
        if any(pkg.startswith(p) for p in KNOWN_SAFE_PREFIXES):
            continue

        perms = current_packages[pkg]
        # Check wiping signature
        if has_wiping_signature(perms):
            new_suspicious_apps.append(pkg)
            continue

        # Check wiping keyword in package name as fallback
        pkg_lower = pkg.lower()
        if any(kw in pkg_lower for kw in WIPING_KEYWORDS):
            new_suspicious_apps.append(pkg)


    all_flagged = confirmed_apps + new_suspicious_apps

    if all_flagged:
        result["fired"] = True
        result["score"] = 25
        for pkg in confirmed_apps:
            result["confidence"] = "HIGH"
            result["evidence"].append(
                f"Unknown wiping app detected: {pkg} — "
                f"has storage permissions, no network permission, "
                f"and was actively used (found in usagestats)"
            )
        for pkg in new_suspicious_apps:
            result["confidence"] = "MEDIUM"
            result["evidence"].append(
                f"Unknown wiping app detected: {pkg} — "
                f"newly installed since baseline, "
                f"has storage permissions and no network permission "
                f"(behavioral signature matches file wiping)"
            )
    else:
        result["evidence"].append(
            "No unknown wiping apps detected"
        )

    return result

# ─────────────────────────────────────────────
# SAVE RESULTS TO JSON — NEW ADDITION
# ─────────────────────────────────────────────
def save_analysis_results(current_folder, rules,
                          total_score, max_score,
                          confidence_pct, overall_confidence,
                          verdict):
    """
    Save rule engine results to JSON file inside scan folder.
    Dashboard reads this file to display results.
    """
    results = {
        "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rules": rules,
        "total_score": total_score,
        "max_score": max_score,
        "confidence_pct": confidence_pct,
        "overall_confidence": overall_confidence,
        "verdict": verdict,
        "fired_count": len([r for r in rules if r["fired"]])
    }

    output_path = os.path.join(current_folder, "analysis_results.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=4)

    print(f"\n[✅] Analysis results saved: {output_path}")
    return output_path


def analyze(baseline_folder, current_folder):
    print("\n" + "="*50)
    print("  DroidSentinel — Rule Engine v1.0")
    print("  Running Detection Rules...")
    print("="*50)

    print(f"\n📁 Baseline: {baseline_folder}")
    print(f"📁 Current:  {current_folder}")

    print("\n[🔍] Running rules...")
    rules = [
        rule_R01_usagestats(baseline_folder, current_folder),
        rule_R02_notification_log(baseline_folder, current_folder),
        rule_R03_dropbox(baseline_folder, current_folder),
        rule_R04_netstats(baseline_folder, current_folder),
        rule_R05_factory_reset(current_folder),
        rule_R06_packages_xml(baseline_folder, current_folder),
        rule_R07_ishredder_pdf(current_folder),
        rule_R08_ishredder_prefs(current_folder),
        rule_R09_shreddit_counter(current_folder),
        rule_R10_secure_eraser_timestamps(baseline_folder, current_folder),
        rule_R11_behavioral_detection(baseline_folder, current_folder),
    ]

    fired_rules = [r for r in rules if r["fired"]]
    total_score = sum(r["score"] for r in rules)
    confidence_pct = round((total_score / MAX_SCORE) * 100, 1)

    if confidence_pct >= 70:
        overall_confidence = "HIGH"
        verdict = "🚨 ANTI-FORENSIC ACTIVITY STRONGLY DETECTED"
    elif confidence_pct >= 40:
        overall_confidence = "MEDIUM"
        verdict = "⚠️  SUSPICIOUS ACTIVITY DETECTED"
    elif confidence_pct >= 15:
        overall_confidence = "LOW"
        verdict = "🔎 MINOR INDICATORS DETECTED"
    else:
        overall_confidence = "NONE"
        verdict = "✅ NO ANTI-FORENSIC ACTIVITY DETECTED"

    print("\n" + "="*50)
    print("RULE ENGINE RESULTS")
    print("="*50)

    for rule in rules:
        status = "🔴 FIRED" if rule["fired"] else "⚪ CLEAR"
        print(f"\n{status} [{rule['rule_id']}] {rule['rule_name']}")
        print(f"         Artifact: {rule['artifact']}")
        print(f"         Confidence: {rule['confidence']} | "
              f"Score: {rule['score']}/{rule['weight']}")
        for ev in rule["evidence"]:
            print(f"         📌 {ev}")

    print("\n" + "="*50)
    print("OVERALL ANALYSIS")
    print("="*50)
    print(f"\n{verdict}")
    print(f"\n📊 Rules Fired:     {len(fired_rules)}/{len(rules)}")
    print(f"📊 Total Score:     {total_score}/{MAX_SCORE}")
    print(f"📊 Confidence:      {confidence_pct}% ({overall_confidence})")

    # ── NEW — Save results to JSON ──
    save_analysis_results(
        current_folder, rules,
        total_score, MAX_SCORE,
        confidence_pct, overall_confidence,
        verdict
    )

    return {
        "rules": rules,
        "fired_count": len(fired_rules),
        "total_score": total_score,
        "max_score": MAX_SCORE,
        "confidence_pct": confidence_pct,
        "overall_confidence": overall_confidence,
        "verdict": verdict,
        "baseline_folder": baseline_folder,
        "current_folder": current_folder
    }


if __name__ == "__main__":
    BASELINE = r"D:\DroidSentinel\scans\baseline_scan"
    CURRENT = r"D:\DroidSentinel\scans\scan_20260617_151530"

    analyze(BASELINE, CURRENT)