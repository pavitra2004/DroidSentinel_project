f = open(r'D:\DroidSentinel\scans\scan_20260622_152654\system\usagestats\0\daily\1782099564302', 'rb')
d = f.read()
f.close()
print('FOUND' if b'cbinnovations' in d else 'NOT FOUND')