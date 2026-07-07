import xml.etree.ElementTree as ET
tree = ET.parse(r'D:\DroidSentinel\temp_runtime_perms.xml')
root = tree.getroot()
for pkg in root.findall('.//pkg'):
    if 'cbinnovations' in pkg.get('name', ''):
        print('Package:', pkg.get('name'))
        for perm in pkg.findall('.//perm'):
            print(' -', perm.get('name'))
