import sqlite3

conn = sqlite3.connect(r'D:\whatsapp_forensics\msgstore.db')
rows = conn.execute('''
    SELECT 
        m._id, 
        m.text_data, 
        m.message_type,
        m.chat_row_id,
        m.from_me
    FROM message m
    WHERE m.text_data IS NOT NULL
    AND m.text_data != ""
    ORDER BY m.timestamp ASC
    LIMIT 15
''').fetchall()

print("Oldest messages in database:")
for r in rows:
    print(f"  ID:{r[0]} | chat:{r[3]} | from_me:{r[4]} | type:{r[2]} | text: {str(r[1])[:50]}")

conn.close()