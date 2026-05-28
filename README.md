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

#งานที่ตั้ง Auto Run
ปัจจุบันตั้ง cron ไว้ 2 งานเท่านั้น

1. register.py
รันทุกวันเวลา 23:00
0 23 * * * /opt/telemed_python/scripts/run_register.sh

2. conference.py
รันทุกวันเวลา 05:00, 10:00, 13:00, 18:00
0 5,10,13,18 * * * /opt/telemed_python/scripts/run_conference.sh
