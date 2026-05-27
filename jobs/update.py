# %%
import os
import sys
import json
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    get_connection,
    get_headers,
    should_verify_ssl,
    telepharma_url,
    UPDATE_PATH,
)


def map_to_update_payload(row):
    return {
        "hn": row.HN,
        "vn": row.VN,
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
        "appointment_type_name": "Telemedicine",
        "hospital_code": "10661",
        "hospital_name": "โรงพยาบาลสระบุรี",
        "hospital_department_name": row.hospital_department_name,
        "hospital_room_name": "Telemedicine",
        "time_start": row.time_start,
        "time_end": row.time_end,
        "require_type": "patient",
        "address_detail": {
            "province": row.province or "",
            "district": row.district or "",
            "sub_district": row.sub_district or "",
            "road": "",
            "moo": row.moo or "",
            "house_no": "",
            "zip_code": row.zip_code or "",
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


def update_appointment(transaction_id, payload):
    url = telepharma_url(f"{UPDATE_PATH}/{transaction_id}")

    response = requests.put(
        url,
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

    response.raise_for_status()

    return data


def get_update_rows(cursor):
    query = """
        SELECT
             HNAPPMNT.HN
            ,VNPRES.VN
            ,HNAPPMNT.transaction_id
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
            ,LEFT(REPLACE(REPLACE(PATIENT_ADDRESS.TEL, '-', ''), ' ', ''), 10) AS phone_number
            ,REPLACE(CONVERT(varchar, APPOINTMENTDATETIME, 111), '/', '-') AS appointment_date
            ,ClinicName AS hospital_department_name
            ,CONVERT(varchar(5), APPOINTMENTDATETIME, 108) AS time_start
            ,CONVERT(varchar(5), DATEADD(MINUTE, NOMINUTESALLOWANCELATE, CONVERT(time, APPOINTMENTDATETIME)), 108) AS time_end
            ,dbo.Province(HNAPPMNT.HN) AS province
            ,dbo.Amphoe(HNAPPMNT.HN) AS district
            ,dbo.Tambon(HNAPPMNT.HN) AS sub_district
            ,PATIENT_ADDRESS.MOO AS moo
            ,PATIENT_ADDRESS.POSTALCODE AS zip_code
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
        JOIN PATIENT_INFO
            ON HNAPPMNT.HN = PATIENT_INFO.HN
        JOIN PATIENT_ADDRESS
            ON HNAPPMNT.HN = PATIENT_ADDRESS.HN
           AND PATIENT_ADDRESS.SUFFIX = '1'
        LEFT JOIN SYSCONFIG
            ON CTRLCODE = '10121'
           AND PYREXT.InitialNameCode = SYSCONFIG.CODE
        JOIN VNPRES
            ON HNAPPMNT.APPOINTMENTNO = VNPRES.APPOINTMENTNO
        WHERE PROCEDURECODE = 'T'
          AND transaction_id IS NOT NULL
          AND TelemedStatus = 'S'
          AND (
                HNAPPMNT.CONFIRMSTATUSTYPE != '6'
                OR HNAPPMNT.CONFIRMSTATUSTYPE IS NULL
              )
          AND VNPRES.VISITDATE >= CONVERT(date, GETDATE())
    """

    cursor.execute(query)
    return cursor.fetchall()


def main():
    print("เริ่มงาน update")

    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        rows = get_update_rows(cursor)
        print("UPDATE ROW COUNT:", len(rows))

        for row in rows:
            try:
                payload = map_to_update_payload(row)

                print("SEND UPDATE APPOINTMENTNO:", row.APPOINTMENTNO)
                print("TRANSACTION_ID:", row.transaction_id)

                result = update_appointment(row.transaction_id, payload)

                print("UPDATE RESULT:", json.dumps(result, ensure_ascii=False))

                if result.get("status") == "success":
                    print("UPDATE SUCCESS:", row.APPOINTMENTNO, row.transaction_id)
                else:
                    msg = result.get("message") or "update fail"
                    print("UPDATE FAIL:", row.APPOINTMENTNO, msg)

            except requests.exceptions.RequestException as err:
                print("UPDATE API ERROR:", row.APPOINTMENTNO)

                if err.response is not None:
                    print("HTTP:", err.response.status_code)
                    print("BODY:", err.response.text)
                else:
                    print("ERROR:", str(err))

                print("UPDATE PAYLOAD SENT:")
                print(json.dumps(payload, ensure_ascii=False, indent=2))

                continue

            except Exception as err:
                print("UPDATE ERROR:", row.APPOINTMENTNO)
                print("ERROR:", str(err))
                continue

    except Exception as err:
        print("JOB ERROR:", str(err))
        raise

    finally:
        if conn is not None:
            conn.close()

    print("จบงาน update")


if __name__ == "__main__":
    main()
# %%
