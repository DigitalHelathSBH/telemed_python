# %%
import os
import sys
import requests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    get_connection,
    get_headers,
    should_verify_ssl,
    telepharma_url,
    CONFERENCE_LIST_PATH,
)
# %%

def map_telemed_status(confirm):
    s = str(confirm or "").strip()

    if s == "waiting_confirm":
        return None

    if s == "answered_not_available":
        return "C"

    if s == "answered_available":
        return "Y"

    return None


def map_telemed_status_act(active):
    s = str(active or "").strip()

    if s == "pending":
        return "P"

    if s == "waiting_conference":
        return "S"

    if s == "complete":
        return "Y"

    if s == "cancel":
        return "C"

    return None


def extract_from_api(api_data, wanted_transaction_id):
    arr = api_data.get("result", {}).get("data")

    if not isinstance(arr, list):
        return {
            "confirmation_contact_status": None,
            "status_active": None,
        }

    item = None

    if wanted_transaction_id:
        for x in arr:
            if x.get("transaction_id") == wanted_transaction_id:
                item = x
                break
    else:
        item = arr[0] if arr else None

    if item is None:
        return {
            "confirmation_contact_status": None,
            "status_active": None,
        }

    return {
        "confirmation_contact_status": item.get("confirmation_contact_status"),
        "status_active": item.get("status_active"),
    }


def get_conference_list(appointment_date, transaction_id):
    response = requests.get(
        telepharma_url(CONFERENCE_LIST_PATH),
        headers=get_headers(),
        params={
            "appointment_date": appointment_date,
            "transaction_id": transaction_id,
        },
        timeout=30,
        verify=should_verify_ssl(),
    )

    response.raise_for_status()
    return response.json()

# %%
def get_conference_rows(cursor):
    query = """
        SELECT
             HNAPPMNT.APPOINTMENTNO
            ,HNAPPMNT.transaction_id
            ,REPLACE(CONVERT(varchar, HNAPPMNT.APPOINTMENTDATETIME, 111), '/', '-') AS appointment_date
            ,CONVERT(date, DATEADD(DAY, -1, HNAPPMNT.APPOINTMENTDATETIME)) AS appointment_date_minus1
        FROM HNAPPMNT
        WHERE HNAPPMNT.transaction_id IS NOT NULL
          AND PROCEDURECODE = 'T'
          AND (
                HNAPPMNT.CONFIRMSTATUSTYPE != '6'
                OR HNAPPMNT.CONFIRMSTATUSTYPE IS NULL
              )
          AND CONVERT(date, HNAPPMNT.APPOINTMENTDATETIME) = CONVERT(date,GETDATE())
          AND (
                TelemedStatusAct NOT IN ('C', 'Y')
                OR TelemedStatusAct IS NULL
              )
    """

    cursor.execute(query)
    return cursor.fetchall()

# %%
def update_telemed_status(cursor, telemed_status, appointment_no):
    cursor.execute(
        """
        UPDATE HNAPPMNT
        SET TelemedStatus = ?
        WHERE APPOINTMENTNO = ?
        """,
        telemed_status,
        appointment_no,
    )


def update_telemed_status_act(cursor, telemed_status_act, appointment_no):
    cursor.execute(
        """
        UPDATE HNAPPMNT
        SET TelemedStatusAct = ?
        WHERE APPOINTMENTNO = ?
        """,
        telemed_status_act,
        appointment_no,
    )

# %%
def main():
    print("เริ่มงาน conference")

    conn = None

    updated_status = 0
    updated_act = 0
    skipped = 0
    failed = 0

    try:
        conn = get_connection()
        cursor = conn.cursor()

        rows = get_conference_rows(cursor)
        print("CONFERENCE-LIST ROW COUNT:", len(rows))

        for row in rows:
            try:
                api_data = get_conference_list(
                    appointment_date=row.appointment_date,
                    transaction_id=row.transaction_id,
                )

                extracted = extract_from_api(api_data, row.transaction_id)

                confirmation_contact_status = extracted["confirmation_contact_status"]
                status_active = extracted["status_active"]

                telemed_status = map_telemed_status(confirmation_contact_status)

                if not telemed_status:
                    skipped += 1
                    print(
                        "SKIP waiting_confirm/unknown:",
                        row.APPOINTMENTNO,
                        confirmation_contact_status,
                    )
                    continue

                update_telemed_status(cursor, telemed_status, row.APPOINTMENTNO)
                conn.commit()

                updated_status += 1
                print("UPDATED TelemedStatus:", row.APPOINTMENTNO, telemed_status)

                if telemed_status != "Y":
                    continue

                telemed_status_act = map_telemed_status_act(status_active)

                if not telemed_status_act:
                    print("NO MAP status_active => SKIP ACT:", row.APPOINTMENTNO, status_active)
                    continue

                update_telemed_status_act(cursor, telemed_status_act, row.APPOINTMENTNO)
                conn.commit()

                updated_act += 1
                print("UPDATED TelemedStatusAct:", row.APPOINTMENTNO, telemed_status_act)

            except requests.exceptions.RequestException as err:
                failed += 1
                print("CONFERENCE API ERROR:", row.APPOINTMENTNO, row.transaction_id)

                if err.response is not None:
                    print("HTTP:", err.response.status_code)
                    print("BODY:", err.response.text)
                else:
                    print("ERROR:", str(err))

                continue

            except Exception as err:
                failed += 1
                print("CONFERENCE ERROR:", row.APPOINTMENTNO, row.transaction_id)
                print("ERROR:", str(err))
                continue

        print(
            f"CONFERENCE SUMMARY => "
            f"updatedStatus={updated_status}, "
            f"updatedAct={updated_act}, "
            f"skipped={skipped}, "
            f"failed={failed}"
        )

    except Exception as err:
        print("JOB ERROR:", str(err))
        raise

    finally:
        if conn is not None:
            conn.close()

    print("จบงาน conference")


if __name__ == "__main__":
    main()
# %%
