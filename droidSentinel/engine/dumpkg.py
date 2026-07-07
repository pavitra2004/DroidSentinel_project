import xml.etree.ElementTree as ET

tree = ET.parse(r'D:\DroidSentinel\scans\scan_20260622_154602\system\packages.xml')
root = tree.getroot()
for pkg in root.findall('.//package'):
    if 'cbinnovations' in pkg.get('name', ''):
        print(ET.tostring(pkg, encoding='unicode')[:3000])
