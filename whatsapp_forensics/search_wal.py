wal_path = r'D:\whatsapp_forensics\wal_file.db'
search_term = 'Message two will be deleted'

with open(wal_path, 'rb') as f:
    content = f.read()

text = content.decode('utf-8', errors='ignore')

if search_term.lower() in text.lower():
    print('✅ FOUND in WAL!')
    idx = text.lower().find(search_term.lower())
    print('Context:', text[idx-20:idx+100])
else:
    print('❌ NOT FOUND in WAL')
    print('WAL may have been checkpointed already')