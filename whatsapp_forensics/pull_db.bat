@echo off
echo [*] Force stopping WhatsApp...
adb -s emulator-5554 shell am force-stop com.whatsapp

echo [*] Pulling msgstore.db...
adb -s emulator-5554 pull /data/data/com.whatsapp/databases/msgstore.db D:\whatsapp_forensics\msgstore.db

echo [*] Pulling WAL file as wal_file.db...
adb -s emulator-5554 pull /data/data/com.whatsapp/databases/msgstore.db-wal D:\whatsapp_forensics\wal_file.db

echo [*] Pulling SHM file...
adb -s emulator-5554 pull /data/data/com.whatsapp/databases/msgstore.db-shm D:\whatsapp_forensics\shm_file.db

echo [*] Verifying...
dir D:\whatsapp_forensics\*.db

echo [*] Running recovery...
cd D:\whatsapp_forensics
python recovery.py

echo Done!
pause