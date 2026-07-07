import sqlite3
import struct
import hashlib
import pandas as pd
from datetime import datetime
import os


# ─────────────────────────────────────────────
# 1. CONNECT TO DATABASE
# ─────────────────────────────────────────────
def connect_db(db_path):
    if not os.path.exists(db_path):
        print(f"[!] Database not found: {db_path}")
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    print(f"[✓] Connected to database: {db_path}")
    return conn


# ─────────────────────────────────────────────
# 2. GET ACTIVE MESSAGES
# ─────────────────────────────────────────────
def get_active_messages(conn):
    try:
        # Detect column name — newer WhatsApp uses text_data, older uses data
        cursor = conn.execute("PRAGMA table_info(message)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'text_data' in columns:
            msg_col = 'text_data'
        elif 'data' in columns:
            msg_col = 'data'
        else:
            print("[!] Cannot find message text column")
            return []

        print(f"[✓] Using message column: {msg_col}")

        query = f"""
        SELECT
            m._id              AS msg_id,
            COALESCE(
                NULLIF(c.subject, ''),
                j.raw_string,
                CAST(m.chat_row_id AS TEXT)
            )                  AS sender,
            m.{msg_col}        AS message_text,
            m.timestamp        AS timestamp_ms,
            m.status           AS status,
            m.from_me          AS from_me,
            NULL               AS media_url,
            'active'           AS source
        FROM message m
        LEFT JOIN chat c ON m.chat_row_id = c._id
        LEFT JOIN jid j ON c.jid_row_id = j._id
        WHERE m.{msg_col} IS NOT NULL
        AND m.{msg_col} != ''
        AND m.message_type = 0
        ORDER BY m.timestamp ASC
        """
        rows = conn.execute(query).fetchall()
        print(f"[✓] Active messages found: {len(rows)}")
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[!] Error reading active messages: {e}")
        return []


# ─────────────────────────────────────────────
# 3. GET DELETED MESSAGE MARKERS
# ─────────────────────────────────────────────
def get_deleted_placeholders(conn):
    try:
        query = """
        SELECT
            m._id              AS msg_id,
            COALESCE(
                NULLIF(c.subject, ''),
                j.raw_string,
                CAST(m.chat_row_id AS TEXT)
            )                  AS sender,
            NULL               AS message_text,
            m.timestamp        AS timestamp_ms,
            m.status           AS status,
            m.from_me          AS from_me,
            NULL               AS media_url,
            'deleted_marker'   AS source
        FROM message m
        LEFT JOIN chat c ON m.chat_row_id = c._id
        LEFT JOIN jid j ON c.jid_row_id = j._id
        WHERE m.text_data IS NULL
        AND m.message_type = 0
        ORDER BY m.timestamp ASC
        """
        rows = conn.execute(query).fetchall()
        print(f"[✓] Deleted markers found: {len(rows)}")
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[!] Error reading deleted markers: {e}")
        return []
# ─────────────────────────────────────────────
# 4. RECOVER FROM WAL FILE
# ─────────────────────────────────────────────
def recover_from_wal(wal_path, page_size=4096):
    recovered = []

    if not os.path.exists(wal_path):
        print(f"[!] WAL file not found: {wal_path}")
        print("    Checkpoint may have already occurred.")
        return recovered

    print(f"[*] Reading WAL file: {wal_path}")

    try:
        with open(wal_path, 'rb') as f:
            # Read WAL header
            header = f.read(32)
            if len(header) < 32:
                print("[!] WAL file too small")
                return recovered

            frame_num = 0
            while True:
                # Read frame header
                frame_header = f.read(24)
                if len(frame_header) < 24:
                    break

                page_number = struct.unpack('>I', frame_header[0:4])[0]

                # Read page data
                page_data = f.read(page_size)
                if len(page_data) < page_size:
                    break

                # Extract all readable strings from page
                strings = extract_strings_from_page(page_data, min_len=4)
                for s in strings:
                    if is_likely_message(s):
                        recovered.append({
                            'msg_id':       None,
                            'sender':       'WAL recovered',
                            'message_text': s,
                            'timestamp_ms': None,
                            'status':       -1,
                            'from_me':      None,
                            'media_url':    None,
                            'source':       f'WAL frame {frame_num} page {page_number}'
                        })
                frame_num += 1

        print(f"[✓] WAL scan complete: {frame_num} frames, {len(recovered)} strings recovered")

    except Exception as e:
        print(f"[!] WAL reading error: {e}")

    return recovered


def extract_strings_from_page(page_bytes, min_len=4):
    strings = []
    current = []
    for byte in page_bytes:
        if 32 <= byte <= 126:
            current.append(chr(byte))
        else:
            if len(current) >= min_len:
                s = ''.join(current).strip()
                if s:
                    strings.append(s)
            current = []
    if len(current) >= min_len:
        s = ''.join(current).strip()
        if s:
            strings.append(s)
    return strings


def is_likely_message(text):
    # Skip obvious SQL and system keywords
    skip_keywords = [
        'CREATE', 'INSERT', 'SELECT *', 'UPDATE', 'DELETE FROM',
        'TABLE', 'INDEX', 'sqlite', 'INTEGER', 'VARCHAR',
        'BEGIN', 'COMMIT', 'ROLLBACK', 'PRAGMA', 'TRIGGER',
        'PRIMARY', 'FOREIGN', 'UNIQUE', 'DEFAULT',
        'participant_deviceg', 'receipt', 'ratchet',
        'axolotl', 'signal', 'cipher', 'proto',
        'media_', 'thumb', 'backup', 'migrate'
    ]
    text_upper = text.upper()
    for kw in skip_keywords:
        if kw.upper() in text_upper:
            return False

    # Must have at least 2 alphabetic characters
    alpha_count = sum(1 for c in text if c.isalpha())
    if alpha_count < 2:
        return False

    return True


# ─────────────────────────────────────────────
# 5. CHECK BACKUP FILES
# ─────────────────────────────────────────────
def find_backup_databases(folder="."):
    import glob
    pattern = os.path.join(folder, "msgstore-*.db")
    backups = sorted(glob.glob(pattern))
    print(f"[✓] Backup files found: {len(backups)}")
    return backups


def compare_backups_to_current(current_db_path, backup_paths):
    conn = connect_db(current_db_path)
    current = get_active_messages(conn)
    conn.close()
    current_ids = {m['msg_id'] for m in current}

    lost = []
    for bp in backup_paths:
        try:
            bconn = sqlite3.connect(bp)
            bconn.row_factory = sqlite3.Row
            backup_msgs = get_active_messages(bconn)
            bconn.close()
            for m in backup_msgs:
                if m['msg_id'] not in current_ids:
                    m['source'] = f'backup: {os.path.basename(bp)}'
                    lost.append(m)
        except Exception as e:
            print(f"[!] Could not read backup {bp}: {e}")

    print(f"[✓] Messages in backups missing from current DB: {len(lost)}")
    return lost


# ─────────────────────────────────────────────
# 6. EVIDENCE INTEGRITY (SHA-256 HASH)
# ─────────────────────────────────────────────
def compute_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def save_evidence_log(db_path, wal_path, output_path="evidence_log.txt"):
    db_hash  = compute_hash(db_path)
    wal_hash = compute_hash(wal_path) if os.path.exists(wal_path) else "WAL not found"
    now      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log = f"""
===================================================
  FORENSIC EVIDENCE LOG
===================================================
Acquisition Time : {now}
Examiner         : Student Forensic Tool v1.0
Tool             : WhatsApp Recovery Script

Database File    : {db_path}
SHA-256 Hash     : {db_hash}

WAL File         : {wal_path}
SHA-256 Hash     : {wal_hash}

NOTE: If the hash of msgstore.db changes after
this log was created, evidence may be tampered.
===================================================
"""
    with open(output_path, 'w') as f:
        f.write(log)

    print(f"[✓] Evidence log saved → {output_path}")
    return db_hash


# ─────────────────────────────────────────────
# 7. TIMESTAMP CONVERSION
# ─────────────────────────────────────────────
def ms_to_datetime(ms):
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(int(ms) / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return None


# ─────────────────────────────────────────────
# 8. BUILD TIMELINE
# ─────────────────────────────────────────────
def build_timeline(active, deleted, wal_recovered):
    all_msgs = active + deleted + wal_recovered
    if not all_msgs:
        print("[!] No messages found at all")
        return pd.DataFrame()
    df = pd.DataFrame(all_msgs)
    if 'timestamp_ms' in df.columns:
        df['datetime'] = df['timestamp_ms'].apply(ms_to_datetime)
    if 'timestamp_ms' in df.columns:
        df = df.sort_values('timestamp_ms', na_position='last')
    df = df.reset_index(drop=True)
    print(f"[✓] Timeline built: {len(df)} total entries")
    return df


# ─────────────────────────────────────────────
# 9. EXPORT CSV
# ─────────────────────────────────────────────
def export_csv(df, output="recovered_messages.csv"):
    df.to_csv(output, index=False, encoding='utf-8-sig')
    print(f"[✓] CSV exported → {output}")


# ─────────────────────────────────────────────
# 10. GENERATE HTML REPORT
# ─────────────────────────────────────────────
def generate_html_report(df, hash_val, output="forensic_report.html"):
    now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total   = len(df)
    active  = len(df[df['source'] == 'active'])
    deleted = len(df[df['source'] == 'deleted_marker'])
    wal_cnt = len(df[df['source'].str.startswith('WAL', na=False)])

    rows_html = ""
    for _, row in df.iterrows():
        source = str(row.get('source', ''))
        if source == 'active':
            color = '#1D9E75'
        elif 'WAL' in source:
            color = '#D85A30'
        elif 'backup' in source:
            color = '#185FA5'
        else:
            color = '#BA7517'

        msg_text = row.get('message_text', '')
        if msg_text and str(msg_text) != 'None':
            text = str(msg_text)[:300]
        else:
            text = '<i style="color:#888">— deleted, text not recoverable —</i>'

        direction = 'Me' if row.get('from_me') == 1 else 'Them'
        sender    = str(row.get('sender', ''))
        dt        = str(row.get('datetime', ''))

        rows_html += f"""
        <tr>
            <td>{dt}</td>
            <td>{sender}</td>
            <td>{direction}</td>
            <td>{text}</td>
            <td><span style="color:{color};font-weight:500">{source}</span></td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>WhatsApp Forensic Report</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 24px; color: #222; }}
  h1   {{ color: #0F6E56; }}
  .meta {{ background: #f5f5f5; padding: 12px 16px; border-radius: 8px; font-size: 13px; margin-bottom: 24px; }}
  .stats {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
  .stat  {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 12px 20px; text-align: center; min-width: 120px; }}
  .stat-num {{ font-size: 28px; font-weight: 600; }}
  .stat-lbl {{ font-size: 12px; color: #666; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th  {{ background: #0F6E56; color: #fff; padding: 10px 12px; text-align: left; }}
  td  {{ padding: 9px 12px; border-bottom: 1px solid #eee; vertical-align: top; word-break: break-word; }}
  tr:hover td {{ background: #f9f9f9; }}
  .legend {{ margin-bottom: 16px; font-size: 12px; }}
  .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }}
</style>
</head>
<body>
<h1>📱 WhatsApp Forensic Report</h1>
<div class="meta">
  <b>Generated:</b> {now} &nbsp;|&nbsp;
  <b>Tool:</b> WhatsApp Recovery Script v1.0 &nbsp;|&nbsp;
  <b>DB Hash (SHA-256):</b> <code>{hash_val[:32]}...</code>
</div>
<div class="stats">
  <div class="stat">
    <div class="stat-num" style="color:#1D9E75">{active}</div>
    <div class="stat-lbl">Active messages</div>
  </div>
  <div class="stat">
    <div class="stat-num" style="color:#BA7517">{deleted}</div>
    <div class="stat-lbl">Deleted markers</div>
  </div>
  <div class="stat">
    <div class="stat-num" style="color:#D85A30">{wal_cnt}</div>
    <div class="stat-lbl">WAL recovered</div>
  </div>
  <div class="stat">
    <div class="stat-num">{total}</div>
    <div class="stat-lbl">Total entries</div>
  </div>
</div>
<div class="legend">
  <span class="dot" style="background:#1D9E75"></span>Active &nbsp;
  <span class="dot" style="background:#BA7517"></span>Deleted marker &nbsp;
  <span class="dot" style="background:#D85A30"></span>WAL recovered &nbsp;
  <span class="dot" style="background:#185FA5"></span>Backup recovered
</div>
<table>
  <thead>
    <tr>
      <th>Date / Time</th>
      <th>Contact / Group</th>
      <th>Direction</th>
      <th>Message</th>
      <th>Source</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
</body>
</html>"""

    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[✓] HTML report saved → {output}")


# ─────────────────────────────────────────────
# MAIN — RUN EVERYTHING
# ─────────────────────────────────────────────
if __name__ == "__main__":


    DB_PATH  = r"D:\whatsapp_forensics\msgstore.db"
    WAL_PATH = r"D:\whatsapp_forensics\wal_file.db"

    print("\n====== WhatsApp Deleted Message Recovery ======\n")

    # Step 1 — Evidence hash
    hash_val = save_evidence_log(DB_PATH, WAL_PATH)

    # Step 2 — Extract messages
    conn    = connect_db(DB_PATH)
    active  = get_active_messages(conn)
    deleted = get_deleted_placeholders(conn)
    conn.close()

    # Step 3 — WAL recovery
    wal_msgs = recover_from_wal(WAL_PATH)

    # Step 4 — Check backups
    backups     = find_backup_databases(".")
    backup_msgs = compare_backups_to_current(DB_PATH, backups)

    # Step 5 — Build timeline
    df = build_timeline(active, deleted, wal_msgs + backup_msgs)

    # Step 6 — Export
    export_csv(df)
    generate_html_report(df, hash_val)

    print("\n====== Done! Open forensic_report.html in browser ======\n")