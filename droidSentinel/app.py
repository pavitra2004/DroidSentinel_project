# app.py — DroidSentinel Dashboard v3.3 (Sidebar + Font Fix)
# Run: streamlit run D:\DroidSentinel\app.py

import streamlit as st
import json, os, sys, sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ── Portable path setup ───────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from config import (
    SCANS_DIR, ENGINE_DIR, BASELINE_SCAN_DIR,
    ML_RESULTS_PATH, PROJECT_ROOT
)
sys.path.append(ENGINE_DIR)
# ─────────────────────────────────────────────────────────────────────────────
try:
    from report_generator import generate_report
except ImportError:
    generate_report = None

st.set_page_config(
    page_title="DroidSentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ──
_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;}

/* BASE — every container dark */
html,body,.stApp,[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],[data-testid="stMain"],
.main,.block-container,[data-testid="stVerticalBlock"]{
    background-color:#060a12 !important;
    color:#dbe4f5 !important;
    font-family:'Inter',sans-serif !important;
    font-size:16px !important;
}

/* HIDE CHROME — but KEEP the sidebar collapse/expand control alive.
   We hide the top menu/toolbar/footer/deploy button individually instead
   of nuking the whole header, so the sidebar toggle arrow still works. */
#MainMenu,footer,.stDeployButton,[data-testid="stStatusWidget"],
[data-testid="stToolbarActions"],
button[kind="header"][data-testid="baseButton-header"],
[data-testid="stHeaderActionElements"],
div[class*="stAppDeployButton"],
button[title="Deploy this app"]{
    display:none !important;visibility:hidden !important;
}
header[data-testid="stHeader"]{
    background-color:#060a12 !important;
    height:2rem !important;
    min-height:2rem !important;
    z-index:999999 !important;
    border:none !important;
    border-bottom:none !important;
    box-shadow:none !important;
}
/* Force the sidebar collapse/expand control to always stay visible,
   regardless of which wrapper Streamlit nests it in. */
header[data-testid="stHeader"] [data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"]{
    visibility:visible !important;
    display:flex !important;
    opacity:1 !important;
}
/* Make the sidebar expand/collapse control clearly visible against the dark bg */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"]{
    visibility:visible !important;
    display:flex !important;
    background:#0a2040 !important;
    border:1px solid #00aaff !important;
    border-radius:6px !important;
    color:#00aaff !important;
    z-index:999999 !important;
}
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="collapsedControl"] svg{
    fill:#00aaff !important;
    color:#00aaff !important;
}
[data-testid="baseButton-headerNoPadding"]{
    color:#00aaff !important;
}

/* BLOCK CONTAINER */
.block-container{padding-top:2.2rem !important;max-width:100% !important;padding-left:2rem !important;padding-right:2rem !important;}

/* ── RESPONSIVE FIX ──────────────────────────────────────────────────────
   Only remove the hard-coded min-widths that stop the main pane from
   reclaiming/shrinking space. Streamlit already handles the actual
   collapse/expand animation itself (via its own margin-left transform on
   the sidebar) — we must NOT re-declare display/flex/margin on top of
   that or we fight its JS and the layout shifts off-screen. */
[data-testid="stAppViewContainer"]{
    min-width:0 !important;
}
[data-testid="stMain"]{
    min-width:0 !important;
}
[data-testid="stMain"] .block-container,
.main .block-container{
    min-width:0 !important;
}

