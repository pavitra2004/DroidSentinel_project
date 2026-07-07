import os
import xml.etree.ElementTree as ET

baseline_xml = r'D:\DroidSentinel\scans\baseline_scan\system\packages.xml'
current_xml  = r'D:\DroidSentinel\scans\scan_20260622_161408\system\packages.xml'
runtime_xml  = r'D:\DroidSentinel\scans\scan_20260622_161408\system\runtime-permissions.xml'

WIPING_PERMISSIONS = [
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.MANAGE_EXTERNAL_STORAGE"
]
EXCLUDE_PERMISSIONS = [
    "android.permission.INTERNET",
    "android.permission.CAMERA",
    "android.permission.RECORD_AUDIO",
    "android.permission.SEND_SMS"
]
KNOWN_SAFE_PREFIXES = [
    "com.android.", "com.google.", "android.",
    "com.whatsapp", "com.projectstar.ishredder",
    "com.palmtronix.shreddit", "com.aiuspaktyn.secureeraser"
]

def get_packages(xml_path, runtime_path=None):
    packages = {}
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for pkg in root.findall('.//package'):
            name = pkg.get('name', '')
            if not name:
                continue
            perms = [p.get('name','') for p in pkg.findall('.//perms/item')]
            packages[name] = perms
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")

    if runtime_path and os.path.exists(runtime_path):
        try:
            tree = ET.parse(runtime_path)
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
        except Exception as e:
            print(f"Error parsing runtime perms: {e}")

    return packages

baseline = get_packages(baseline_xml)
current  = get_packages(current_xml, runtime_xml)

print(f"\n[1] Total packages in baseline: {len(baseline)}")
print(f"[2] Total packages in current:  {len(current)}")

# Check cbinnovations specifically
print("\n[3] cbinnovations permissions:")
for k, v in current.items():
    if 'cbinnovations' in k:
        print(f"    Package: {k}")
        print(f"    Perms: {v}")
        print(f"    In baseline: {k in baseline}")

# Check what suspicious apps R11 would find
print("\n[4] Suspicious apps found by R11:")
for pkg, perms in current.items():
    # Skip safe
    safe = any(pkg.startswith(p) for p in KNOWN_SAFE_PREFIXES)
    if safe:
        continue
    has_storage = any(p in perms for p in WIPING_PERMISSIONS)
    has_excluded = any(p in perms for p in EXCLUDE_PERMISSIONS)
    if has_storage and not has_excluded:
        new = pkg not in baseline
        print(f"    {pkg} — new={new} — perms={perms}")

print("\n[5] Done")