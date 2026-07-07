# report_generator.py
# Generates a downloadable forensic PDF report for a single scan,
# summarizing rule engine findings, ML verdict, and collected artifacts.
# Designed to be called from app.py (Streamlit dashboard).

import os
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


# ─────────────────────────────────────────────
# COLOR PALETTE (kept close to the dashboard's
# dark security-tool theme, but PDF-safe)
# ─────────────────────────────────────────────
COLOR_DARK_NAVY   = colors.HexColor("#0a1626")
COLOR_TEXT        = colors.HexColor("#1a1a2e")
COLOR_MUTED       = colors.HexColor("#5d7299")
COLOR_RED         = colors.HexColor("#c0392b")
COLOR_ORANGE      = colors.HexColor("#e0922b")
COLOR_BLUE        = colors.HexColor("#1f6fb2")
COLOR_GREEN       = colors.HexColor("#1f9254")
COLOR_TABLE_HEAD  = colors.HexColor("#16324f")
COLOR_TABLE_ALT   = colors.HexColor("#f2f5f9")


def _confidence_color(pct):
    if pct >= 70:
        return COLOR_RED
    if pct >= 40:
        return COLOR_ORANGE
    if pct >= 15:
        return COLOR_BLUE
    return COLOR_GREEN


def _get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle", fontName="Helvetica-Bold", fontSize=20,
        textColor=COLOR_TEXT, spaceAfter=4, alignment=TA_LEFT
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle", fontName="Helvetica", fontSize=10,
        textColor=COLOR_MUTED, spaceAfter=14
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", fontName="Helvetica-Bold", fontSize=13,
        textColor=COLOR_TEXT, spaceBefore=16, spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="SubHeading", fontName="Helvetica-Bold", fontSize=10.5,
        textColor=COLOR_TEXT, spaceBefore=10, spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="BodyTextSmall", fontName="Helvetica", fontSize=9.5,
        textColor=COLOR_TEXT, leading=14
    ))
    styles.add(ParagraphStyle(
        name="EvidenceText", fontName="Courier", fontSize=8.5,
        textColor=COLOR_MUTED, leftIndent=10, leading=12
    ))
    styles.add(ParagraphStyle(
        name="MutedSmall", fontName="Helvetica", fontSize=8,
        textColor=COLOR_MUTED
    ))
    styles.add(ParagraphStyle(
        name="VerdictBig", fontName="Helvetica-Bold", fontSize=16,
        alignment=TA_CENTER
    ))
    return styles


def _summary_table(rows, styles, col_widths=None):
    """Simple 2-column key/value table for header-level summary info."""
    table_rows = []
    for label, value in rows:
        table_rows.append([
            Paragraph(f"<b>{label}</b>", styles["BodyTextSmall"]),
            Paragraph(str(value), styles["BodyTextSmall"]),
        ])

    t = Table(table_rows, colWidths=col_widths or [55 * mm, 110 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#e0e0e0")),
    ]))
    return t