/* SIDEBAR */
[data-testid="stSidebar"]{background-color:#07111e !important;border-right:1px solid #0f2035 !important;}
[data-testid="stSidebar"][aria-expanded="true"]{min-width:300px !important;max-width:300px !important;}
[data-testid="stSidebar"]>div{background-color:#07111e !important;}
[data-testid="stSidebar"] *{color:#dbe4f5 !important;}

/* TABS */
.stTabs [data-baseweb="tab-list"]{background:transparent !important;border-bottom:1px solid #0f2035 !important;gap:0 !important;}
.stTabs [data-baseweb="tab"]{
    background:transparent !important;border:none !important;
    color:#4d7299 !important;font-family:'Inter',sans-serif !important;
    font-size:0.95em !important;font-weight:700 !important;
    letter-spacing:1.5px !important;text-transform:uppercase !important;
    padding:14px 24px !important;border-bottom:2px solid transparent !important;
}
.stTabs [aria-selected="true"]{color:#22b6ff !important;border-bottom:2px solid #22b6ff !important;background:transparent !important;}
.stTabs [data-baseweb="tab-panel"]{padding-top:24px !important;background:transparent !important;}
.stTabs [data-baseweb="tab-highlight"]{background:transparent !important;}

/* BUTTON — visible, bright */
.stButton>button{
    background:linear-gradient(135deg,#0046a8,#0066ee) !important;
    color:#ffffff !important;border:1px solid #2391ff !important;
    border-radius:8px !important;font-family:'Inter',sans-serif !important;
    font-weight:700 !important;font-size:1em !important;
    letter-spacing:0.5px !important;padding:12px 20px !important;
    width:100% !important;cursor:pointer !important;transition:all .2s !important;
    box-shadow:0 0 0 1px rgba(34,182,255,0.25) !important;
}
.stButton>button:hover{background:linear-gradient(135deg,#0055cc,#1f87ff) !important;border-color:#55b3ff !important;}
.stButton>button p,.stButton>button span,.stButton>button div{color:#ffffff !important;font-weight:700 !important;}

/* DOWNLOAD BUTTON — Streamlit renders this as a separate component
   from st.button, so it needs its own matching dark-theme styling */
.stDownloadButton>button{
    background:linear-gradient(135deg,#0046a8,#0066ee) !important;
    color:#ffffff !important;border:1px solid #2391ff !important;
    border-radius:8px !important;font-family:'Inter',sans-serif !important;
    font-weight:700 !important;font-size:1em !important;
    letter-spacing:0.5px !important;padding:12px 20px !important;
    width:100% !important;cursor:pointer !important;transition:all .2s !important;
    box-shadow:0 0 0 1px rgba(34,182,255,0.25) !important;
}
.stDownloadButton>button:hover{background:linear-gradient(135deg,#0055cc,#1f87ff) !important;border-color:#55b3ff !important;}
.stDownloadButton>button p,.stDownloadButton>button span,.stDownloadButton>button div{color:#ffffff !important;font-weight:700 !important;}

/* RADIO (used as a pill-style view toggle, e.g. ML predictions filter) */
.stRadio>label{display:none !important;}
.stRadio [role="radiogroup"]{gap:8px !important;}
.stRadio [data-baseweb="radio"]{
    background:#0a1c30 !important;border:1px solid #1c3a5c !important;
    border-radius:8px !important;padding:6px 14px !important;
    margin-right:4px !important;
}
.stRadio [data-baseweb="radio"] label{
    color:#9bbade !important;font-family:'Inter',sans-serif !important;
    font-size:0.92em !important;font-weight:600 !important;
}
.stRadio [data-baseweb="radio"]:has(input:checked){
    background:#123a63 !important;border-color:#22b6ff !important;
}
.stRadio [data-baseweb="radio"]:has(input:checked) label{
    color:#22b6ff !important;
}

/* TEXT INPUT (e.g. sidebar date filter) */
.stTextInput>label{display:none !important;}
.stTextInput input{
    background-color:#0a1c30 !important;border:1px solid #1c3a5c !important;
    border-radius:8px !important;color:#cfe0f5 !important;
    font-family:'JetBrains Mono',monospace !important;font-size:0.92em !important;
    padding:8px 12px !important;
}
.stTextInput input::placeholder{color:#3f6b96 !important;opacity:1 !important;}
.stTextInput input:focus{border-color:#22b6ff !important;box-shadow:0 0 0 1px rgba(34,182,255,0.3) !important;}

/* SELECTBOX */
.stSelectbox>label,.stSelectbox label{display:none !important;}
.stSelectbox [data-baseweb="select"]>div{
    background-color:#0a1c30 !important;border:1px solid #1c3a5c !important;
    border-radius:8px !important;color:#cfe0f5 !important;
    font-family:'JetBrains Mono',monospace !important;font-size:0.95em !important;
}
.stSelectbox [data-baseweb="select"] span,.stSelectbox [data-baseweb="select"] div{
    color:#cfe0f5 !important;background-color:transparent !important;
}
[data-baseweb="popover"],
[data-baseweb="popover"] *:not([data-baseweb="option"]):not([data-baseweb="option"] *),
div[data-baseweb="popover"] > div,
ul[role="listbox"],
[data-baseweb="menu"]{
    background-color:#0a1c30 !important;
    border-color:#1c3a5c !important;
}
[data-baseweb="popover"]{
    border:1px solid #1c3a5c !important;
    box-shadow:0 8px 24px rgba(0,0,0,0.5) !important;
}
li[role="option"],
[data-baseweb="option"],
[data-baseweb="menu"] li{
    background-color:#0a1c30 !important;color:#cfe0f5 !important;
    font-family:'JetBrains Mono',monospace !important;font-size:0.95em !important;
}
li[role="option"]:hover,
[data-baseweb="option"]:hover,
[data-baseweb="menu"] li:hover{
    background-color:#123354 !important;color:#ffffff !important;
}
li[aria-selected="true"][role="option"],
[aria-selected="true"][data-baseweb="option"]{
    background-color:#123a63 !important;color:#22b6ff !important;
}

/* MARKDOWN TEXT */
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] span{color:#dbe4f5 !important;font-size:1em !important;}

/* ALERTS */
.stAlert{background-color:#0a1c30 !important;border:1px solid #1c3a5c !important;color:#dbe4f5 !important;}
.stAlert p,.stAlert span{color:#dbe4f5 !important;}

/* COLUMN GAPS */
[data-testid="stHorizontalBlock"]{gap:1rem !important;}
[data-testid="column"]{background:transparent !important;}

/* SCROLLBAR */
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:#060a12;}
::-webkit-scrollbar-thumb{background:#1c3a5c;border-radius:3px;}

/* ── CARD CLASSES ── */
.ds-card{background:#0a1626;border:1px solid #1c3a5c;border-radius:10px;padding:20px 24px;margin-bottom:12px;color:#dbe4f5;}
.ds-card-red{background:#1a0d0d;border:1px solid #5c1414;border-radius:10px;padding:24px 32px;margin-bottom:12px;}
.ds-card-yellow{background:#1a160d;border:1px solid #5c4514;border-radius:10px;padding:24px 32px;margin-bottom:12px;}
.ds-card-green{background:#0d1a0d;border:1px solid #145c14;border-radius:10px;padding:24px 32px;margin-bottom:12px;}
.ds-card-blue{background:#0a1a2e;border:1px solid #14457c;border-radius:10px;padding:24px 32px;margin-bottom:12px;}

.ds-label{font-size:0.8em;font-weight:700;color:#5d87b3;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:8px;font-family:'Inter',sans-serif;}

/* RULE ENGINE */
.ds-rule-fired{
    background:#1a0d0d;border:1px solid #4a1414;
    border-left:3px solid #ff4444;border-radius:8px;
    padding:20px 24px;margin-bottom:14px;
}
.ds-rule-fired-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;}
.ds-rule-id{font-size:0.85em;font-weight:700;color:#ff5555;letter-spacing:1.5px;font-family:'JetBrains Mono',monospace;margin-bottom:4px;}
.ds-rule-name{font-size:1.15em;font-weight:700;color:#f2f5fb;margin-bottom:6px;font-family:'Inter',sans-serif;}
.ds-rule-artifact{font-size:0.92em;color:#7295bb;font-family:'JetBrains Mono',monospace;}
.ds-rule-pts{font-size:1.05em;font-weight:700;color:#ff7777;font-family:'JetBrains Mono',monospace;}
.ds-ev{
    background:#0a1320;border-left:2px solid #2c5a89;
    padding:8px 14px;margin-top:6px;border-radius:0 4px 4px 0;
    font-size:0.95em;color:#9bbade;
    font-family:'JetBrains Mono',monospace;line-height:1.7;
}
.ds-rule-clear{
    background:#0a1626;border:1px solid #15293f;border-left:2px solid #1d3a58;
    border-radius:8px;padding:14px 18px;margin-bottom:8px;
}
.ds-rule-clear-id{font-size:0.85em;font-weight:700;color:#3f6b96;letter-spacing:1px;font-family:'JetBrains Mono',monospace;margin-bottom:3px;}
.ds-rule-clear-name{font-size:1em;font-weight:600;color:#5d87b3;margin-bottom:5px;font-family:'Inter',sans-serif;}
.ds-rule-clear-ev{font-size:0.88em;color:#3f6b96;font-family:'JetBrains Mono',monospace;}
</style>
"""
st.html(_CSS)

import streamlit.components.v1 as components
components.html("""
<script>
(function(){
    function fireResize(){
        try { window.parent.dispatchEvent(new Event('resize')); } catch(e) {}
        try { window.dispatchEvent(new Event('resize')); } catch(e) {}
    }
    function pulseResize(){
        // Streamlit only recalculates the main pane's width on an actual
        // window 'resize' event. Clicking the sidebar collapse arrow changes
        // the DOM (aria-expanded) but never fires that event, so the main
        // pane's width goes stale -> visible gap / cut-off content. Firing a
        // burst of resize events across the CSS collapse transition keeps it
        // in sync no matter how long that transition takes.
        var i = 0;
        var iv = setInterval(function(){
            fireResize();
            i++;
            if (i > 12) clearInterval(iv);
        }, 40);
    }
    function watchSidebar(){
        var doc = window.parent.document;
        var sb = doc.querySelector('[data-testid="stSidebar"]');
        if(!sb){ setTimeout(watchSidebar, 300); return; }
        var obs = new MutationObserver(function(mutations){
            mutations.forEach(function(m){
                if(m.attributeName === 'aria-expanded'){ pulseResize(); }
            });
        });
        obs.observe(sb, {attributes:true, attributeFilter:['aria-expanded']});
        // also cover the collapse/expand arrow button click directly, in case
        // the attribute change lags behind the click
        var btn = doc.querySelector('[data-testid="stSidebarCollapseButton"] button, [data-testid="collapsedControl"] button');
        if(btn){ btn.addEventListener('click', pulseResize); }
    }
    watchSidebar();
})();
</script>
""", height=0, width=0)

# ── Paths ──
SCANS   = SCANS_DIR
ENGINE  = ENGINE_DIR
BASE    = BASELINE_SCAN_DIR
ML_PATH = ML_RESULTS_PATH

# ── Helpers ──
def all_scans():
    if not os.path.exists(SCANS): return []
    out = []
    for f in sorted(os.listdir(SCANS), reverse=True):
        fp = os.path.join(SCANS, f)
        if os.path.isdir(fp):
            out.append({"name":f,"path":fp,
                "ok":os.path.exists(os.path.join(fp,"analysis_results.json"))})
    return out

def load_r(path):
    p = os.path.join(path,"analysis_results.json")
    return json.load(open(p)) if os.path.exists(p) else None

def load_s(path):
    p = os.path.join(path,"scan_summary.json")
    return json.load(open(p)) if os.path.exists(p) else None

def load_ml():
    return json.load(open(ML_PATH)) if os.path.exists(ML_PATH) else None

def tcolor(pct):
    if pct>=70: return "#ff3333"
    if pct>=40: return "#ffb020"
    if pct>=15: return "#2299ff"
    return "#21d35a"

def tcard(pct):
    if pct>=70: return "ds-card-red"
    if pct>=40: return "ds-card-yellow"
    if pct>=15: return "ds-card-blue"
    return "ds-card-green"

def badge(c):
    clr = {"HIGH":"#ff4444","MEDIUM":"#ffb020","LOW":"#2299ff","NONE":"#5d87b3"}.get(c,"#5d87b3")
    return f"<span style='color:{clr};font-weight:700;font-size:0.9em;letter-spacing:1px;border:1px solid {clr}66;padding:3px 10px;border-radius:4px;'>{c}</span>"

def dot_color(pct):
    if pct>=70: return "#ff3333"
    if pct>=40: return "#ffb020"
    if pct>=15: return "#2299ff"
    return "#21d35a"

def gauge(val, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        number={"suffix":"%","font":{"color":color,"size":56,"family":"JetBrains Mono"}},
        gauge={
            "axis":{"range":[0,100],"tickwidth":0,"tickcolor":"rgba(0,0,0,0)",
                    "tickfont":{"color":"rgba(0,0,0,0)","size":1}},
            "bar":{"color":color,"thickness":0.25},
            "bgcolor":"#0a1626",
            "borderwidth":0,
            "steps":[
                {"range":[0,15],"color":"#0a1626"},
                {"range":[15,40],"color":"#0c1a2a"},
                {"range":[40,70],"color":"#10171f"},
                {"range":[70,100],"color":"#190d0d"},
            ],
            "threshold":{"line":{"color":color,"width":3},"thickness":0.8,"value":val}
        }
    ))
    fig.update_layout(
        paper_bgcolor="#0a1626",plot_bgcolor="#0a1626",
        height=240,margin=dict(l=24,r=24,t=8,b=4),
        font={"family":"JetBrains Mono","color":color}
    )
    return fig

def update_ml_results(scan_folder, ml_result, rule_engine_result=None):
    """
    Append (or refresh) this scan's ML prediction inside ml_results.json's
    validation_results list, so the dashboard's ML Analysis tab and the
    per-scan ML Verdict card immediately reflect the new scan.

    For live scans we don't have a human-confirmed ground-truth label,
    but we DO have the rule engine's independent verdict for this exact
    scan (real evidence: PDF reports, job counters, ghost traces, etc.).
    We use that as a proxy "actual" label instead of leaving it unknown:
        any rule fired  -> actual = "anomaly"
        no rules fired  -> actual = "normal"
    This lets us show a real ✓/✗ comparing the ML model's independent
    guess against the rule engine's evidence-backed verdict, which is a
    more useful comparison than an unlabeled "unknown" row.
    """
    scan_name = os.path.basename(scan_folder)

    if os.path.exists(ML_PATH):
        with open(ML_PATH, "r") as f:
            data = json.load(f)
    else:
        # No trained model / results file yet — nothing to merge into.
        return

    vr = data.get("validation_results", [])

    if rule_engine_result is not None:
        fired_count = rule_engine_result.get("fired_count", 0)
        actual = "anomaly" if fired_count > 0 else "normal"
    else:
        # Rule engine result wasn't passed in for some reason — fall
        # back to unknown rather than guessing blindly.
        actual = "unknown"

    predicted = ml_result.get("ml_prediction", "unknown")
    correct = (actual == predicted) if actual != "unknown" else None

    new_entry = {
        "scan": scan_name,
        "actual": actual,
        "predicted": predicted,
        "score": ml_result.get("ml_score", 0),
        "correct": correct
    }

    # Replace any existing entry for this scan (e.g. re-running a scan),
    # otherwise add it.
    vr = [r for r in vr if r.get("scan") != scan_name]
    vr.append(new_entry)
    data["validation_results"] = vr

    with open(ML_PATH, "w") as f:
        json.dump(data, f, indent=4)


def run_scan():
    try:
        sys.path.insert(0, PROJECT_ROOT)
        from collector.artifact_collector import collect
        from engine.rule_engine import analyze
        from engine.ml_detector import predict_scan

        with st.spinner("📡 Connecting to device..."):
            sf = collect()
        if not sf:
            st.error("❌ No device connected. Make sure emulator-5554 is running.")
            return None

        with st.spinner("🔍 Running rule analysis..."):
            rule_result = analyze(BASE,sf)

        with st.spinner("🤖 Scoring with ML model..."):
            try:
                ml_result = predict_scan(sf, BASE)
                if ml_result.get("error"):
                    st.warning(f"⚠️ ML scoring skipped: {ml_result['error']}")
                else:
                    update_ml_results(sf, ml_result, rule_result)
            except Exception as ml_e:
                st.warning(f"⚠️ ML scoring failed: {ml_e}")

        st.success(f"✅ Done: {os.path.basename(sf)}")
        return sf
    except ImportError as e:
        st.error(f"❌ Module not found: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Scan failed: {e}")
        return None

# ════════════════════════════════
# SIDEBAR
# ════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='padding:28px 20px 20px;border-bottom:1px solid #1c3a5c;'>
        <div style='font-size:1.5em;font-weight:800;color:#f2f5fb;letter-spacing:-0.5px;font-family:"Inter",sans-serif;'>
            🛡️ DroidSentinel
        </div>
        <div style='font-size:0.78em;color:#3f6b96;letter-spacing:3px;text-transform:uppercase;margin-top:5px;font-family:"Inter",sans-serif;'>
            Anti-Forensics Detection
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    if st.button("⚡  Run New Scan", key="run_scan_btn", use_container_width=True):
        r = run_scan()
        if r: st.rerun()

    st.markdown("""
    <div style='font-size:0.78em;color:#3f6b96;letter-spacing:2.5px;text-transform:uppercase;
                margin:22px 0 10px;font-family:"Inter",sans-serif;'>
        Scan History
    </div>
    """, unsafe_allow_html=True)

    scans = all_scans()
    names = [s["name"] for s in scans if s["ok"]]

    st.markdown("""
    <div style='font-size:0.72em;color:#3f6b96;letter-spacing:2px;text-transform:uppercase;
                margin:14px 0 6px;font-family:"Inter",sans-serif;'>
        Filter by Date
    </div>
    """, unsafe_allow_html=True)

    date_filter = st.text_input(
        "date_filter", placeholder="e.g. 20260622",
        label_visibility="collapsed", key="scan_date_filter"
    )

    if date_filter.strip():
        filtered_names = [n for n in names if date_filter.strip() in n]
    else:
        filtered_names = names

    st.markdown(
        f"<div style='font-size:0.8em;color:#3f6b96;margin:6px 0 8px;font-family:\"Inter\",sans-serif;'>"
        f"Showing {len(filtered_names)} of {len(names)} scans</div>",
        unsafe_allow_html=True
    )

    sel = st.selectbox("scan", filtered_names, label_visibility="collapsed") if filtered_names else None

    if not names:
        st.markdown("<div style='font-size:0.95em;color:#5d87b3;padding:8px 0;'>No scans found. Click Run New Scan.</div>", unsafe_allow_html=True)
    elif not filtered_names:
        st.markdown("<div style='font-size:0.95em;color:#5d87b3;padding:8px 0;'>No scans match that date filter.</div>", unsafe_allow_html=True)

    ml_data = load_ml()
    if ml_data:
        acc   = ml_data.get("accuracy",0)
        total = ml_data.get("total_samples",0)
        st.markdown(f"""
        <div style='margin-top:28px;padding-top:20px;border-top:1px solid #1c3a5c;'>
            <div style='font-size:0.78em;color:#3f6b96;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:14px;font-family:"Inter",sans-serif;'>ML Model</div>
            <div style='font-size:0.95em;color:#7295bb;line-height:2.2;font-family:"Inter",sans-serif;'>
                Algorithm<br><span style='color:#cfe0f5;font-family:"JetBrains Mono",monospace;'>Isolation Forest</span><br>
                Accuracy<br><span style='color:#22b6ff;font-weight:700;font-size:1.15em;font-family:"JetBrains Mono",monospace;'>{acc}%</span><br>
                Samples<br><span style='color:#cfe0f5;font-family:"JetBrains Mono",monospace;'>{total} total</span>
            </div>
        </div>
        """, unsafe_allow_html=True)



# ── No scan selected ──
if not sel:
    st.markdown("""
    <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;height:70vh;text-align:center;'>
        <div style='font-size:5em;'>🛡️</div>
        <div style='font-size:1.8em;font-weight:800;color:#f2f5fb;margin-top:16px;font-family:"Inter",sans-serif;'>DroidSentinel</div>
        <div style='font-size:1.1em;color:#5d87b3;margin-top:10px;font-family:"Inter",sans-serif;'>Select a scan from the sidebar or click ⚡ Run New Scan</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Load data ──
sp      = os.path.join(SCANS,sel)
res     = load_r(sp)
summ    = load_s(sp)
ml_data = load_ml()

if not res:
    st.error(f"No results found for scan: {sel}")
    st.stop()

pct     = res.get("confidence_pct",0)
verdict = res.get("verdict","")
rules   = res.get("rules",[])
fired   = [r for r in rules if r.get("fired")]
clear   = [r for r in rules if not r.get("fired")]
color   = tcolor(pct)
devinfo = summ.get("device_info",{}) if summ else {}

ml_label = "—"
ml_score = None
if ml_data:
    for vr in ml_data.get("validation_results",[]):
        if vr.get("scan")==sel:
            ml_label = vr.get("predicted","—").upper()
            ml_score = round(vr.get("score",0),4)
            break

verdict_clean = verdict.replace("🚨","").replace("⚠️","").replace("🔎","").replace("✅","").strip()
emoji = ("🚨" if "STRONGLY" in verdict else "⚠️" if "SUSPICIOUS" in verdict
         else "🔎" if "MINOR" in verdict else "✅")

# ── Page header ──
st.markdown(f"""
<div style='display:flex;align-items:flex-start;justify-content:space-between;
            padding:18px 0 20px;border-bottom:1px solid #1c3a5c;margin-bottom:24px;'>
    <div>
        <div style='font-size:0.78em;color:#3f6b96;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px;font-family:"Inter",sans-serif;'>Active Scan</div>
        <div style='font-size:1.4em;font-weight:800;color:#f2f5fb;font-family:"JetBrains Mono",monospace;'>{sel}</div>
        <div style='font-size:1em;color:#5d87b3;margin-top:5px;font-family:"Inter",sans-serif;'>
            {devinfo.get("model","—")} &nbsp;·&nbsp; Android {devinfo.get("android_version","?")} &nbsp;·&nbsp; {devinfo.get("scan_time",res.get("analysis_time","—"))}
        </div>
    </div>
    <div style='text-align:right;'>
        <div style='font-size:0.78em;color:#3f6b96;letter-spacing:3px;text-transform:uppercase;margin-bottom:5px;font-family:"Inter",sans-serif;'>Rules Fired</div>
        <div style='font-size:3em;font-weight:900;color:{color};font-family:"JetBrains Mono",monospace;line-height:1;'>{len(fired)}/{len(rules)}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Download Forensic Report (PDF) ──
if generate_report is not None:
    try:
        ml_label_for_report = ml_label if ml_label != "—" else "UNKNOWN"
        pdf_bytes = generate_report(
            scan_name=sel,
            res=res,
            summ=summ,
            ml_label=ml_label_for_report,
            ml_score=ml_score,
            output_path=None  # returns bytes for in-memory download
        )
        dl_col, _ = st.columns([1, 4])
        with dl_col:
            st.download_button(
                label="📄  Download Forensic Report (PDF)",
                data=pdf_bytes,
                file_name=f"DroidSentinel_Report_{sel}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    except Exception as e:
        st.warning(f"⚠️ Could not generate PDF report: {e}")
else:
    st.info("📄 PDF report generation unavailable — report_generator.py not found.")

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

# ── Tabs ──
t1,t2,t3,t4,t5 = st.tabs(["Overview","Rule Engine","ML Analysis","Artifact Explorer","Scan History"])

# ════════════════════════════════
# TAB 1 — OVERVIEW
# ════════════════════════════════
with t1:
    c1,c2,c3 = st.columns([1.1,1.5,1])

    with c1:
        st.markdown("""<div style='background:#0a1626;border:1px solid #1c3a5c;border-radius:10px;padding:16px 12px 8px;'>
            <div class='ds-label' style='text-align:center;'>Threat Confidence</div>""", unsafe_allow_html=True)
        st.plotly_chart(gauge(pct,color), use_container_width=True, config={"displayModeBar":False})


    with c2:
        cc = tcard(pct)
        st.markdown(f"""
        <div class='{cc}' style='min-height:310px;display:flex;flex-direction:column;justify-content:center;'>
            <div style='font-size:3em;margin-bottom:12px;'>{emoji}</div>
            <div style='font-size:1.25em;font-weight:700;color:#f2f5fb;line-height:1.4;margin-bottom:12px;font-family:"Inter",sans-serif;'>{verdict_clean}</div>
            <div style='font-size:0.95em;color:#7295bb;font-family:"JetBrains Mono",monospace;margin-bottom:14px;'>
                Score: <span style='color:#dbe4f5;'>{res.get("total_score",0)}</span> / {res.get("max_score",285)} pts
            </div>
            <div style='height:6px;border-radius:3px;background:#1c3a5c;overflow:hidden;'>
                <div style='height:100%;width:{pct}%;background:{color};border-radius:3px;'></div>
            </div>
            <div style='font-size:0.95em;color:{color};margin-top:8px;font-weight:700;font-family:"JetBrains Mono",monospace;'>{pct}%</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        ml_c = "#ff4444" if ml_label=="ANOMALY" else "#21d35a" if ml_label=="NORMAL" else "#5d87b3"
        st.markdown(f"""
        <div class='ds-card' style='margin-bottom:12px;padding:16px 18px;'>
            <div class='ds-label'>ML Verdict</div>
            <div style='font-size:1.8em;font-weight:800;color:{ml_c};font-family:"JetBrains Mono",monospace;margin-top:4px;'>{ml_label}</div>
            <div style='font-size:0.9em;color:#5d87b3;margin-top:4px;font-family:"JetBrains Mono",monospace;'>Score: {ml_score if ml_score is not None else "—"}</div>
        </div>
        <div class='ds-card' style='margin-bottom:12px;padding:16px 18px;'>
            <div class='ds-label'>Rules Triggered</div>
            <div style='font-size:1.8em;font-weight:800;color:{color};font-family:"JetBrains Mono",monospace;margin-top:4px;'>{len(fired)}</div>
            <div style='font-size:0.9em;color:#5d87b3;margin-top:4px;font-family:"Inter",sans-serif;'>out of {len(rules)} rules</div>
        </div>
        <div class='ds-card' style='padding:16px 18px;'>
            <div class='ds-label'>Threat Level</div>
            <div style='font-size:1.8em;font-weight:800;color:{color};font-family:"JetBrains Mono",monospace;margin-top:4px;'>{res.get("overall_confidence","NONE")}</div>
            <div style='font-size:0.9em;color:#5d87b3;margin-top:4px;font-family:"Inter",sans-serif;'>confidence rating</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div class='ds-label' style='margin:28px 0 14px;'>Collected Artifacts</div>", unsafe_allow_html=True)
    arts = summ.get("system_artifacts",{}) if summ else {}
    art_list = [
        ("packages_xml","packages.xml","App registry"),
        ("usagestats","usagestats/","Usage history"),
        ("notification_log","notification_log.db","Ghost traces"),
        ("dropbox","dropbox/","System logs"),
        ("netstats","netstats/","Network stats"),
        ("runtime_permissions","runtime-perms.xml","App permissions"),
    ]
    cols = st.columns(3)
    for i,(k,lbl,desc) in enumerate(art_list):
        a  = arts.get(k,{})
        sz = a.get("size",0)
        ok = a.get("success",False)
        with cols[i%3]:
            st.markdown(f"""
            <div class='ds-card' style='padding:14px 16px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;'>
                    <div style='font-size:0.95em;font-family:"JetBrains Mono",monospace;color:#8fb0d6;'>{lbl}</div>
                    <div style='font-size:1.05em;color:{"#21d35a" if ok else "#ff4444"};font-weight:700;'>{"✓" if ok else "✗"}</div>
                </div>
                <div style='font-size:0.85em;color:#5d87b3;font-family:"Inter",sans-serif;'>{desc}</div>
                <div style='font-size:1.0em;font-weight:600;color:{"#22b6ff" if ok else "#4a5d72"};margin-top:8px;font-family:"JetBrains Mono",monospace;'>
                    {f"{sz:,} bytes" if ok else "not found"}
                </div>
            </div>
            """, unsafe_allow_html=True)

# ════════════════════════════════
# TAB 2 — RULE ENGINE
# ════════════════════════════════
with t2:
    if fired:
        st.markdown(f"""
        <div style='font-size:0.9em;color:#ff4444;letter-spacing:2px;text-transform:uppercase;
                    font-weight:700;margin-bottom:20px;font-family:"Inter",sans-serif;'>
            ● {len(fired)} Rule{"s" if len(fired)>1 else ""} Fired
        </div>
        """, unsafe_allow_html=True)
        for rule in fired:
            ev_html = "".join(f"<div class='ds-ev'>▸ {e}</div>" for e in rule.get("evidence",[]))
            st.markdown(f"""
            <div class='ds-rule-fired'>
                <div class='ds-rule-fired-header'>
                    <div style='flex:1;'>
                        <div class='ds-rule-id'>● {rule["rule_id"]}</div>
                        <div class='ds-rule-name'>{rule["rule_name"]}</div>
                        <div class='ds-rule-artifact'>📁 {rule["artifact"]}</div>
                    </div>
                    <div style='text-align:right;flex-shrink:0;margin-left:20px;'>
                        <div class='ds-rule-pts'>{rule["score"]}/{rule["weight"]} pts</div>
                        <div style='margin-top:6px;'>{badge(rule.get("confidence","NONE"))}</div>
                    </div>
                </div>
                {ev_html}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='ds-card-green' style='text-align:center;padding:48px;'>
            <div style='font-size:2.5em;'>✅</div>
            <div style='font-size:1.3em;font-weight:700;color:#21d35a;margin-top:12px;font-family:"Inter",sans-serif;'>No rules fired — device appears clean</div>
        </div>
        """, unsafe_allow_html=True)

    if clear:
        st.markdown("<div class='ds-label' style='margin:36px 0 16px;'>Clear Rules — No Evidence</div>", unsafe_allow_html=True)
        cols2 = st.columns(2)
        for i,rule in enumerate(clear):
            ev0 = rule.get("evidence",["No evidence"])[0]
            ev0 = ev0[:90]+"..." if len(ev0)>90 else ev0
            with cols2[i%2]:
                st.markdown(f"""
                <div class='ds-rule-clear'>
                    <div class='ds-rule-clear-id'>○ {rule["rule_id"]}</div>
                    <div class='ds-rule-clear-name'>{rule["rule_name"]}</div>
                    <div class='ds-rule-clear-ev'>{ev0}</div>
                </div>
                """, unsafe_allow_html=True)

# ════════════════════════════════
# TAB 3 — ML ANALYSIS
# ════════════════════════════════
with t3:
    if not ml_data:
        st.markdown("<div class='ds-card' style='color:#ffb020;'>No ML results found. Run ml_detector.py first.</div>", unsafe_allow_html=True)
    else:
        cm1,cm2 = st.columns([1,1.6])

        with cm1:
            ml_c2 = "#ff4444" if ml_label=="ANOMALY" else "#21d35a" if ml_label=="NORMAL" else "#5d87b3"
            acc   = ml_data.get("accuracy",0)

            st.markdown(f"""
            <div class='ds-card' style='text-align:center;padding:40px 24px;margin-bottom:14px;'>
                <div class='ds-label'>Prediction — This Scan</div>
                <div style='font-size:2.8em;font-weight:900;color:{ml_c2};font-family:"JetBrains Mono",monospace;margin:18px 0 12px;letter-spacing:2px;'>
                    {ml_label}
                </div>
                <div style='font-size:1em;color:#7295bb;font-family:"JetBrains Mono",monospace;'>
                    Score: <span style='color:#cfe0f5;'>{ml_score if ml_score is not None else "—"}</span>
                </div>
                <div style='font-size:0.85em;color:#5d87b3;margin-top:5px;font-family:"Inter",sans-serif;'>more negative = more anomalous</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class='ds-card' style='padding:20px 22px;'>
                <div class='ds-label'>Model Stats</div>
                <div style='margin-top:12px;'>
                    <div style='display:flex;justify-content:space-between;font-size:1em;color:#7295bb;margin-bottom:6px;font-family:"Inter",sans-serif;'>
                        <span>Accuracy</span>
                        <span style='color:#22b6ff;font-weight:700;font-family:"JetBrains Mono",monospace;'>{acc}%</span>
                    </div>
                    <div style='height:6px;border-radius:3px;background:#15293f;overflow:hidden;'>
                        <div style='height:100%;width:{acc}%;background:linear-gradient(90deg,#0046a8,#22b6ff);border-radius:3px;'></div>
                    </div>
                </div>
                <div style='margin-top:20px;font-size:0.98em;color:#7295bb;line-height:2.3;font-family:"Inter",sans-serif;'>
                    Algorithm<br><span style='color:#dbe4f5;font-family:"JetBrains Mono",monospace;'>Isolation Forest</span><br>
                    Training samples<br><span style='color:#dbe4f5;font-family:"JetBrains Mono",monospace;'>{ml_data.get("normal_samples",0)} normal</span><br>
                    Total dataset<br><span style='color:#dbe4f5;font-family:"JetBrains Mono",monospace;'>{ml_data.get("total_samples",0)} samples</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with cm2:
            import re as _re
            LIVE_SCAN_RE = _re.compile(r"^scan_\d{8}_\d{6}$")

            all_vr = ml_data.get("validation_results",[])
            live_vr = [r for r in all_vr if LIVE_SCAN_RE.match(r.get("scan",""))]

            st.markdown("<div class='ds-label' style='margin-bottom:8px;'>Scan Predictions</div>", unsafe_allow_html=True)

            view_choice = st.radio(
                "view",
                options=["Selected Scan", "My Scans Only", "All (incl. Training Data)"],
                index=0,
                horizontal=True,
                label_visibility="collapsed",
                key="ml_predictions_view_toggle"
            )

            if view_choice == "Selected Scan":
                vr_list = [r for r in all_vr if r.get("scan") == sel]
            elif view_choice == "My Scans Only":
                vr_list = live_vr
            else:
                vr_list = all_vr

            if view_choice == "Selected Scan" and not vr_list:
                st.markdown(
                    f"<div style='font-size:0.92em;color:#5d87b3;padding:10px 0;font-family:\"Inter\",sans-serif;'>"
                    f"No ML prediction found for <b>{sel}</b> — this scan may not have been "
                    f"ML-scored yet, or switch to \"All\" to browse other scans.</div>",
                    unsafe_allow_html=True
                )
            elif view_choice == "My Scans Only" and not vr_list:
                st.markdown(
                    "<div style='font-size:0.92em;color:#5d87b3;padding:10px 0;font-family:\"Inter\",sans-serif;'>"
                    "No live dashboard scans yet — click \"Run New Scan\" in the sidebar, "
                    "or switch to \"All\" to see training/synthetic data.</div>",
                    unsafe_allow_html=True
                )

            st.markdown(f"""
            <div style='display:flex;padding:8px 14px 10px;border-bottom:1px solid #1c3a5c;margin-bottom:4px;'>
                <span style='flex:2.2;font-size:0.85em;color:#3f6b96;font-family:"JetBrains Mono",monospace;letter-spacing:1px;'>SCAN</span>
                <span style='flex:0.8;font-size:0.85em;color:#3f6b96;font-family:"JetBrains Mono",monospace;letter-spacing:1px;text-align:center;'>ACTUAL</span>
                <span style='flex:0.8;font-size:0.85em;color:#3f6b96;font-family:"JetBrains Mono",monospace;letter-spacing:1px;text-align:center;'>PRED</span>
                <span style='flex:0.8;font-size:0.85em;color:#3f6b96;font-family:"JetBrains Mono",monospace;letter-spacing:1px;text-align:center;'>SCORE</span>
                <span style='width:22px;'></span>
            </div>
            """, unsafe_allow_html=True)

            for item in vr_list:
                actual    = item.get("actual","").upper()
                predicted = item.get("predicted","").upper()
                correct   = item.get("correct",False)
                sv        = round(item.get("score",0),4)
                sn        = item.get("scan","")
                is_cur    = sn==sel
                pc  = "#ff4444" if predicted=="ANOMALY" else "#21d35a"
                if correct is None:
                    # Live scan with no ground-truth label yet
                    mc, mi = "#5d87b3", "–"
                else:
                    mc  = "#21d35a" if correct else "#ff4444"
                    mi  = "✓" if correct else "✗"
                bg  = "background:#0a1626;" if is_cur else "background:#070f1c;"
                bo  = "border:1px solid #22b6ff;border-radius:6px;" if is_cur else "border:1px solid #15243a;border-radius:6px;"
                nc  = "#22b6ff" if is_cur else "#7295bb"
                mk  = " ◄" if is_cur else ""

                st.markdown(f"""
                <div style='display:flex;align-items:center;padding:8px 14px;margin-bottom:2px;{bg}{bo}'>
                    <div style='flex:2.2;font-size:0.95em;font-family:"JetBrains Mono",monospace;color:{nc};overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>
                        {sn[:26]}{"…" if len(sn)>26 else ""}{mk}
                    </div>
                    <div style='flex:0.8;font-size:0.95em;color:#7295bb;font-family:"JetBrains Mono",monospace;text-align:center;'>{actual[:3]}</div>
                    <div style='flex:0.8;font-size:0.95em;font-weight:700;color:{pc};font-family:"JetBrains Mono",monospace;text-align:center;'>{predicted[:3]}</div>
                    <div style='flex:0.8;font-size:0.92em;color:#5d87b3;font-family:"JetBrains Mono",monospace;text-align:center;'>{sv}</div>
                    <div style='width:22px;font-size:1.05em;color:{mc};font-weight:700;text-align:right;'>{mi}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("""
            <div style='display:flex;gap:20px;margin-top:12px;padding:0 14px;font-size:0.9em;color:#5d87b3;font-family:"Inter",sans-serif;'>
                <span>ACT = Actual &nbsp;|&nbsp; PRED = Predicted</span>
                <span style='color:#21d35a;font-weight:600;'>✓ Correct</span>
                <span style='color:#ff4444;font-weight:600;'>✗ Wrong</span>
            </div>
            """, unsafe_allow_html=True)

# ════════════════════════════════
# TAB 4 — ARTIFACT EXPLORER
# ════════════════════════════════
with t4:
    st.markdown("<div class='ds-label' style='margin-bottom:16px;'>Artifact Size — Baseline vs Current</div>", unsafe_allow_html=True)

    if summ:
        cur_arts = summ.get("system_artifacts",{})
        base_summ_path = os.path.join(BASE,"scan_summary.json")
        base_arts = {}
        if os.path.exists(base_summ_path):
            base_arts = json.load(open(base_summ_path)).get("system_artifacts",{})

        art_keys = [
            ("packages_xml","packages.xml"),
            ("usagestats","usagestats/"),
            ("notification_log","notification_log.db"),
            ("dropbox","dropbox/"),
            ("netstats","netstats/"),
        ]

        ca1,ca2 = st.columns(2)

        with ca1:
            st.markdown("<div class='ds-label' style='margin-bottom:10px;'>Size Comparison</div>", unsafe_allow_html=True)
            labels = [l for _,l in art_keys]
            bsz    = [base_arts.get(k,{}).get("size",0) for k,_ in art_keys]
            csz    = [cur_arts.get(k,{}).get("size",0)  for k,_ in art_keys]
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Baseline",x=labels,y=bsz,marker_color="#2c5a89",
                                 hovertemplate="%{x}<br>%{y:,} bytes<extra>Baseline</extra>"))
            fig.add_trace(go.Bar(name="Current",x=labels,y=csz,marker_color="#22b6ff",
                                 hovertemplate="%{x}<br>%{y:,} bytes<extra>Current</extra>"))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",barmode="group",
                font={"family":"JetBrains Mono","color":"#7295bb","size":13},
                xaxis=dict(tickfont=dict(size=12,color="#7295bb"),gridcolor="rgba(0,0,0,0)",linecolor="#1c3a5c"),
                yaxis=dict(gridcolor="#15243a",tickfont=dict(size=12,color="#7295bb")),
                legend=dict(font=dict(color="#9bbade",size=13),bgcolor="rgba(0,0,0,0)",orientation="h",y=1.1),
                height=300,margin=dict(l=10,r=10,t=30,b=60),bargap=0.2
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        with ca2:
            st.markdown("<div class='ds-label' style='margin-bottom:10px;'>Size Diff</div>", unsafe_allow_html=True)
            for k,lbl in art_keys:
                b    = base_arts.get(k,{}).get("size",0)
                c    = cur_arts.get(k,{}).get("size",0)
                d    = c-b
                pct2 = round(d/b*100,1) if b>0 else 0
                dc   = "#ff4444" if d>0 else "#21d35a" if d<0 else "#5d87b3"
                arr  = "▲" if d>0 else "▼" if d<0 else "●"
                sign = f"+{d:,}" if d>0 else f"{d:,}"
                st.markdown(f"""
                <div class='ds-card' style='padding:12px 16px;margin-bottom:8px;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <div style='font-size:0.98em;font-family:"JetBrains Mono",monospace;color:#8fb0d6;'>{lbl}</div>
                        <div style='font-size:1em;font-weight:700;color:{dc};font-family:"JetBrains Mono",monospace;'>
                            {arr} {sign} B <span style='color:#5d87b3;font-weight:400;font-size:0.9em;'>({pct2:+.1f}%)</span>
                        </div>
                    </div>
                    <div style='font-size:0.88em;color:#5d87b3;margin-top:4px;font-family:"JetBrains Mono",monospace;'>{b:,} → {c:,} bytes</div>
                </div>
                """, unsafe_allow_html=True)

        # Notification log
        st.markdown("<div class='ds-label' style='margin:24px 0 12px;'>Notification Log — Wiping App Entries</div>", unsafe_allow_html=True)
        ndb = os.path.join(sp,"system","notification_log.db")
        if os.path.exists(ndb):
            try:
                conn = sqlite3.connect(ndb)
                rows = conn.execute("SELECT pkg, event_time_ms FROM log ORDER BY event_time_ms DESC LIMIT 50").fetchall()
                conn.close()
                wrows = [r for r in rows if any(x in r[0].lower() for x in ["ishredder","shreddit","secureeraser","eraser","shred"])]
                if wrows:
                    for pkg,ts in wrows[:15]:
                        try: t = datetime.fromtimestamp(ts/1000).strftime("%Y-%m-%d %H:%M:%S")
                        except: t = str(ts)
                        st.markdown(f"""
                        <div style='background:#0a1320;border-left:2px solid #14507a;padding:9px 16px;
                                    margin-bottom:4px;border-radius:0 6px 6px 0;'>
                            <span style='font-size:0.95em;font-family:"JetBrains Mono",monospace;color:#7fb0d8;'>📱 {pkg}</span>
                            <span style='font-size:0.9em;color:#5d87b3;margin-left:12px;font-family:"JetBrains Mono",monospace;'>{t}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("<div class='ds-card' style='color:#5d87b3;font-size:1em;'>No wiping app entries found</div>", unsafe_allow_html=True)
            except Exception as e:
                st.markdown(f"<div class='ds-card' style='color:#ff4444;'>DB Error: {e}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='ds-card' style='color:#5d87b3;font-size:1em;'>notification_log.db not collected in this scan</div>", unsafe_allow_html=True)

        # Dropbox count
        st.markdown("<div class='ds-label' style='margin:24px 0 12px;'>Dropbox File Count</div>", unsafe_allow_html=True)
        def cnt_drop(folder):
            p = os.path.join(folder,"system","dropbox")
            if not os.path.exists(p): return 0
            return sum(len(fs) for _,_,fs in os.walk(p))
        bd = cnt_drop(BASE); cd = cnt_drop(sp); dd = cd-bd
        dc1,dc2,dc3 = st.columns(3)
        for col,lbl,val,clr in [
            (dc1,"Baseline",bd,"#7295bb"),
            (dc2,"Current",cd,"#22b6ff"),
            (dc3,"Difference",f"{'+' if dd>0 else ''}{dd}","#ff4444" if dd>0 else "#21d35a"),
        ]:
            with col:
                st.markdown(f"""
                <div class='ds-card' style='text-align:center;padding:20px;'>
                    <div class='ds-label'>{lbl}</div>
                    <div style='font-size:2.2em;font-weight:800;color:{clr};font-family:"JetBrains Mono",monospace;margin-top:8px;'>{val}</div>
                    <div style='font-size:0.9em;color:#5d87b3;margin-top:4px;font-family:"Inter",sans-serif;'>files</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown("<div class='ds-card' style='color:#5d87b3;'>No scan summary available.</div>", unsafe_allow_html=True)

# ════════════════════════════════
# TAB 5 — SCAN HISTORY
# ════════════════════════════════
with t5:
    hist = []
    for s in scans:
        if not s["ok"]: continue
        r = load_r(s["path"])
        if r:
            hist.append({
                "scan":  s["name"],
                "fired": r.get("fired_count",0),
                "pct":   r.get("confidence_pct",0),
                "verdict":r.get("overall_confidence","NONE"),
                "score": r.get("total_score",0),
            })

    if not hist:
        st.markdown("<div class='ds-card' style='color:#5d87b3;text-align:center;padding:48px;'>No scan history found.</div>", unsafe_allow_html=True)
        st.stop()

    ch1,ch2 = st.columns([1.6,1])

    with ch1:
        st.markdown("<div class='ds-label' style='margin-bottom:12px;'>Threat Confidence — All Scans</div>", unsafe_allow_html=True)
        df         = pd.DataFrame(hist)
        bar_colors = [tcolor(p) for p in df["pct"]]
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df["scan"], y=df["pct"],
            marker_color=bar_colors, marker_line_width=0,
            hovertemplate="<b>%{x}</b><br>Confidence: %{y:.1f}%<extra></extra>"
        ))
        if sel in df["scan"].values:
            idx = df[df["scan"]==sel].index[0]
            fig2.add_shape(type="rect",
                x0=idx-0.4,x1=idx+0.4,y0=0,y1=max(df.iloc[idx]["pct"],2),
                line=dict(color="#22b6ff",width=2),fillcolor="rgba(34,182,255,0.08)")
        fig2.add_hline(y=40,line_dash="dot",line_color="#ffb020",opacity=0.7,
                       annotation_text="MEDIUM",annotation_font_color="#ffb020",annotation_font_size=11)
        fig2.add_hline(y=70,line_dash="dot",line_color="#ff4444",opacity=0.7,
                       annotation_text="HIGH",annotation_font_color="#ff4444",annotation_font_size=11)
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
            font={"family":"JetBrains Mono","color":"#5d87b3","size":12},
            xaxis=dict(tickangle=45,tickfont=dict(size=10,color="#5d87b3"),gridcolor="rgba(0,0,0,0)",linecolor="#1c3a5c"),
            yaxis=dict(range=[0,100],gridcolor="#15243a",tickfont=dict(size=11,color="#5d87b3"),
                       title=dict(text="Confidence %",font=dict(size=12,color="#5d87b3"))),
            height=320,margin=dict(l=10,r=10,t=10,b=90),showlegend=False,bargap=0.3
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})

        # Summary stats
        tot  = len(hist)
        susp = sum(1 for h in hist if h["pct"]>=15)
        cln  = tot-susp
        avg  = round(sum(h["pct"] for h in hist)/tot,1)
        sc1,sc2,sc3,sc4 = st.columns(4)
        for col,lbl,val,clr in [
            (sc1,"Total Scans",tot,"#f2f5fb"),
            (sc2,"Suspicious",susp,"#ff4444"),
            (sc3,"Clean",cln,"#21d35a"),
            (sc4,"Avg Confidence",f"{avg}%","#22b6ff"),
        ]:
            with col:
                st.markdown(f"""
                <div class='ds-card' style='text-align:center;padding:16px 12px;'>
                    <div class='ds-label'>{lbl}</div>
                    <div style='font-size:1.9em;font-weight:800;color:{clr};font-family:"JetBrains Mono",monospace;margin-top:6px;'>{val}</div>
                </div>
                """, unsafe_allow_html=True)

    with ch2:
        st.markdown("<div class='ds-label' style='margin-bottom:12px;'>Timeline</div>", unsafe_allow_html=True)
        for h in hist:
            is_cur = h["scan"]==sel
            dc     = dot_color(h["pct"])
            bg     = "background:#0a1626;" if is_cur else "background:#070f1c;"
            bo     = "border:1px solid #22b6ff;" if is_cur else "border:1px solid #15243a;"
            nc     = "#22b6ff" if is_cur else "#7295bb"
            st.markdown(f"""
            <div style='display:flex;align-items:center;padding:10px 14px;margin-bottom:3px;
                        border-radius:8px;{bg}{bo}'>
                <div style='width:9px;height:9px;border-radius:50%;background:{dc};flex-shrink:0;margin-right:12px;'></div>
                <div style='flex:1;min-width:0;'>
                    <div style='font-size:0.95em;font-family:"JetBrains Mono",monospace;color:{nc};
                                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>
                        {h["scan"]}{" ◄" if is_cur else ""}
                    </div>
                    <div style='font-size:0.85em;color:#5d87b3;margin-top:2px;font-family:"Inter",sans-serif;'>
                        {h["fired"]} rules · {h["verdict"]}
                    </div>
                </div>
                <div style='font-size:1.05em;font-weight:700;color:{dc};font-family:"JetBrains Mono",monospace;
                            margin-left:10px;flex-shrink:0;'>{h["pct"]}%</div>
            </div>
            """, unsafe_allow_html=True)
