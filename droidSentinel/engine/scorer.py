import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
# ATTACK VECTOR GROUPINGS — CORRECTED
# Each rule can belong to multiple vectors
# based on actual forensic behavior observed
# ─────────────────────────────────────────────
ATTACK_VECTORS = {
    "Vector 1 — File Wiping": {
        "rules": ["R01", "R03", "R07", "R08", "R09", "R10","R11"],
        "description": "Detection of file wiping app activity",
        "color": "#FF4444"
    },
    "Vector 2 — App Uninstall / Ghost Trace": {
        "rules": ["R02", "R03", "R06"],
        "description": "Detection of app uninstall to conceal wiping",
        "color": "#FF8800"
    },
    "Vector 3 — Manual Log Clearing": {
        "rules": ["R01", "R02", "R03", "R04"],
        "description": "Detection of deliberate system log clearing",
        "color": "#FFCC00"
    },
    "Vector 4 — Factory Reset": {
        "rules": ["R01", "R05", "R06"],
        "description": "Detection of factory reset to destroy evidence",
        "color": "#AA44FF"
    }
}

# ─────────────────────────────────────────────
# MULTI-VECTOR BONUS MULTIPLIERS
# More vectors detected = higher suspicion
# ─────────────────────────────────────────────
MULTI_VECTOR_BONUS = {
    1: 1.0,   # 1 vector fired — no bonus
    2: 1.15,  # 2 vectors fired — 15% bonus
    3: 1.30,  # 3 vectors fired — 30% bonus
    4: 1.50   # all 4 vectors fired — 50% bonus
}


def calculate_vector_scores(rule_results):
    """
    Group rule results by attack vector.
    Calculate per-vector score and confidence.
    Note: Same rule can contribute to multiple vectors.
    """
    rule_lookup = {r["rule_id"]: r for r in rule_results}

    vector_scores = {}

    for vector_name, vector_config in ATTACK_VECTORS.items():
        vector_rules = vector_config["rules"]

        # Get rules that belong to this vector
        relevant_rules = [
            rule_lookup[rid]
            for rid in vector_rules
            if rid in rule_lookup
        ]

        # Calculate max possible score for this vector
        max_score = sum(r["weight"] for r in relevant_rules)

        # Calculate actual score
        actual_score = sum(r["score"] for r in relevant_rules)

        # Calculate percentage
        pct = round(
            (actual_score / max_score) * 100, 1
        ) if max_score > 0 else 0

        # Determine vector confidence
        if pct >= 70:
            confidence = "HIGH"
        elif pct >= 40:
            confidence = "MEDIUM"
        elif pct > 0:
            confidence = "LOW"
        else:
            confidence = "NONE"

        # Which rules fired in this vector
        fired_rules = [r for r in relevant_rules if r["fired"]]

        vector_scores[vector_name] = {
            "description": vector_config["description"],
            "color": vector_config["color"],
            "rules_checked": len(relevant_rules),
            "rules_fired": len(fired_rules),
            "fired_rule_ids": [r["rule_id"] for r in fired_rules],
            "max_score": max_score,
            "actual_score": actual_score,
            "percentage": pct,
            "confidence": confidence,
            "detected": len(fired_rules) > 0
        }

    return vector_scores


def calculate_final_score(rule_results, vector_scores):
    """
    Calculate final weighted confidence score.
    Applies multi-vector bonus if multiple vectors detected.
    """
    # Base score from rule engine
    total_score = sum(r["score"] for r in rule_results)
    max_score = sum(r["weight"] for r in rule_results)
    base_pct = round(
        (total_score / max_score) * 100, 1
    ) if max_score > 0 else 0

    # Count how many vectors were detected
    detected_vectors = [
        v for v, data in vector_scores.items()
        if data["detected"]
    ]
    num_detected = len(detected_vectors)

    # Apply multi-vector bonus
    multiplier = MULTI_VECTOR_BONUS.get(num_detected, 1.0)
    adjusted_pct = min(round(base_pct * multiplier, 1), 100.0)

    # Determine overall confidence
    if adjusted_pct >= 70:
        overall_confidence = "HIGH"
        verdict = "🚨 ANTI-FORENSIC ACTIVITY STRONGLY DETECTED"
        verdict_short = "STRONGLY DETECTED"
    elif adjusted_pct >= 40:
        overall_confidence = "MEDIUM"
        verdict = "⚠️  SUSPICIOUS ACTIVITY DETECTED"
        verdict_short = "SUSPICIOUS"
    elif adjusted_pct >= 15:
        overall_confidence = "LOW"
        verdict = "🔎 MINOR INDICATORS DETECTED"
        verdict_short = "MINOR INDICATORS"
    else:
        overall_confidence = "NONE"
        verdict = "✅ NO ANTI-FORENSIC ACTIVITY DETECTED"
        verdict_short = "CLEAN"

    return {
        "base_score": total_score,
        "max_score": max_score,
        "base_pct": base_pct,
        "multiplier": multiplier,
        "adjusted_pct": adjusted_pct,
        "overall_confidence": overall_confidence,
        "verdict": verdict,
        "verdict_short": verdict_short,
        "vectors_detected": num_detected,
        "detected_vector_names": detected_vectors
    }


