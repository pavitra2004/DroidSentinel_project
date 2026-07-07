import sqlite3
import struct
import os
import shutil

DB_PATH  = r"D:\whatsapp_forensics\msgstore.db"
WAL_PATH = r"D:\whatsapp_forensics\wal_file.db"
BACKUP   = r"D:\whatsapp_forensics\msgstore_backup.db"

PAGE_SIZE = 4096

# Step 1 — Backup original database
shutil.copy2(DB_PATH, BACKUP)
print(f"[✓] Backup created → {BACKUP}")

# Step 2 — Read real messages from database
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT m._id, m.text_data, m.timestamp, m.chat_row_id, m.from_me
    FROM message m
    WHERE m.text_data IS NOT NULL
    AND m.text_data != ''
    AND LENGTH(m.text_data) > 3
    AND m.from_me = 1
    ORDER BY m.timestamp DESC
    LIMIT 20
""").fetchall()

if not rows:
    print("[!] No messages found in database")
    conn.close()
    exit()

print(f"[✓] Found {len(rows)} recent messages")
print("\nRecent messages:")
for i, r in enumerate(rows[:10]):
    print(f"  [{i}] {r['text_data'][:50]}")

# Step 3 — Pick 3 most recent messages to simulate as deleted
to_delete     = rows[:3]
deleted_texts = [r['text_data'] for r in to_delete]
deleted_ids   = [r['_id'] for r in to_delete]

print(f"\n[*] Simulating deletion of these messages:")
for t in deleted_texts:
    print(f"  → '{t[:60]}'")

# Step 4 — Create WAL file
def create_wal_with_messages(messages, wal_path):
    with open(wal_path, 'wb') as f:

        # WAL file header — exactly 32 bytes (8 fields x 4 bytes)
        f.write(b'\x37\x7f\x06\x83')           # magic number      (4 bytes)
        f.write(struct.pack('>I', 3007000))     # file format       (4 bytes)
        f.write(struct.pack('>I', PAGE_SIZE))   # page size         (4 bytes)
        f.write(struct.pack('>I', 1))           # checkpoint seq    (4 bytes)
        f.write(struct.pack('>I', 12345))       # salt-1            (4 bytes)
        f.write(struct.pack('>I', 67890))       # salt-2            (4 bytes)
        f.write(struct.pack('>I', 0))           # checksum-1        (4 bytes)
        f.write(struct.pack('>I', 0))           # checksum-2        (4 bytes)
        # Total header = 32 bytes ✅

        for i, msg in enumerate(messages):
            page_num = i + 1

            # Frame header — exactly 24 bytes (6 fields x 4 bytes)
            f.write(struct.pack('>I', page_num))  # page number     (4 bytes)
            f.write(struct.pack('>I', page_num))  # commit size     (4 bytes)
            f.write(struct.pack('>I', 12345))     # salt-1          (4 bytes)
            f.write(struct.pack('>I', 67890))     # salt-2          (4 bytes)
            f.write(struct.pack('>I', 0))         # checksum-1      (4 bytes)
            f.write(struct.pack('>I', 0))         # checksum-2      (4 bytes)
            # Total frame header = 24 bytes ✅

            # Page data — exactly PAGE_SIZE bytes
            page = bytearray(PAGE_SIZE)
            page[0] = 0x0D  # leaf table b-tree page

            # Write message text at position 100
            msg_bytes = msg.encode('utf-8')
            for j, b in enumerate(msg_bytes):
                if 100 + j < PAGE_SIZE:
                    page[100 + j] = b

            f.write(bytes(page))
            # Total frame = 24 + 4096 = 4120 bytes ✅

    # Verify file size
    file_size = os.path.getsize(wal_path)
    expected  = 32 + (len(messages) * (24 + PAGE_SIZE))
    print(f"[✓] WAL file created with {len(messages)} frames → {wal_path}")
    print(f"[✓] WAL file size: {file_size} bytes (expected: {expected} bytes)")
    if file_size == expected:
        print(f"[✓] WAL file size is CORRECT!")
    else:
        print(f"[!] Difference: {expected - file_size} bytes")

create_wal_with_messages(deleted_texts, WAL_PATH)

# Step 5 — Remove deleted messages from main DB
conn.execute(f"""
    DELETE FROM message
    WHERE _id IN ({','.join(map(str, deleted_ids))})
""")
conn.commit()
conn.close()

print(f"[✓] Deleted {len(deleted_ids)} messages from main database")
print()
print("=" * 50)
print("SIMULATION COMPLETE!")
print("=" * 50)
print()
print("These messages were deleted from DB:")
for t in deleted_texts:
    print(f"  ❌ '{t[:60]}'")
print()
print("These messages are now in WAL file:")
for t in deleted_texts:
    print(f"  ✅ '{t[:60]}'")
print()
print("Now run: python recovery.py")
print("Then run: streamlit run app.py")
print()
print("To restore original DB run:")
print(f"  copy {BACKUP} {DB_PATH}")