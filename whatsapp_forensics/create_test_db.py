import sqlite3
import os
import struct

# Delete old files
for f in ['msgstore.db', 'msgstore.db-wal']:
    if os.path.exists(f):
        os.remove(f)

# Create database
conn = sqlite3.connect('msgstore.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS message (
    _id INTEGER PRIMARY KEY,
    key_remote_jid TEXT,
    data TEXT,
    timestamp INTEGER,
    status INTEGER,
    from_me INTEGER,
    media_url TEXT
)''')

# Insert ALL messages with their original text first
messages = [
    (1,'919876543210@s.whatsapp.net','Hello how are you',1700000000000,0,1,None),
    (2,'919876543210@s.whatsapp.net','I am fine thank you',1700000100000,0,0,None),
    (3,'919876543210@s.whatsapp.net','Meet me tomorrow',1700000300000,0,1,None),
    (4,'918888888888@s.whatsapp.net','Project update ready',1700000500000,0,0,None),
    (5,'919876543210@s.whatsapp.net','See you at 5pm',1700000700000,0,1,None),
    (6,'919876543210@s.whatsapp.net','This message will be deleted',1700000200000,0,1,None),
    (7,'918888888888@s.whatsapp.net','This was also deleted by user',1700000600000,0,1,None),
    (8,'919876543210@s.whatsapp.net','Secret plan deleted',1700000800000,0,1,None),
]

c.executemany('INSERT INTO message VALUES (?,?,?,?,?,?,?)', messages)
conn.commit()

print('[✓] Step 1: All messages inserted with original text')

# Now simulate deletion — WhatsApp sets data=NULL and status=-1
deleted_ids = [6, 7, 8]
c.execute(f'''UPDATE message 
              SET data = NULL, status = -1 
              WHERE _id IN ({",".join(map(str, deleted_ids))})''')
conn.commit()

print('[✓] Step 2: Messages 6, 7, 8 deleted (text set to NULL)')
print('     → In real WhatsApp, original text would be in WAL file')
print('     → We will now create a fake WAL with the deleted text')

conn.close()

# Create a simple WAL file containing the deleted message texts
# This simulates what a real WhatsApp WAL file would contain
deleted_texts = [
    'This message will be deleted',
    'This was also deleted by user', 
    'Secret plan deleted'
]

wal_content = b''
# WAL file header (32 bytes)
wal_content += b'7\x7f\x06\x83'  # magic
wal_content += b'\x00\x00\x10\x00'  # page size 4096
wal_content += b'\x00\x00\x00\x01'  # checkpoint sequence
wal_content += b'\x00\x00\x00\x01'  # salt-1
wal_content += b'\x00\x00\x00\x01'  # salt-2
wal_content += b'\x00\x00\x00\x00'  # checksum-1
wal_content += b'\x00\x00\x00\x00'  # checksum-2
wal_content += b'\x00\x00\x00\x00'  # reserved

# Create one WAL frame per deleted message
for i, text in enumerate(deleted_texts):
    # Frame header (24 bytes)
    frame_header = struct.pack('>I', i+1)      # page number
    frame_header += struct.pack('>I', 0)        # commit size
    frame_header += struct.pack('>I', 1)        # salt-1
    frame_header += struct.pack('>I', 1)        # salt-2
    frame_header += struct.pack('>I', 0)        # checksum-1
    frame_header += struct.pack('>I', 0)        # checksum-2

    # Page data (4096 bytes) containing the deleted message text
    page_data = text.encode('utf-8')
    page_data += b'\x00' * (4096 - len(page_data))

    wal_content += frame_header + page_data

with open('msgstore.db-wal', 'wb') as f:
    f.write(wal_content)

print('[✓] Step 3: WAL file created with deleted message texts')
print()
print('=== Database Summary ===')
conn2 = sqlite3.connect('msgstore.db')
total = conn2.execute('SELECT COUNT(*) FROM message').fetchone()[0]
active = conn2.execute('SELECT COUNT(*) FROM message WHERE data IS NOT NULL').fetchone()[0]
deleted = conn2.execute('SELECT COUNT(*) FROM message WHERE data IS NULL').fetchone()[0]
conn2.close()
print(f'Total messages : {total}')
print(f'Active messages: {active}')
print(f'Deleted markers: {deleted}')
print(f'WAL file created with {len(deleted_texts)} recoverable deleted messages')
print()
print('Now run: python recovery.py')