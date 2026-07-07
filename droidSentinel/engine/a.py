python -c 
import os
folder = r'D:\DroidSentinel\scans\scan_20260622_152654\system\usagestats'
for root, dirs, files in os.walk(folder):
    for f in files:
        path = os.path.join(root, f)
        try:
            with open(path, 'rb') as fp:
                content = fp.read()
                if b'cbinnovations' in content:
                    print(f'FOUND in: {path}')
                else:
                    print(f'NOT found in: {path}')
        except: pass
