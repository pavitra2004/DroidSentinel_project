import sys
sys.path.append(r"D:\DroidSentinel\engine")
from rule_engine import analyze

BASELINE = r"D:\DroidSentinel\scans\baseline_scan"

SCANS = [
    r"D:\DroidSentinel\scans\baseline_scan",
    r"D:\DroidSentinel\scans\scan_20260615_145928",
    r"D:\DroidSentinel\scans\scan_20260615_151217",
    r"D:\DroidSentinel\scans\scan_20260618_102522",
    r"D:\DroidSentinel\scans\scan_20260618_102956",
    r"D:\DroidSentinel\scans\scan_20260618_103609",
    r"D:\DroidSentinel\scans\scan_20260615_152150",
    r"D:\DroidSentinel\scans\scan_20260617_151004",
    r"D:\DroidSentinel\scans\scan_20260617_151530",
    r"D:\DroidSentinel\scans\scan_20260618_104018",
    r"D:\DroidSentinel\scans\scan_20260618_104208",
    r"D:\DroidSentinel\scans\scan_20260618_104523",
    r"D:\DroidSentinel\scans\scan_20260622_104830",
    r"D:\DroidSentinel\scans\scan_20260622_114030",
    r"D:\DroidSentinel\scans\scan_20260622_105235",
    r"D:\DroidSentinel\scans\scan_20260622_105433",
    r"D:\DroidSentinel\scans\scan_20260622_105814",
    r"D:\DroidSentinel\scans\scan_20260622_110305",
    r"D:\DroidSentinel\scans\scan_20260622_155941",
   
]

print("\n" + "="*50)
print("Generating analysis_results.json for all scans")
print("="*50)

for scan in SCANS:
    import os
    print(f"\n[🔍] Processing: {os.path.basename(scan)}")
    try:
        analyze(BASELINE, scan)
        print(f"[✅] Done")
    except Exception as e:
        print(f"[❌] Error: {e}")

print("\n[✅] All scans processed")