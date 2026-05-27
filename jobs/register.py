# %%
import os
import sys
import json
import requests

# ให้ไฟล์ใน jobs/ import commn.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    get_connection,
    get_headers,
    should_verify_ssl,
    telepharma_url,
    REGISTER_PATH,
)



def map_to_register_payload(row):
    return {
        "hn": row.HN,
        "vn": "False",
        "patient_cid": row.patient_cid,
        "account_title": row.account_title,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "doctor_cid": row.doctor_cid,
        "doctor_title": "แพทย์",
        "doctor_firstname": row.doctor_firstname,
        "doctor_lastname": row.doctor_lastname,
        "birth_date": row.birth_date,
        "phone_number": row.phone_number,
        "phone_number_other": "",
        "appointment_date": row.appointment_date,
        "hospital_code": "10661",
        "hospital_name": "โรงพยาบาลสระบุรี",
        "hospital_department_name": row.hospital_department_name,
        "appointment_type_name": "Telemedicine",
        "hospital_room_name": "Telemedicine",
        "time_start": row.time_start,
        "time_end": row.time_end,
        "require_type": "patient",
        "address_detail": {
            "province": getattr(row, "province", "") or "",
            "district": getattr(row, "district", "") or "",
            "sub_district": getattr(row, "sub_district", "") or "",
            "road": "",
            "moo": getattr(row, "moo", "") or "",
            "house_no": "",
            "zip_code": getattr(row, "zip_code", "") or "",
            "landmark": "",
            "lat": "",
            "lng": "",
        },
        "address_detail_health_rider": {
            "province": "",
            "district": "",
            "sub_district": "",
            "road": "",
            "moo": "",
            "house_no": "",
            "zip_code": "",
            "landmark": "",
            "lat": "",
            "lng": "",
        },
    }


def register_appointment(payload):
    response = requests.post(
        telepharma_url(REGISTER_PATH),
        headers=get_headers(),
        json=payload,
        timeout=30,
        verify=should_verify_ssl(),
    )

    try:
        data = response.json()
    except Exception:
        data = {
            "status": "fail",
            "message": response.text,
        }

    return response.status_code, data


def get_register_rows(cursor):
    query = """
        SELECT
             HNAPPMNT.HN
            ,REPLACE(CONVERT(varchar, APPOINTMENTDATETIME, 111), '/', '-') AS appointment_date
            ,PATIENT_REF.REF AS patient_cid
            ,PYREXT.IDCARD AS doctor_cid
            ,CASE
                WHEN WORKPERMITNO IS NOT NULL THEN
                    (
                        CASE
                            WHEN PYREXT.SEX = '1' THEN 'นพ.'
                            WHEN PYREXT.SEX = '2' THEN 'พญ.'
                            ELSE dbo.GetSSBName(SYSCONFIG.THAINAME)
                        END
                    )
                ELSE dbo.GetSSBName(SYSCONFIG.THAINAME)
             END AS doctor_title
            ,dbo.GetSSBName(PYREXT.FIRSTTHAINAME) AS doctor_firstname
            ,dbo.GetSSBName(PYREXT.LASTTHAINAME) AS doctor_lastname
            ,dbo.GetTitle(HNAPPMNT.HN) AS account_title
            ,REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                dbo.GetSSBName(PATIENT_NAME.FIRSTNAME)
                ,'นาย',''),'น.ส.',''),'ด.ต.',''),'ด.ช.',''),'ด.ญ.',''),'ร.ท.',''),'จ.ส.อ.',''),'ร.ต.',''),'พ.ภ.',''),'น.พ.',''),'น.ญ.','') AS first_name
            ,dbo.GetSSBName(PATIENT_NAME.LASTNAME) AS last_name
            ,REPLACE(CONVERT(varchar, PATIENT_INFO.BIRTHDATETIME, 111), '/', '-') AS birth_date
            ,LEFT(REPLACE(REPLACE(REPLACE(PATIENT_ADDRESS.TEL, '-', ''), ' ', ''), ',', ''), 10) AS phone_number
            ,ClinicName AS hospital_department_name
            ,CONVERT(varchar(5), APPOINTMENTDATETIME, 108) AS time_start
            ,CONVERT(varchar(5), DATEADD(MINUTE, NOMINUTESALLOWANCELATE, CONVERT(time, APPOINTMENTDATETIME)), 108) AS time_end
            ,HNAPPMNT.APPOINTMENTNO
        FROM HNAPPMNT
        JOIN ClinicName
            ON APPOINTMENTWITHCLINIC = CODE
        JOIN PATIENT_REF
            ON HNAPPMNT.HN = PATIENT_REF.HN
           AND PATIENT_REF.REFTYPE = '01'
        JOIN PYREXT
            ON APPOINTMENTWITHDOCTOR = PYREXT.PAYROLLNO
        JOIN PATIENT_NAME
            ON HNAPPMNT.HN = PATIENT_NAME.HN
           AND PATIENT_NAME.SUFFIX = '0'
        JOIN PATIENT_INFO
            ON HNAPPMNT.HN = PATIENT_INFO.HN
        JOIN PATIENT_ADDRESS
            ON HNAPPMNT.HN = PATIENT_ADDRESS.HN
           AND PATIENT_ADDRESS.SUFFIX = '1'
        LEFT JOIN SYSCONFIG
            ON CTRLCODE = '10121'
           AND PYREXT.InitialNameCode = SYSCONFIG.CODE
        WHERE CONVERT(date, HNAPPMNT.MAKEDATETIME) = CONVERT(date,GETDATE())
          AND PROCEDURECODE = 'T'
          AND (
                HNAPPMNT.CONFIRMSTATUSTYPE != '6'
                OR HNAPPMNT.CONFIRMSTATUSTYPE IS NULL
              )
          AND transaction_id IS NULL
    """

    cursor.execute(query)
    return cursor.fetchall()


