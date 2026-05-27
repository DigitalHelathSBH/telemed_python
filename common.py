import os
import pyodbc
from dotenv import load_dotenv


load_dotenv()


DB_SERVER = os.getenv("DB_SERVER")
DB_PORT = os.getenv("DB_PORT", "1433")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

TELEPHARMA_BASE_URL = os.getenv("TELEPHARMA_BASE_URL")
HOSPITAL_KEY = os.getenv("HOSPITAL_KEY")
TLS_REJECT_UNAUTHORIZED = os.getenv("TLS_REJECT_UNAUTHORIZED", "true").lower()


REGISTER_PATH = "/telemed-center/register-appointment"
UPDATE_PATH = "/telemed-center/appointment"
CONFERENCE_LIST_PATH = "/telemed-center/conference-list"


def get_connection():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={DB_SERVER},{DB_PORT};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        f"TrustServerCertificate=yes;"
    )


def get_headers():
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json",
        "hospitalkey": HOSPITAL_KEY,
    }


def should_verify_ssl():
    return TLS_REJECT_UNAUTHORIZED != "false"


def telepharma_url(path):
    return f"{TELEPHARMA_BASE_URL}{path}"