def generate_summary(rule_results, vector_scores, final_score, device_info):
    """
    Generate complete analysis summary.
    This is what gets passed to dashboard and PDF report.
    """
    fired_rules = [r for r in rule_results if r["fired"]]

    summary = {
        "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "device_info": device_info,
        "final_score": final_score,
        "vector_scores": vector_scores,
        "fired_rules": fired_rules,
        "all_rules": rule_results,
        "total_rules_fired": len(fired_rules),
        "total_rules_checked": len(rule_results)
    }

    return summary


def print_scored_results(summary):
    """
    Print complete scored analysis to console.
    """
    print("\n" + "="*55)
    print("  DroidSentinel — Confidence Scorer v1.0")
    print("="*55)

    # Device info
    device = summary.get("device_info", {})
    if device:
        print(f"\n📱 Device: {device.get('model', 'Unknown')}")
        print(f"🤖 Android: {device.get('android_version', 'Unknown')} "
              f"(API {device.get('api_level', 'Unknown')})")
        print(f"🕐 Scan Time: {summary['scan_time']}")

    # Per-vector breakdown
    print("\n" + "="*55)
    print("ATTACK VECTOR BREAKDOWN")
    print("="*55)

    for vector_name, data in summary["vector_scores"].items():
        status = "🔴 DETECTED" if data["detected"] else "⚪ NOT DETECTED"
        print(f"\n{status} — {vector_name}")
        print(f"   Description: {data['description']}")
        print(
            f"   Rules Fired: {data['rules_fired']}/{data['rules_checked']}"
            f" ({', '.join(data['fired_rule_ids']) if data['fired_rule_ids'] else 'none'})"
        )
        print(
            f"   Score: {data['actual_score']}/{data['max_score']} "
            f"({data['percentage']}%) — {data['confidence']}"
        )

    # Final score
    fs = summary["final_score"]
    print("\n" + "="*55)
    print("FINAL CONFIDENCE SCORE")
    print("="*55)
    print(f"\n{fs['verdict']}")
    print(
        f"\n📊 Base Score:        {fs['base_score']}/{fs['max_score']} "
        f"({fs['base_pct']}%)"
    )
    print(f"📊 Vectors Detected:  {fs['vectors_detected']}/4")
    print(f"📊 Bonus Multiplier:  x{fs['multiplier']}")
    print(
        f"📊 Final Confidence:  {fs['adjusted_pct']}% "
        f"({fs['overall_confidence']})"
    )

    if fs["detected_vector_names"]:
        print(f"\n🎯 Active Vectors:")
        for v in fs["detected_vector_names"]:
            print(f"   • {v}")

    print("\n" + "="*55)

    return summary


def score(rule_results, device_info=None):
    """
    Main scoring function.
    Call this from app.py with rule engine output.
    Returns complete summary for dashboard.
    """
    # Step 1 — Calculate per-vector scores
    vector_scores = calculate_vector_scores(rule_results)

    # Step 2 — Calculate final score with bonus
    final_score = calculate_final_score(rule_results, vector_scores)

    # Step 3 — Generate complete summary
    summary = generate_summary(
        rule_results, vector_scores, final_score, device_info or {}
    )

    # Step 4 — Print results
    print_scored_results(summary)

    return summary


# ─────────────────────────────────────────────
# RUN DIRECTLY — Test with rule engine output
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.append(r"D:\DroidSentinel\engine")
    from rule_engine import analyze

    BASELINE = r"D:\DroidSentinel\scans\baseline_scan"
    CURRENT = r"D:\DroidSentinel\scans\scan_20260615_152150"

    # Get rule engine results
    engine_results = analyze(BASELINE, CURRENT)

    # Load device info from scan summary
    summary_path = os.path.join(CURRENT, "scan_summary.json")
    device_info = {}
    if os.path.exists(summary_path):
        with open(summary_path, 'r') as f:
            scan_data = json.load(f)
            device_info = scan_data.get("device_info", {})

    # Run scorer
    score(engine_results["rules"], device_info)