def generate_report(
    scan_name,
    res,            # analysis_results.json contents
    summ,           # scan_summary.json contents (may be None)
    ml_label,       # "ANOMALY" / "NORMAL" / "—"
    ml_score,       # float or None
    output_path=None
):
    """
    Build a forensic PDF report for one scan.

    Parameters mirror what app.py already loads for the Overview tab:
    res      -> result of load_r(scan_path)  (analysis_results.json)
    summ     -> result of load_s(scan_path)  (scan_summary.json)
    ml_label -> e.g. "ANOMALY" / "NORMAL" / "—"
    ml_score -> raw isolation forest score, or None

    Returns: the output_path the PDF was written to (str)
    If output_path is None, writes to an in-memory buffer and returns
    the bytes instead (useful for Streamlit's download_button).
    """
    styles = _get_styles()

    buffer = io.BytesIO() if output_path is None else None
    target = buffer if buffer is not None else output_path

    doc = SimpleDocTemplate(
        target, pagesize=A4,
        topMargin=18 * mm, bottomMargin=16 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
        title=f"DroidSentinel Forensic Report — {scan_name}"
    )

    story = []

    # ── Header ──
    story.append(Paragraph("DroidSentinel", styles["ReportTitle"]))
    story.append(Paragraph(
        "Anti-Forensics Detection Report — Android Device Scan",
        styles["ReportSubtitle"]
    ))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc"), thickness=0.8))
    story.append(Spacer(1, 10))

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    devinfo = summ.get("device_info", {}) if summ else {}

    header_rows = [
        ("Scan ID:", scan_name),
        ("Device Model:", devinfo.get("model", "—")),
        ("Android Version:", devinfo.get("android_version", "—")),
        ("Scan Time:", devinfo.get("scan_time", res.get("analysis_time", "—"))),
        ("Report Generated:", generated_at),
    ]
    story.append(_summary_table(header_rows, styles))
    story.append(Spacer(1, 14))

    # ── Verdict Summary ──
    pct = res.get("confidence_pct", 0)
    verdict_clean = res.get("verdict", "").replace("🚨", "").replace("⚠️", "") \
        .replace("🔎", "").replace("✅", "").strip()
    conf_color = _confidence_color(pct)

    story.append(Paragraph("Overall Verdict", styles["SectionHeading"]))

    verdict_table = Table(
        [[
            Paragraph(
                f"<font color='{conf_color.hexval()}'><b>{verdict_clean}</b></font>",
                styles["VerdictBig"]
            )
        ]],
        colWidths=[165 * mm]
    )
    verdict_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f5f5")),
        ("BOX", (0, 0), (-1, -1), 0.8, conf_color),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(verdict_table)
    story.append(Spacer(1, 8))

    fired_count = res.get("fired_count", 0)
    total_rules = len(res.get("rules", []))
    verdict_rows = [
        ("Confidence Score:", f"{pct}%  ({res.get('overall_confidence', 'NONE')})"),
        ("Points Scored:", f"{res.get('total_score', 0)} / {res.get('max_score', 285)} pts"),
        ("Rules Fired:", f"{fired_count} of {total_rules}"),
        ("ML Model Verdict:", f"{ml_label}" + (f"  (score: {ml_score})" if ml_score is not None else "")),
    ]
    story.append(_summary_table(verdict_rows, styles))
    story.append(Spacer(1, 16))

    # ── Fired Rules — Detailed Evidence ──
    rules = res.get("rules", [])
    fired = [r for r in rules if r.get("fired")]
    clear = [r for r in rules if not r.get("fired")]

    story.append(Paragraph(
        f"Detection Evidence — {len(fired)} Rule(s) Fired", styles["SectionHeading"]
    ))

    if not fired:
        story.append(Paragraph(
            "No anti-forensic indicators were detected on this scan.",
            styles["BodyTextSmall"]
        ))
    else:
        for rule in fired:
            badge_color = {
                "HIGH": COLOR_RED, "MEDIUM": COLOR_ORANGE,
                "LOW": COLOR_BLUE, "NONE": COLOR_MUTED
            }.get(rule.get("confidence", "NONE"), COLOR_MUTED)

            heading = (
                f"<font color='{badge_color.hexval()}'>●</font> "
                f"<b>{rule['rule_id']} — {rule['rule_name']}</b>"
                f"  &nbsp;&nbsp;"
                f"<font color='{badge_color.hexval()}'>[{rule.get('confidence','NONE')}]</font>"
                f"  &nbsp;&nbsp;{rule['score']}/{rule['weight']} pts"
            )
            story.append(Paragraph(heading, styles["SubHeading"]))
            story.append(Paragraph(
                f"Artifact: {rule.get('artifact', '—')}", styles["MutedSmall"]
            ))

            for ev in rule.get("evidence", []):
                ev_escaped = (
                    ev.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                )
                story.append(Paragraph(f"▸ {ev_escaped}", styles["EvidenceText"]))

            story.append(Spacer(1, 6))

    # ── Clear Rules — quick summary table ──
    if clear:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Clear Rules — No Evidence Found", styles["SubHeading"]))

        clear_rows = [["Rule", "Description"]]
        for rule in clear:
            clear_rows.append([rule["rule_id"], rule["rule_name"]])

        t = Table(clear_rows, colWidths=[20 * mm, 145 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_TABLE_HEAD),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_TABLE_ALT]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)

    # ── Collected Artifacts ──
    story.append(PageBreak())
    story.append(Paragraph("Collected Artifacts", styles["SectionHeading"]))

    arts = summ.get("system_artifacts", {}) if summ else {}
    art_list = [
        ("packages_xml", "packages.xml"),
        ("usagestats", "usagestats/"),
        ("notification_log", "notification_log.db"),
        ("dropbox", "dropbox/"),
        ("netstats", "netstats/"),
        ("runtime_permissions", "runtime-perms.xml"),
    ]

    art_rows = [["Artifact", "Status", "Size"]]
    for key, label in art_list:
        a = arts.get(key, {})
        ok = a.get("success", False)
        size = a.get("size", 0)
        art_rows.append([
            label,
            "Collected" if ok else "Not Found",
            f"{size:,} bytes" if ok else "—"
        ])

    t = Table(art_rows, colWidths=[60 * mm, 45 * mm, 60 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_TABLE_HEAD),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_TABLE_ALT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    # ── Disclaimer / Footer note ──
    story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc"), thickness=0.6))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This report was automatically generated by DroidSentinel, a hybrid "
        "rule-based and machine-learning anti-forensics detection tool. "
        "Findings are based on artifacts collected directly from the device "
        "at scan time and should be reviewed alongside other forensic "
        "evidence as part of a complete investigation. This report does not "
        "constitute legal certification of evidentiary findings.",
        styles["MutedSmall"]
    ))

    doc.build(story)

    if buffer is not None:
        buffer.seek(0)
        return buffer.getvalue()
    return output_path