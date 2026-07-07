import os
import json

SCANS = [
    {"folder": r"D:\DroidSentinel\scans\baseline_scan", "label": "normal"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260615_145928", "label": "normal"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260615_151217", "label": "normal"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260618_102522", "label": "normal"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260618_102956", "label": "normal"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260618_103609", "label": "normal"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260615_152150", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260617_151004", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260617_151530", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260618_104018", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260618_104208", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260618_104523", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260622_104830", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260622_114030", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260622_105235", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260622_105433", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260622_105814", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260622_110305", "label": "anomaly"},
    {"folder": r"D:\DroidSentinel\scans\scan_20260622_155941", "label": "anomaly"},

]

RULES = ["R01","R02","R03","R04","R05","R06","R07","R08","R09","R10","R11"]

def validate():
    print("\n" + "="*65)
    print("  DroidSentinel — Validation Framework")
    print("="*65)

    # Collect per-rule firing data
    rule_data = {r: {"tp": 0, "fp": 0, "tn": 0, "fn": 0} for r in RULES}

    for scan in SCANS:
        results_path = os.path.join(
            scan["folder"], "analysis_results.json"
        )
        if not os.path.exists(results_path):
            print(f"[⚠️] No analysis_results.json in {scan['folder']}")
            continue

        with open(results_path, 'r') as f:
            results = json.load(f)

        label = scan["label"]
        fired_rules = [r["rule_id"] for r in results["rules"] if r["fired"]]

        for rule_id in RULES:
            fired = rule_id in fired_rules
            if label == "anomaly" and fired:
                rule_data[rule_id]["tp"] += 1
            elif label == "normal" and fired:
                rule_data[rule_id]["fp"] += 1
            elif label == "anomaly" and not fired:
                rule_data[rule_id]["fn"] += 1
            elif label == "normal" and not fired:
                rule_data[rule_id]["tn"] += 1

    # Print results
    print(f"\n{'Rule':<6} {'TP':<5} {'FP':<5} {'TN':<5} {'FN':<5} "
          f"{'Precision':<12} {'Recall':<10} {'Assessment'}")
    print("-"*65)

    for rule_id in RULES:
        d = rule_data[rule_id]
        tp, fp, tn, fn = d["tp"], d["fp"], d["tn"], d["fn"]

        precision = round(tp / (tp + fp) * 100, 1) if (tp + fp) > 0 else 0
        recall = round(tp / (tp + fn) * 100, 1) if (tp + fn) > 0 else 0

        if tp == 0 and fp == 0:
            assessment = "Not triggered"
        elif fp == 0 and fn == 0:
            assessment = "Perfect ✅"
        elif fp > 0 and fn == 0:
            assessment = "False positives ⚠️"
        elif fp == 0 and fn > 0:
            assessment = "Missed some ⚠️"
        else:
            assessment = "Needs improvement ❌"

        print(f"{rule_id:<6} {tp:<5} {fp:<5} {tn:<5} {fn:<5} "
              f"{precision:<12} {recall:<10} {assessment}")

    print("\n" + "="*65)
    print("LEGEND:")
    print("TP = True Positive  (correctly detected anomaly)")
    print("FP = False Positive (incorrectly flagged normal as anomaly)")
    print("TN = True Negative  (correctly identified clean)")
    print("FN = False Negative (missed an anomaly)")
    print("="*65)

if __name__ == "__main__":
    validate()