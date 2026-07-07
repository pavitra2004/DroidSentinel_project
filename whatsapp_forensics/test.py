import struct

wal_path = r'D:\whatsapp_forensics\wal_file.db'
PAGE_SIZE = 4096

with open(wal_path, 'rb') as f:
    # Read header
    header = f.read(32)
    print(f"WAL header: {len(header)} bytes")
    
    frame_num = 0
    while True:
        frame_header = f.read(24)
        if len(frame_header) < 24:
            break
            
        page_number = struct.unpack('>I', frame_header[0:4])[0]
        page_data = f.read(PAGE_SIZE)
        if len(page_data) < PAGE_SIZE:
            break
            
        # Extract readable text
        text = page_data.decode('utf-8', errors='ignore')
        printable = ''
        for c in text:
            if 32 <= ord(c) <= 126:
                printable += c
            else:
                if len(printable) > 3:
                    print(f"  Frame {frame_num} page {page_number}: '{printable}'")
                printable = ''
                
        frame_num += 1
        
print(f"Total frames: {frame_num}")