def update_success(cursor, transaction_id, appointment_no):
    cursor.execute(
        """
        UPDATE HNAPPMNT
        SET transaction_id = ?,
            TelemedStatus = 'S'
        WHERE APPOINTMENTNO = ?
        """,
        transaction_id,
        appointment_no,
    )


def update_fail(cursor, message, appointment_no):
    cursor.execute(
        """
        UPDATE HNAPPMNT
        SET transaction_id = ?,
            TelemedStatus = 'U'
        WHERE APPOINTMENTNO = ?
        """,
        message,
        appointment_no,
    )


def main():
    print("เริ่มงาน register")

    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        rows = get_register_rows(cursor)
        print(f"REGISTER ROW COUNT: {len(rows)}")

        for row in rows:
            try:
                payload = map_to_register_payload(row)

                print("SEND REGISTER APPOINTMENTNO:", row.APPOINTMENTNO)

                http_status, result = register_appointment(payload)

                print("HTTP STATUS:", http_status)
                print("REGISTER RESULT:", json.dumps(result, ensure_ascii=False))

                if result.get("status") == "success":
                    transaction_id = result.get("result", {}).get("transaction_id")

                    update_success(cursor, transaction_id, row.APPOINTMENTNO)
                    conn.commit()

                    print("UPDATED transaction_id:", row.APPOINTMENTNO, transaction_id)

                elif result.get("status") == "fail":
                    message = result.get("message") or "unknown error"

                    update_fail(cursor, message, row.APPOINTMENTNO)
                    conn.commit()

                    print("UPDATED fail message:", row.APPOINTMENTNO, message)

                else:
                    print("UNKNOWN RESPONSE:", row.APPOINTMENTNO)
                    print(json.dumps(result, ensure_ascii=False, indent=2))

            except requests.exceptions.RequestException as err:
                print("REGISTER API ERROR:", row.APPOINTMENTNO)

                if err.response is not None:
                    print("HTTP:", err.response.status_code)
                    print("BODY:", err.response.text)
                else:
                    print("ERROR:", str(err))

                print("REGISTER PAYLOAD SENT:")
                print(json.dumps(payload, ensure_ascii=False, indent=2))

                continue

            except Exception as err:
                print("REGISTER ERROR:", row.APPOINTMENTNO)
                print("ERROR:", str(err))
                continue

    except Exception as err:
        print("JOB ERROR:", str(err))
        raise

    finally:
        if conn is not None:
            conn.close()

    print("จบงาน register")


if __name__ == "__main__":
    main()
# %%
