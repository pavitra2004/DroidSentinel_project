import subprocess
import os
import json
from datetime import datetime
import sys

# ── Portable path import ──────────────────────────────────────────────────────
# Import BASE_SCAN_FOLDER from config.py instead of hardcoding it,
# so this script works wherever the project folder is placed.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SCANS_DIR as BASE_SCAN_FOLDER
# ─────────────────────────────────────────────────────────────────────────────

KNOWN_WIPING_APPS = [
    "com.projectstar.ishredder.android.standard",
    "com.palmtronix.shreddit.v1",
    "com.aiuspaktyn.secureeraser"
]


def run_adb(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", "Timeout"
    except Exception as e:
        return "", str(e)


def check_adb_connection():
    print("\n[DroidSentinel] Checking ADB connection...")
    stdout, stderr = run_adb("adb devices")
    if "emulator" in stdout or "device" in stdout:
        lines = stdout.strip().split("\n")
        for line in lines[1:]:
            if "device" in line and "offline" not in line:
                device_id = line.split()[0]
                print(f"[✅] Device connected: {device_id}")
                return True, device_id
    print("[❌] No device connected. Please start your emulator.")
    return False, None


def enable_root():
    print("\n[DroidSentinel] Enabling root access...")
    stdout, stderr = run_adb("adb root")
    if "already running as root" in stdout or "restarting" in stdout:
        print("[✅] Root access enabled")
        return True
    print(f"[⚠️] Root issue: {stdout} {stderr}")
    return False


def get_device_info():
    print("\n[DroidSentinel] Collecting device information...")
    model, _ = run_adb("adb shell getprop ro.product.model")
    android_version, _ = run_adb("adb shell getprop ro.build.version.release")
    api_level, _ = run_adb("adb shell getprop ro.build.version.sdk")
    serial, _ = run_adb("adb shell getprop ro.serialno")
    build_id, _ = run_adb("adb shell getprop ro.build.id")
    info = {
        "model": model or "Unknown",
        "android_version": android_version or "Unknown",
        "api_level": api_level or "Unknown",
        "serial": serial or "Unknown",
        "build_id": build_id or "Unknown",
        "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    print(f"[✅] Device: {info['model']}")
    print(f"[✅] Android: {info['android_version']} (API {info['api_level']})")
    print(f"[✅] Serial: {info['serial']}")
    return info


def create_scan_folder():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_folder = os.path.join(BASE_SCAN_FOLDER, f"scan_{timestamp}")
    folders = [
        scan_folder,
        os.path.join(scan_folder, "system"),
        os.path.join(scan_folder, "app_data"),
        os.path.join(scan_folder, "app_data", "ishredder"),
        os.path.join(scan_folder, "app_data", "shreddit"),
        os.path.join(scan_folder, "app_data", "secureeraser"),
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
    print(f"\n[✅] Scan folder created: {scan_folder}")
    return scan_folder


def pull_artifact(source, destination, label, step, total):
    print(f"\n[{step}/{total}] Pulling {label}...")
    stdout, stderr = run_adb(f'adb pull "{source}" "{destination}"')
    if "error" in stderr.lower() or "failed" in stderr.lower():
        print(f"[❌] Failed: {stderr}")
        return False, 0
    total_size = 0
    if os.path.isdir(destination):
        for root, dirs, files in os.walk(destination):
            for f in files:
                total_size += os.path.getsize(os.path.join(root, f))
    elif os.path.isfile(destination):
        total_size = os.path.getsize(destination)
    print(f"[✅] Done — {total_size:,} bytes pulled")
    return True, total_size


def pull_system_artifacts(scan_folder):
    print("\n" + "="*50)
    print("PHASE 1 — SYSTEM ARTIFACTS")
    print("="*50)
    system_folder = os.path.join(scan_folder, "system")
    results = {}
    total_steps = 7

    success, size = pull_artifact("/data/system/packages.xml", os.path.join(system_folder, "packages.xml"), "packages.xml (App Registry)", 1, total_steps)
    results["packages_xml"] = {"success": success, "size": size}

    success, size = pull_artifact("/data/system/packages.list", os.path.join(system_folder, "packages.list"), "packages.list (Current Apps)", 2, total_steps)
    results["packages_list"] = {"success": success, "size": size}

    success, size = pull_artifact("/data/system/usagestats/", os.path.join(system_folder, "usagestats"), "usagestats/ (App Usage History)", 3, total_steps)
    results["usagestats"] = {"success": success, "size": size}

    success, size = pull_artifact("/data/system/dropbox/", os.path.join(system_folder, "dropbox"), "dropbox/ (System Event Logs)", 4, total_steps)
    results["dropbox"] = {"success": success, "size": size}

    success, size = pull_artifact("/data/system/notification_log.db", os.path.join(system_folder, "notification_log.db"), "notification_log.db (Notification History)", 5, total_steps)
    results["notification_log"] = {"success": success, "size": size}

    success, size = pull_artifact("/data/system/netstats/", os.path.join(system_folder, "netstats"), "netstats/ (Network Usage)", 6, total_steps)
    results["netstats"] = {"success": success, "size": size}

    print(f"\n[7/{total_steps}] Pulling runtime-permissions.xml (App Permissions)...")
    stdout, stderr = run_adb(f'adb pull "/data/system/users/0/runtime-permissions.xml" "{os.path.join(system_folder, "runtime-permissions.xml")}"')
    if os.path.exists(os.path.join(system_folder, "runtime-permissions.xml")):
        size = os.path.getsize(os.path.join(system_folder, "runtime-permissions.xml"))
        print(f"[✅] Done — {size:,} bytes pulled")
        results["runtime_permissions"] = {"success": True, "size": size}
    else:
        print(f"[ℹ️] runtime-permissions.xml not found")
        results["runtime_permissions"] = {"success": False, "size": 0}

    return results


def pull_app_data(scan_folder):
    print("\n" + "="*50)
    print("PHASE 2 — WIPING APP INTERNAL DATA")
    print("="*50)
    results = {}
    app_configs = [
        {"name": "iShredder", "package": "com.projectstar.ishredder.android.standard", "folder": os.path.join(scan_folder, "app_data", "ishredder"), "paths": ["shared_prefs", "files/reports"], "use_cat": False},
        {"name": "Shreddit", "package": "com.palmtronix.shreddit.v1", "folder": os.path.join(scan_folder, "app_data", "shreddit"), "paths": ["shared_prefs", "no_backup"], "use_cat": False},
        {"name": "Secure Eraser", "package": "com.aiuspaktyn.secureeraser", "folder": os.path.join(scan_folder, "app_data", "secureeraser"), "paths": ["shared_prefs"], "use_cat": True}
    ]
    for app in app_configs:
        print(f"\n[🔍] Checking {app['name']} ({app['package']})...")
        stdout, _ = run_adb("adb shell pm list packages")
        if app['package'] not in stdout:
            print(f"[⚠️] {app['name']} not installed — skipping")
            results[app['name']] = {"installed": False}
            continue
        print(f"[✅] {app['name']} is installed")
        results[app['name']] = {"installed": True, "paths": {}}
        for path in app['paths']:
            source = f"/data/data/{app['package']}/{path}/"
            dest = os.path.join(app['folder'], path.replace("/", "_"))
            os.makedirs(dest, exist_ok=True)
            if app['use_cat']:
                list_stdout, _ = run_adb(f"adb shell ls {source}")
                if not list_stdout or "No such file" in list_stdout:
                    print(f"[ℹ️] {path} — not created yet (app not run)")
                    results[app['name']]["paths"][path] = {"success": False, "reason": "App not run yet — no data created"}
                    continue
                files = list_stdout.strip().split("\n")
                total_size = 0
                files_saved = 0
                for filename in files:
                    filename = filename.strip()
                    if not filename:
                        continue
                    safe_filename = filename.replace(":", "_")
                    dest_file = os.path.join(dest, safe_filename)
                    content, err = run_adb(f'adb shell cat "{source}{filename}"')
                    if content and "No such file" not in err:
                        with open(dest_file, 'w', encoding='utf-8', errors='ignore') as f:
                            f.write(content)
                        size = os.path.getsize(dest_file)
                        total_size += size
                        files_saved += 1
                        print(f"[✅] Saved {safe_filename} — {size} bytes")
                    else:
                        print(f"[⚠️] Could not read {filename}")
                if files_saved > 0:
                    results[app['name']]["paths"][path] = {"success": True, "size": total_size}
                else:
                    results[app['name']]["paths"][path] = {"success": False, "reason": "No files could be read"}
            else:
                stdout, stderr = run_adb(f'adb pull "{source}" "{dest}"')
                if "No such file" in stderr or "failed to stat" in stderr:
                    print(f"[ℹ️] {path} — not created yet (app not run)")
                    results[app['name']]["paths"][path] = {"success": False, "reason": "App not run yet — no data created"}
                elif "error" not in stderr.lower():
                    total_size = 0
                    for root, dirs, files in os.walk(dest):
                        for f in files:
                            total_size += os.path.getsize(os.path.join(root, f))
                    print(f"[✅] Pulled {path} — {total_size:,} bytes")
                    results[app['name']]["paths"][path] = {"success": True, "size": total_size}
                else:
                    print(f"[⚠️] Could not pull {path} — {stderr}")
                    results[app['name']]["paths"][path] = {"success": False}
    return results


def check_factory_reset(scan_folder):
    print("\n" + "="*50)
    print("PHASE 3 — FACTORY RESET CHECK")
    print("="*50)
    stdout, _ = run_adb("adb shell ls /data/system/")
    if "factory_reset" in stdout:
        timestamp_out, _ = run_adb("adb shell stat /data/system/factory_reset")
        print(f"[🚨] FACTORY RESET FILE DETECTED!")
        print(f"[📅] {timestamp_out}")
        return True, timestamp_out
    else:
        print(f"[✅] No factory reset file found — device not reset")
        return False, None


def save_scan_summary(scan_folder, device_info, system_results, app_results, reset_detected):
    summary = {
        "device_info": device_info,
        "system_artifacts": system_results,
        "app_data": app_results,
        "factory_reset_detected": reset_detected,
        "scan_folder": scan_folder
    }
    summary_path = os.path.join(scan_folder, "scan_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=4)
    print(f"\n[✅] Scan summary saved: {summary_path}")
    return summary_path


def print_collection_summary(device_info, system_results, app_results, reset_detected, scan_folder):
    print("\n" + "="*50)
    print("COLLECTION COMPLETE — SUMMARY")
    print("="*50)
    print(f"\n📱 Device: {device_info['model']}")
    print(f"🤖 Android: {device_info['android_version']} (API {device_info['api_level']})")
    print(f"🕐 Scan Time: {device_info['scan_time']}")
    print("\n📁 SYSTEM ARTIFACTS:")
    for artifact, data in system_results.items():
        status = "✅" if data["success"] else "❌"
        size = f"{data['size']:,} bytes" if data["success"] else "Failed"
        print(f"   {status} {artifact}: {size}")
    print("\n📦 WIPING APP DATA:")
    for app_name, data in app_results.items():
        if not data.get("installed"):
            print(f"   ⚠️  {app_name}: Not installed")
        else:
            paths = data.get("paths", {})
            pulled = [p for p, v in paths.items() if v.get("success")]
            if pulled:
                print(f"   ✅ {app_name}: Installed — {len(pulled)} path(s) pulled")
            else:
                print(f"   ℹ️  {app_name}: Installed — no data yet (app not run)")
    print("\n🔄 FACTORY RESET:")
    if reset_detected:
        print("   🚨 FACTORY RESET DETECTED")
    else:
        print("   ✅ No factory reset detected")
    print(f"\n💾 Artifacts saved to: {scan_folder}")
    print("\n[DroidSentinel] Collection complete. Ready for rule engine analysis.")
    print("="*50)


def collect(target_folder=None):
    print("\n" + "="*50)
    print("  DroidSentinel — Artifact Collector v1.0")
    print("  Android Anti-Forensics Detection Framework")
    print("="*50)
    connected, device_id = check_adb_connection()
    if not connected:
        return None
    enable_root()
    device_info = get_device_info()
    scan_folder = target_folder or create_scan_folder()
    system_results = pull_system_artifacts(scan_folder)
    app_results = pull_app_data(scan_folder)
    reset_detected, reset_timestamp = check_factory_reset(scan_folder)
    save_scan_summary(scan_folder, device_info, system_results, app_results, reset_detected)
    print_collection_summary(device_info, system_results, app_results, reset_detected, scan_folder)
    return scan_folder


if __name__ == "__main__":
    collect()