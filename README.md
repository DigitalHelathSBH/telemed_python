# telemed_python

โปรเจกต์ Python สำหรับงาน Telemed ของโรงพยาบาล ใช้สำหรับยิง API และอัปเดตสถานะ Telemedicine ตามรอบเวลาที่กำหนดบน Linux Server ผ่าน `cron`

## โครงสร้างโปรเจกต์

```text
telemed_python/
├── .env
├── .gitignore
├── common.py
├── requirements.txt
├── jobs/
│   ├── register.py
│   ├── update.py
│   └── conference.py
├── logs/
│   ├── register.log
│   └── conference.log
└── scripts/
    ├── run_register.sh
    └── run_conference.sh
```
### งานที่ตั้ง Auto Run
ปัจจุบันตั้ง cron ไว้ 2 งานเท่านั้น

1. register.py รันทุกวันเวลา 23:00
```text
0 23 * * * /opt/telemed_python/scripts/run_register.sh
```
2. conference.py
รันทุกวันเวลา 05:00, 10:00, 13:00, 18:00
```text
0 5,10,13,18 * * * /opt/telemed_python/scripts/run_conference.sh
```
## คำสั่งที่ใช้บ่อย
### เช็ค cron ทั้งหมดของ root
```text
crontab -l
```
### แก้ไข cron
```text
crontab -e
```
### เช็คสถานะ cron service
```text
systemctl status cron
```
### เช็ค log ล่าสุด
```text
tail -n 50 /opt/telemed_python/logs/register.log
tail -n 50 /opt/telemed_python/logs/conference.log
```
### เช็ค log แบบ real-time
```text
tail -f /opt/telemed_python/logs/register.log
tail -f /opt/telemed_python/logs/conference.log
```
### ทดสอบรันเอง
```text
cd /opt/telemed_python
./scripts/run_register.sh
./scripts/run_conference.sh
```

## ขั้นตอน Deploy ขึ้น Linux Server
### 1. Clone project จาก GitHub
เข้า server ด้วย root หรือ user ที่มีสิทธิ์ sudo แล้วรัน
```text
cd /opt
git clone https://github.com/DigitalHelathSBH/telemed_python.git /opt/telemed_python
```
### 2. สร้างไฟล์ .env บน server
```text
cd /opt/telemed_python
nano .env
```
ตัวอย่างรูปแบบไฟล์
```text
DB_SERVER=xxx.xxx.xxx.xxx
DB_PORT=1433
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=your_database

TELEPHARMA_BASE_URL=https://example.com
HOSPITAL_KEY=your_hospital_key
TLS_REJECT_UNAUTHORIZED=false
```
บันทึกไฟล์
```text
Ctrl + O
Enter
Ctrl + X
```
### 3. เช็ค Python และ pip
```text
python3 --version
pip3 --version
```
ถ้ายังไม่มี pip3 ให้ติดตั้ง
```text
apt update
apt install python3-pip -y
```
### 4. สร้าง Python Virtual Environment
```text
cd /opt/telemed_python
apt install python3-venv -y
python3 -m venv .venv
```
### 5. ติดตั้ง Python Package
```text
.venv/bin/pip install -r requirements.txt
```
### 6. เช็ค ODBC Driver สำหรับ SQL Server
```text
odbcinst -q -d
```
ต้องเห็น
```text
[ODBC Driver 17 for SQL Server]
```
### 7. ทดสอบเชื่อมต่อ SQL Server
```text
.venv/bin/python -c "from common import get_connection; conn=get_connection(); print('SQL CONNECT OK'); conn.close()"
```
ถ้าปกติจะขึ้น
```text
SQL CONNECT OK
```
## สร้าง Script สำหรับ Cron
### 1. สร้าง folder logs และ scripts
```text
cd /opt/telemed_python
mkdir -p logs scripts
```
### 2. สร้าง run_register.sh
```text
nano /opt/telemed_python/scripts/run_register.sh
```
ใส่เนื้อหา
```text
#!/bin/bash
cd /opt/telemed_python
/opt/telemed_python/.venv/bin/python /opt/telemed_python/jobs/register.py >> /opt/telemed_python/logs/register.log 2>&1
```
### 3. สร้าง run_conference.sh
```text
nano /opt/telemed_python/scripts/run_conference.sh
```
ใส่เนื้อหา
```text
#!/bin/bash
cd /opt/telemed_python
/opt/telemed_python/.venv/bin/python /opt/telemed_python/jobs/conference.py >> /opt/telemed_python/logs/conference.log 2>&1
```
### 4. ให้สิทธิ์ execute
```text
cd /opt/telemed_python
chmod +x scripts/run_register.sh
chmod +x scripts/run_conference.sh
```
เช็คสิทธิ์
```text
ls -la scripts
```
ควรเห็นประมาณนี้
```text
-rwxr-xr-x ... run_register.sh
-rwxr-xr-x ... run_conference.sh
```
## ตั้ง Cron
เปิด crontab
```text
crontab -e
```
เพิ่ม 2 บรรทัดนี้
```text
0 23 * * * /opt/telemed_python/scripts/run_register.sh
0 5,10,13,18 * * * /opt/telemed_python/scripts/run_conference.sh
```
เช็ค cron ที่ตั้งไว้
```text
crontab -l
```
ตัวอย่าง cron ที่ถูกต้อง
```text
0 23 * * * /opt/telemed_python/scripts/run_register.sh
0 5,10,13,18 * * * /opt/telemed_python/scripts/run_conference.sh
```

## เช็คว่า Cron Service ทำงานอยู่ไหม
```text
systemctl status cron
```
ต้องเห็น
```text
Active: active (running)
```
ถ้าเห็นบรรทัดประมาณนี้ แปลว่า cron เรียกงานแล้ว
```text
CRON[...] (root) CMD (/opt/telemed_python/scripts/run_conference.sh)
```
## การเช็ค Log
### ดู log register
```text
tail -n 50 /opt/telemed_python/logs/register.log
```
ดูแบบ real-time
```text
tail -f /opt/telemed_python/logs/register.log
```
### ดู log conference
```text
tail -n 50 /opt/telemed_python/logs/conference.log
```
ดูแบบ real-time
```text
tail -f /opt/telemed_python/logs/conference.log
```
### เช็คเวลาที่ไฟล์ log ถูกแก้ไขล่าสุด
```text
ls -lh /opt/telemed_python/logs
```
ถ้าเวลาไฟล์ register.log หรือ conference.log เปลี่ยนตามรอบ cron แปลว่างานยังทำงานอยู่

## การ Update Code จาก GitHub

เมื่อแก้โค้ดบนเครื่องตัวเองแล้ว push ขึ้น GitHub ให้มา pull บน server
```text
cd /opt/telemed_python
git pull
```
ถ้ามีการเพิ่ม package ใหม่ใน requirements.txt ให้ติดตั้งเพิ่ม
```text
.venv/bin/pip install -r requirements.txt
```
ทดสอบ script อีกครั้ง
```text
./scripts/run_register.sh
tail -n 50 logs/register.log

./scripts/run_conference.sh
tail -n 50 logs/conference.log
```
