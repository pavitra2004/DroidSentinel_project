import os

# Path to one daily usagestats file
folder = r"D:\DroidSentinel\artifacts\baseline\usagestats\usagestats\0\daily"

files = os.listdir(folder)
print("Files found:", files)

# Read first file as binary
if files:
    filepath = os.path.join(folder, files[0])
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"\nFile: {files[0]}")
    print(f"Size: {len(data)} bytes")
    print(f"\nFirst 100 bytes (hex):")
    print(data[:100].hex())
    
    print(f"\nReadable strings found:")
    # Extract readable ASCII strings
    current = ""
    for byte in data:
        if 32 <= byte <= 126:
            current += chr(byte)
        else:
            if len(current) >= 4:
                print(current)
            current = ""