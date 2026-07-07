import streamlit as st
import sqlite3
import pandas as pd
import os
import tempfile

from recovery import (
    connect_db, get_active_messages, get_deleted_placeholders,
    recover_from_wal, build_timeline, compute_hash,
    generate_html_report, export_csv
)

st.set_page_config(
    page_title="WhatsApp Forensic Recovery",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 WhatsApp Deleted Message Recovery Tool")
st.caption("Upload decrypted msgstore.db and WAL file to begin forensic analysis")

st.divider()

col1, col2 = st.columns(2)
with col1:
    db_file = st.file_uploader("📂 Upload msgstore.db", type=["db"])
with col2:
    wal_file = st.file_uploader("📂 Upload WAL file (wal_file.db)", type=["db", "wal"])

if db_file:
    # Create temp directory that persists during session
    tmpdir = tempfile.mkdtemp()
    db_path  = os.path.join(tmpdir, "msgstore.db")
    wal_path = os.path.join(tmpdir, "wal_file.db")

    # Save uploaded DB file
    with open(db_path, 'wb') as f:
        f.write(db_file.read())

    # Save uploaded WAL file if provided
    wal_uploaded = False
    if wal_file:
        with open(wal_path, 'wb') as f:
            f.write(wal_file.read())
        wal_uploaded = True

    # Show hash
    db_hash = compute_hash(db_path)
    st.success(f"✅ File received | SHA-256: `{db_hash[:40]}...`")

    st.divider()

    # Extract active and deleted messages
    conn    = connect_db(db_path)
    active  = get_active_messages(conn)
    deleted = get_deleted_placeholders(conn)
    conn.close()

    # WAL recovery
    wal_msgs = []
    if wal_uploaded:
        wal_msgs = recover_from_wal(wal_path)
        st.info(f"📂 WAL file processed: {len(wal_msgs)} strings recovered from {wal_path}")
    else:
        st.warning("⚠️ No WAL file uploaded — WAL recovery skipped")

    # Build timeline
    df = build_timeline(active, deleted, wal_msgs)

    # Stats
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ Active Messages",  len(active))
    c2.metric("🟡 Deleted Markers",  len(deleted))
    c3.metric("🔴 WAL Recovered",    len(wal_msgs))
    c4.metric("📊 Total Entries",    len(df))

    st.divider()

    if len(df) > 0:
        # Filter by source
        sources = df['source'].dropna().unique().tolist()
        selected = st.multiselect(
            "Filter by source:",
            options=sources,
            default=sources
        )
        filtered = df[df['source'].isin(selected)]

        # Show available columns only
        display_cols = ['datetime', 'sender', 'message_text', 'source']
        available_cols = [c for c in display_cols if c in filtered.columns]

        st.dataframe(
            filtered[available_cols],
            use_container_width=True,
            height=400
        )

        st.divider()

        # Downloads
        col_a, col_b = st.columns(2)
        with col_a:
            csv = filtered.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "⬇️ Download CSV",
                csv,
                "recovered_messages.csv",
                "text/csv"
            )
        with col_b:
            report_path = os.path.join(tmpdir, "forensic_report.html")
            generate_html_report(filtered, db_hash, report_path)
            with open(report_path, "rb") as f:
                st.download_button(
                    "⬇️ Download HTML Report",
                    f.read(),
                    "forensic_report.html",
                    "text/html"
                )
    else:
        st.warning("No messages found in the uploaded database.")

else:
    st.info("👆 Upload your decrypted msgstore.db file above to begin")