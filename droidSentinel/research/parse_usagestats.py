import os

# Known wiping app package names
WIPING_APPS = [
    "com.projectstar.ishredder.android.standard",
    "com.palmtronix.shreddit.v1",
    "com.aiuspaktyn.secureeraser"
]

def parse_usagestats(folder):
    findings = []
    
    for root, dirs, files in os.walk(folder):
        for filename in files:
            filepath = os.path.join(root, filename)
            
            try:
                with open(filepath, 'rb') as f:
                    data = f.read()
                
                # Extract readable strings
                strings_found = []
                current = ""
                for byte in data:
                    if 32 <= byte <= 126:
                        current += chr(byte)
                    else:
                        if len(current) >= 5:
                            strings_found.append(current)
                        current = ""
                
                # Check for wiping apps
                for app in WIPING_APPS:
                    for s in strings_found:
                        if app in s:
                            findings.append({
                                "file": filename,
                                "app_found": app,
                                "evidence": s.strip()
                            })
                            break
                            
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    
    return findings

# Test on baseline
print("=== SCANNING BASELINE USAGESTATS ===")
baseline = r"D:\DroidSentinel\artifacts\baseline\usagestats"
results = parse_usagestats(baseline)

if results:
    for r in results:
        print(f"✅ FOUND: {r['app_found']} in file {r['file']}")
else:
    print("No wiping apps found in baseline")

print("\n=== SCANNING AFTER WIPE USAGESTATS ===")
after_wipe = r"D:\DroidSentinel\artifacts\after_wipe\usagestats"
results = parse_usagestats(after_wipe)

if results:
    for r in results:
        print(f"✅ FOUND: {r['app_found']} in file {r['file']}")
else:
    print("No wiping apps found in after_wipe")

print("\n=== SCANNING AFTER WIPE SHREDDIT ===")
shreddit = r"D:\DroidSentinel\artifacts\after_wipe_shreddit\usagestats"
results = parse_usagestats(shreddit)
if results:
    for r in results:
        print(f"✅ FOUND: {r['app_found']} in file {r['file']}")
else:
    print("No wiping apps found")

print("\n=== SCANNING AFTER WIPE SECURE ERASER ===")
secureeraser = r"D:\DroidSentinel\artifacts\after_wipe_secureeraser\usagestats"
results = parse_usagestats(secureeraser)
if results:
    for r in results:
        print(f"✅ FOUND: {r['app_found']} in file {r['file']}")
else:
    print("No wiping apps found")

print("\n=== SCANNING AFTER CLEAR DATA USAGESTATS ===")
after_clear = r"D:\DroidSentinel\artifacts\after_clear_data\usagestats_after"
results = parse_usagestats(after_clear)
if results:
    for r in results:
        print(f"✅ FOUND: {r['app_found']} in file {r['file']}")
else:
    print("No wiping apps found after clear data")

print("\n=== SCANNING AFTER FACTORY RESET USAGESTATS ===")
after_reset = r"D:\DroidSentinel\artifacts\after_reset\usagestats_after"
results = parse_usagestats(after_reset)
if results:
    for r in results:
        print(f"✅ FOUND: {r['app_found']} in file {r['file']}")
else:
    print("No wiping apps found after factory reset")