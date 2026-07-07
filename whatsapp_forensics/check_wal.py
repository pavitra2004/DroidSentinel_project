wal_path = r'D:\whatsapp_forensics\wal_file.db'

with open(wal_path, 'rb') as f:
    content = f.read()

text = content.decode('utf-8', errors='ignore')

printable = ''
found = []
for c in text:
    if 32 <= ord(c) <= 126:
        printable += c
    else:
        if len(printable) > 4:
            found.append(printable.strip())
        printable = ''

print(f"Total strings found: {len(found)}")
print("\nAll strings in WAL:")
for s in found:
    print(f"  → '{s}'")